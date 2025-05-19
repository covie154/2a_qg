import datetime
import question_gen.class_gen as class_gen
from langchain_community.document_loaders import PyPDFLoader
from celery import shared_task, group
from celery_progress.backend import ProgressRecorder
from celery.result import AsyncResult, allow_join_result
import time
from django.conf import settings
from upload_file.models import upload_file as Upload
import os
import logging
import traceback

# Set up logging
logger = logging.getLogger(__name__)

def track_time(func):
    """
    Decorator to track the time taken for a function to run.
    Args:
        func (function): The function to track the time for.
    Returns:
        function: The decorated function.
    """
    def wrapper(*args, **kwargs):
        # Track the start time
        start_time = time.time()

        # Run the function
        result = func(*args, **kwargs)

        # Track the end time
        end_time = time.time()

        # Calculate the time taken
        time_taken = end_time - start_time
        time_taken_min_sec = [int(time_taken // 60), int(time_taken % 60)]
        print(f'Time taken: {time_taken_min_sec[0]} mins {time_taken_min_sec[1]} secs')

        return result

    return wrapper

# Instantiate the TwoAQG class
TwoAQG = class_gen.TwoAQG()
TwoAQG.log_level = 0

def get_progress_increment(task_id):
    """
    Get the current progress increment values from a celery task.
    
    Args:
        task_id (str): The ID of the task to get progress for
        
    Returns:
        list: A list containing [current_progress, total_progress] or [0, 100] if not available
    """
    try:
        # Get the task result
        result = AsyncResult(task_id)
        
        # Check if the task has progress metadata
        if result.state == 'PROGRESS' and result.info:
            # Extract progress info from the task metadata
            meta = result.info
            if 'current' in meta and 'total' in meta:
                return [meta['current'], meta['total']]
        
        # For completed tasks
        if result.ready():
            return [100, 100]  # Return full progress
            
        # Default progress values if not found
        return [0, 100]
    except Exception as e:
        logger.error(f"Error retrieving progress for task {task_id}: {str(e)}")
        return [0, 100]  # Return default progress on error
    
def updateTask(task_id, current, total, description='Processing'):
    """
    Update the progress of another task by ID.
    
    Args:
        task_id (str): The ID of the task to update progress for
        current (int): Current progress value
        total (int): Total work to do
        description (str): Description of the current progress state
    """
    try:
        # Get the task result
        result = AsyncResult(task_id)
        
        # Update task state with progress information
        result.backend.store_result(
            task_id,
            {
                'current': current, 
                'total': total,
                'description': description
            },
            'PROGRESS'
        )
        logger.info(f"Updated task {task_id} progress: {current}/{total} - {description}")
    except Exception as e:
        logger.error(f"Error updating progress for task {task_id}: {str(e)}")

# Explicitly register tasks with descriptive names
@shared_task(bind=True, name='upload_file.tasks.generateAQuestion')
@track_time
def generateAQuestion(self, input_paper, dx, input_paper_path, doi, parent_task_id=None):
    """
    Generates one question with its own progress tracking.
    
    Args:
        input_paper (dict): A dictionary containing the input paper data.
        dx (dict): dx to use when generating diagnosis.
        
    Returns:
        dict: The generated question.
    """
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 4  # Diagnosis, Stem, Options, Complete
    
    if parent_task_id:
        current, total = get_progress_increment(parent_task_id)

    try:
        # Generate the question
        qn_stem = TwoAQG.generateStem(dx, dx['Diagnosis'])
        progress_recorder.set_progress(1, total_work_to_do, description=f'Generating question stem')
        if parent_task_id:
            updateTask(parent_task_id, current+1, total, description=f"Generating question stem for: {dx['Diagnosis']}")
        logger.info(f"[+] Subqn: Generating question stem for {dx['Diagnosis']}")
        
        qn_options = TwoAQG.generateOptions(input_paper, dx['Diagnosis'])
        progress_recorder.set_progress(2, total_work_to_do, description=f'Generating options')
        if parent_task_id:
            updateTask(parent_task_id, current+2, total, description=f"Generating options for: {dx['Diagnosis']}")
        logger.info(f"[+] Subqn: Generating options for {dx['Diagnosis']}")
        
        init_qn = TwoAQG.completeQuestion(qn_stem, qn_options)
        progress_recorder.set_progress(3, total_work_to_do, description=f'Completing question')
        if parent_task_id:
            updateTask(parent_task_id, current+3, total, description=f"Completing question for: {dx['Diagnosis']}")
        logger.info(f"[+] Subqn: Completing question for {dx['Diagnosis']}")
        
        modified_qn = TwoAQG.refineQuestionCOT(init_qn, input_paper)
        progress_recorder.set_progress(4, total_work_to_do, description=f'Refining question')
        if parent_task_id:
            updateTask(parent_task_id, current+4, total, description=f"Refining question for: {dx['Diagnosis']}")
        logger.info(f"[+] Subqn: Refining question for {dx['Diagnosis']}")
                
        # If explanation_other is less than 4, fill the rest with empty strings to complete it
        for empty_entry in range(4 - len(modified_qn['Explanation_Other'])):
            modified_qn['Explanation_Other'].append('')
        
    except Exception as e:
        logger.error(f"[!] Error: {str(e)}")
        logger.error(traceback.format_exc())
    
        if parent_task_id:
            updateTask(parent_task_id, current+4, total, description=f"Error in generating question for {dx['Diagnosis']}")
        return None
    
    else:
        modified_qn['paper_path'] = input_paper_path
        modified_qn['doi'] = doi
        logger.info(f"[+] Subqn: Succesfully generated qn for {dx['Diagnosis']}:`n{TwoAQG.displayPlaintextQuestion(modified_qn)}")
        return modified_qn

@shared_task(bind=True, name='upload_file.tasks.generateNQuestions')
def generateNQuestions(self, n, input_paper, input_paper_path):
    """
    Process the results of question generation tasks.
    Called as a callback after all question generation tasks complete.
    
    Args:
        input_paper (dict): The input paper data.
        input_paper_path (str): The path to the input paper file.
        
    Returns:
        dict: The processed questions results
    """
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 3 + (4 * n)  # Diagnosis, Stem, Options, Complete
    current_task_id = self.request.id
    
    progress_recorder.set_progress(0, total_work_to_do, description='Setting up...')
    
    # Generate N diagnoses instead of one
    diagnoses = TwoAQG.generateDx(input_paper, n)
    
    # Get the doi
    doi = TwoAQG.getDOI(input_paper)
    
    logger.info(f"[+] Generated {len(diagnoses)} diagnoses for question generation")
    progress_recorder.set_progress(1, total_work_to_do, description='Generating diagnoses')
    
    # Generate the questions in parallel
    result_group = group(
        generateAQuestion.signature(
            args=(input_paper, dx, input_paper_path, doi, current_task_id),
            options={'queue': 'question_generation'}
        )
        for dx in diagnoses
    )
        
    # Execute the tasks in parallel using group
    group_result = result_group.apply_async()
    progress_recorder.set_progress(2, total_work_to_do, description='Waiting for questions to complete')
    
    # Log the task IDs for each subtask
    task_ids = []
    for task_result in group_result.children:
        task_id = task_result.id
        task_ids.append(task_id)
        logger.info(f"[+] Started subtask with ID: {task_id}")

    # Wait for all tasks to complete with a timeout
    try:
        # Use allow_join_result to explicitly permit waiting for results within a task
        with allow_join_result():
            questions = group_result.get(timeout=1200)  # 20-minute timeout
            for key, value in enumerate(questions):
                if value is None:
                    del questions[key]
                    continue             
            logger.info(f"[+] Successfully generated {len(questions)} questions")
        progress_recorder.set_progress(3, total_work_to_do, description='Processing results')
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        # Fallback: if we got some results but not all
        questions = []
        with allow_join_result():
            if hasattr(group_result, 'results') and group_result.results:
                questions = [r.result for r in group_result.results if r.successful()]
                logger.info(f"[!] Retrieved {len(questions)} partial results")
    
    progress_recorder.set_progress(4, total_work_to_do, description='Complete')
    logger.info("[+] All questions generated successfully")
    
    # Return the results as a JSON
    all_qns = {
        'questions': questions,
        # 'task_ids': task_ids, # Include the task IDs in the result
        # parent_task_id: current_task_id
    }
    
    logger.info(f"[+] Successfully generated {len(questions)} questions`n{all_qns}")
    
    return all_qns

# When calling the task from elsewhere in the code:
#
# When calling the task
# task_result = generateNQuestions.delay(n, input_paper, input_paper_path)
# task_id = task_result.id
# print(f"Started task with ID: {task_id}")

@shared_task(bind=True)
def testTask(self):
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 20

    for i in range(total_work_to_do):
        time.sleep(3)
        print(f'Progress: {i + 1}/{total_work_to_do}')
        progress_recorder.set_progress(i + 1, total_work_to_do, description='Processing...')

    return 'Done'

def progress_callback(current, total):
    print('Task progress: {}%'.format(current / total * 100))


def generateQuestion(class_class_gen, input_paper, no_dx=3):
        """
        Generates a set of questions based on the number of diagnoses provided.
        Args:
            no_dx (int, optional): The number of diagnoses to generate questions for. Defaults to 3.
        Returns:
            None
        """

        diagnoses = class_class_gen.generateDx(input_paper, no_dx)
        output_dx_lst = []

        for dx in diagnoses:
            # Generate the question
            one_qn = generateOneQuestion.delay(class_class_gen, input_paper, dx)
            output_dx_lst.append(one_qn)

        return output_dx_lst

def handleUploadedFile(f): 
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = timestamp + "_" + f.name
    
    if settings.USE_S3:
        # Rename the file object before saving to S3
        f.name = file_name
        # Create a new upload object and assign the file directly
        upload = Upload(file=f)  # Pass the actual file object with the new name
        upload.save()
        file_path = upload.file.url
        
        # For PyPDFLoader, we'll need to download the file temporarily
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1])
        for chunk in f.chunks():
            temp_file.write(chunk)
        temp_file.close()
        file_path_for_loader = temp_file.name
    else:
        file_path = 'upload_file/static/upload/' + file_name
        with open(file_path, 'wb+') as destination:  
            for chunk in f.chunks():  
                destination.write(chunk)
        file_path_for_loader = file_path

    return file_path_for_loader

def getTextFromFile(file_path_for_loader):
    # Load the document using PyPDFLoader
    loader = PyPDFLoader(file_path_for_loader)
    documents = loader.load()

    # Clean up temporary file if we created one
    if settings.USE_S3 and os.path.exists(file_path_for_loader):
        os.unlink(file_path_for_loader)

    # Get the text of the document
    doc_text = [x.page_content for x in documents]
    doc_text_1 = '\n'.join(doc_text)

    # Get DOI
    #doi = TwoAQG.getDOI(doc_text_1)
    # Get facts
    #ten_facts = TwoAQG.generateFacts()
    #ten_facts_string = '\n\n'.join(ten_facts)
    
    if doc_text_1:
        return doc_text_1
    else:
        return False
    
############################################

# DEPRECATED
# Explicitly register tasks with descriptive names
@shared_task(bind=True, name='upload_file.tasks.generateOneQuestion')
@track_time
def generateOneQuestion(self, input_paper, input_paper_path=None):
    """
    Generates a single question based on the provided class generator, input paper, and diagnosis data.
    Args:
        input_paper (dict): A dictionary containing the input paper data.
    Returns:
        dict: A dictionary representing the modified question.
    """
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 6
    
    # Find the DOI and get the 10 facts
    doi = TwoAQG.getDOI(input_paper)
    #ten_facts = TwoAQG.generateFacts()
    progress_recorder.set_progress(1, total_work_to_do, description='Setting up')
    
    # Generate the dx
    diagnoses = TwoAQG.generateDx(input_paper, 1)
    dx = diagnoses[0]
    progress_recorder.set_progress(2, total_work_to_do, description='Generating diagnosis')

    # Generate the question
    qn_stem = TwoAQG.generateStem(dx, dx['Diagnosis'])
    progress_recorder.set_progress(3, total_work_to_do, description='Generating question stem')
    
    qn_options = TwoAQG.generateOptions(input_paper, dx['Diagnosis'])
    progress_recorder.set_progress(4, total_work_to_do, description='Generating question options')
    
    init_qn = TwoAQG.completeQuestion(qn_stem, qn_options)
    progress_recorder.set_progress(5, total_work_to_do, description='Completing question')
    
    modified_qn = TwoAQG.refineQuestionCOT(init_qn, input_paper)
    progress_recorder.set_progress(6, total_work_to_do, description='Refining question')

    modified_qn['doi'] = doi
    modified_qn['paper_path'] = input_paper_path
    
    return modified_qn
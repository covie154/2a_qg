import datetime
import question_gen.class_gen as class_gen
from langchain_community.document_loaders import PyPDFLoader
from celery import shared_task
from celery_progress.backend import ProgressRecorder
import time

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
TwoAQG.log_level = 1

@shared_task(bind=True)
@track_time
def generateOneQuestion(self, input_paper):
    """
    Generates a single question based on the provided class generator, input paper, and diagnosis data.
    Args:
        input_paper (dict): A dictionary containing the input paper data.
    Returns:
        dict: A dictionary representing the modified question.
    """
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 5

    # Generate the dx
    diagnoses = TwoAQG.generateDx(input_paper, 1)
    dx = diagnoses[0]
    progress_recorder.set_progress(1, total_work_to_do, description='Generating diagnosis')

    # Generate the question
    qn_stem = TwoAQG.generateStem(dx, dx['Diagnosis'])
    progress_recorder.set_progress(2, total_work_to_do, description='Generating question stem')
    
    qn_options = TwoAQG.generateOptions(input_paper, dx['Diagnosis'])
    progress_recorder.set_progress(3, total_work_to_do, description='Generating question options')
    
    init_qn = TwoAQG.completeQuestion(qn_stem, qn_options)
    progress_recorder.set_progress(4, total_work_to_do, description='Completing question')
    
    modified_qn = TwoAQG.refineQuestionCOT(init_qn, input_paper)
    progress_recorder.set_progress(5, total_work_to_do, description='Refining question')

    return modified_qn

@shared_task(bind=True)
def testTask(self):
    progress_recorder = ProgressRecorder(self)
    total_work_to_do = 10

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

def handle_uploaded_file(f): 
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # Upload the file
    file_path = 'upload_file/static/upload/'+timestamp+"_"+f.name
    with open(file_path, 'wb+') as destination:  
        for chunk in f.chunks():  
            destination.write(chunk)

    # Load the document using PyPDFLoader
    loader = PyPDFLoader(file_path)
    documents = loader.load()

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
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.http import require_POST
from upload_file.functions import handleUploadedFile, testTask, getTextFromFile, generateNQuestions, get_progress_increment
from upload_file.forms import UploadForm 
from celery.result import AsyncResult
from .models import TwoAQuestions
import logging

# Set logging
logger = logging.getLogger(__name__)

def index(request):  
    if request.method == 'POST':  
        student = UploadForm(request.POST, request.FILES)  
        if student.is_valid():
            input_paper_path = handleUploadedFile(request.FILES['file'])
            input_paper = getTextFromFile(input_paper_path)
            if input_paper:
                # Changed to use generateThreeQuestions instead of generateOneQuestion
                result = generateNQuestions.apply_async(args=[3, input_paper, input_paper_path], queue='default')
                print(f'http://127.0.0.1:8000/celery-progress/{result.task_id}')
                return render(request, 'display_progress.html', context={'task_id': result.task_id})
            else:
                return HttpResponse("Something wrong?")       
    else:  
        student = UploadForm()  
        return render(request,"upload_file.html",{'form':student})

def result_view(request, task_id):
    """View to display the result of a completed task in an HTML template"""
    task_result = AsyncResult(task_id)
    if (task_result.ready()):
        result_data = task_result.result
        
        # Log the structure of the result
        logger.info(f"Task {task_id} result structure: {type(result_data)}")
        if isinstance(result_data, dict):
            logger.info(f"Result keys: {result_data.keys()}")
            if 'questions' in result_data:
                logger.info(f"Number of questions: {len(result_data['questions'])}")
        
        # Save multiple questions to database
        save_multiple_results_to_db(result_data, task_id=task_id)
        
        # Retrieve the questions directly from the database using task_id
        question_entries = TwoAQuestions.objects.filter(task_id=task_id)
        logger.info(f"Found {question_entries.count()} questions in database for task {task_id}")
        
        # Create a list of result dictionaries from the database entries
        db_results = []
        for question_entry in question_entries:
            db_result = {
                "id": question_entry.id,
                "Question_Stem": question_entry.question,
                "Options": [
                    question_entry.option1,
                    question_entry.option2,
                    question_entry.option3,
                    question_entry.option4,
                    question_entry.option5
                ],
                "Correct_Option_Index": question_entry.answer_index,
                "Explanation": question_entry.explanation,
                "Explanation_Other": [
                    question_entry.explanation_other1,
                    question_entry.explanation_other2,
                    question_entry.explanation_other3,
                    question_entry.explanation_other4
                ],
                "doi": question_entry.doi,
            }
            db_results.append(db_result)
        
        # Render the template using data from the database
        return render(request, "results_multiple.html", {'results': db_results})
    else:
        return render(request, "display_progress.html", {'task_id': task_id})

def save_result_to_db(result, task_id=None, source_file=None):
    """
    Save the task result to the database using the TwoAQuestions model.
    
    Args:
        result: Dictionary containing the task result
        task_id: ID of the task that generated this result
        source_file: Optional file object that was the source of the task
    """
    question_entry = TwoAQuestions(
        doi=result["doi"],
        task_id=task_id,  # Save the task_id to the database
        source_file=result['paper_path'],
        question=result["Question_Stem"],
        option1=result["Options"][0],
        option2=result["Options"][1],
        option3=result["Options"][2],
        option4=result["Options"][3],
        option5=result["Options"][4],
        answer_index=result["Correct_Option_Index"],
        explanation=result["Explanation"],
        explanation_other1=result["Explanation_Other"][0],
        explanation_other2=result["Explanation_Other"][1],
        explanation_other3=result["Explanation_Other"][2],
        explanation_other4=result["Explanation_Other"][3],
    )
    question_entry.save()
    return question_entry

def save_multiple_results_to_db(result_data, task_id=None):
    """
    Save multiple questions to the database.
    
    Args:
        result_data: Dictionary containing 'questions' list with multiple question results
        task_id: ID of the task that generated these results
    
    Returns:
        List of saved database entries
    """
    question_entries = []
    
    # Extract questions from the result data structure
    questions = result_data.get('questions', [])
    
    # Save each question to the database with the same task_id
    for question in questions:
        question_entry = save_result_to_db(question, task_id)
        question_entries.append(question_entry)
    
    return question_entries

def qn_view(request, qn_id):
    """View to display a specific question by ID in an HTML template"""
    try:
        # Get the question from the database
        question_entry = TwoAQuestions.objects.get(id=qn_id)
        
        # Create a result dictionary from the database entry
        result = {
            "Question_Stem": question_entry.question,
            "Options": [
                question_entry.option1,
                question_entry.option2,
                question_entry.option3,
                question_entry.option4,
                question_entry.option5
            ],
            "Correct_Option_Index": question_entry.answer_index,
            "Explanation": question_entry.explanation,
            "Explanation_Other": [
                question_entry.explanation_other1,
                question_entry.explanation_other2,
                question_entry.explanation_other3,
                question_entry.explanation_other4
            ],
            "doi": question_entry.doi,
        }
        
        # Render the template using data from the database
        return render(request, "result.html", {'result': result})
    
    except TwoAQuestions.DoesNotExist:
        # Return a 404 if the question doesn't exist
        raise Http404("Question does not exist")

def list_questions(request):
    """View to display a list of all questions with links to their individual pages"""
    # Get all questions from the database
    questions = TwoAQuestions.objects.all()
    
    # Render the template with the list of questions
    return render(request, "questions_list.html", {'questions': questions})

def selected_questions(request):
    """View to display a list of only the chosen questions"""
    # Get only chosen questions from the database
    questions = TwoAQuestions.objects.filter(chosen=True)
    
    # Render the template with the filtered list of questions
    return render(request, "questions_list.html", {'questions': questions, 'selected_view': True})

def get_task_progress(request, task_id):
    """API endpoint to get the current progress of a task"""
    progress_values = get_progress_increment(task_id)
    current, total = progress_values
    
    # Calculate percentage
    percentage = (current / total) * 100 if total > 0 else 0
    
    # Get the task result to check status and description
    result = AsyncResult(task_id)
    status = result.state
    
    # Get description if available
    description = "Processing..."
    if status == 'PROGRESS' and hasattr(result, 'info') and result.info:
        description = result.info.get('description', description)
    
    # Prepare the response data
    data = {
        'task_id': task_id,
        'current': current,
        'total': total,
        'percentage': round(percentage, 1),
        'status': status,
        'description': description
    }
    
    return JsonResponse(data)

@require_POST
def toggle_chosen(request, qn_id):
    """Toggle the 'chosen' status of a question"""
    try:
        # Get the question from the database
        question = TwoAQuestions.objects.get(id=qn_id)
        
        # Toggle the chosen field
        question.chosen = not question.chosen
        question.save()
        
        return JsonResponse({
            'success': True,
            'chosen': question.chosen
        })
    
    except TwoAQuestions.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Question does not exist'
        }, status=404)

def tasks_all(request):
    """View to display a list of all task IDs with their related questions"""
    # Get all unique task_ids from the database
    task_ids = TwoAQuestions.objects.values_list('task_id', flat=True).distinct()
    
    # Create a list to store task data
    tasks_data = []
    
    # For each task_id, get the related questions
    for task_id in task_ids:
        questions = TwoAQuestions.objects.filter(task_id=task_id)
               
        # Get all questions for this task (truncated)
        all_questions = []
        for question in questions:
            all_questions.append({
                'id': question.id,
                'text': question.question[:100] + '...' if len(question.question) > 100 else question.question,
                'chosen': question.chosen
            })
        
        # Add task data to the list
        tasks_data.append({
            'task_id': task_id,
            'questions': all_questions,
            'created_at': questions.first().uploaded_at if hasattr(questions.first(), 'uploaded_at') else 'Unknown'
        })
    
    # Sort by most recent first (if timestamp available)
    tasks_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Render the template with the tasks data
    return render(request, "tasks_list.html", {'tasks': tasks_data})

def task_view(request, task_id):
    """View to display results of a specific task by its ID"""
    try:
        # Retrieve the questions directly from the database using task_id
        question_entries = TwoAQuestions.objects.filter(task_id=task_id)
        
        if not question_entries.exists():
            return HttpResponse(f"No questions found for task ID: {task_id}", status=404)
            
        logger.info(f"Found {question_entries.count()} questions in database for task {task_id}")
        
        # Create a list of result dictionaries from the database entries
        db_results = []
        for question_entry in question_entries:
            db_result = {
                "id": question_entry.id,
                "Question_Stem": question_entry.question,
                "Options": [
                    question_entry.option1,
                    question_entry.option2,
                    question_entry.option3,
                    question_entry.option4,
                    question_entry.option5
                ],
                "Correct_Option_Index": question_entry.answer_index,
                "Explanation": question_entry.explanation,
                "Explanation_Other": [
                    question_entry.explanation_other1,
                    question_entry.explanation_other2,
                    question_entry.explanation_other3,
                    question_entry.explanation_other4
                ],
                "doi": question_entry.doi,
                "chosen": question_entry.chosen
            }
            db_results.append(db_result)
        
        # Render the template using data from the database
        return render(request, "results_multiple.html", {'results': db_results, 'task_id': task_id})
        
    except Exception as e:
        logger.error(f"Error retrieving task results: {str(e)}")
        return HttpResponse(f"Error retrieving results for task ID: {task_id}", status=500)
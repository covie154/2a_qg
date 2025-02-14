from django.shortcuts import render
from django.http import HttpResponse  
from upload_file.functions import handle_uploaded_file, testTask, ProgressRecorder
from upload_file.forms import UploadForm 

def index(request):  
    if request.method == 'POST':  
        student = UploadForm(request.POST, request.FILES)  
        if student.is_valid():
            input_paper = handle_uploaded_file(request.FILES['file'])
            if input_paper:
                #result = generateOneQuestion.delay(input_paper)
                result = testTask.delay()
                print(f'http://127.0.0.1:8000/celery-progress/{result.task_id}')
                return render(request, 'display_progress.html', context={'task_id': result.task_id})
            else:
                return HttpResponse("Something wrong?")       
    else:  
        student = UploadForm()  
        return render(request,"upload_file.html",{'form':student})

'''
def progress_view(request):
    result = my_task.delay(10)
    return render(request, 'display_progress.html', context={'task_id': result.task_id})
'''	
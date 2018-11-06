import time
from celery import Celery

celery_app = Celery('tasks', backend='redis://localhost', broker='redis://localhost')
# this is celery settings

# this is a function about need many time
@celery_app.task
def add(a, b):
    time.sleep(5)
    return a + b

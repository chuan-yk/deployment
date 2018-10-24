from django.template import loader
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def indexpage(request):
    return render(request, 'indexpage.html')

@login_required
def comingsoon(request):
    return render(request, '404page.html')
#from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    return HttpResponse('Здесь будет главная страница')


def group_posts(request, slug):
    return HttpResponse('Здесь будут посты, отфильтрованные по группам')

# Create your views here.

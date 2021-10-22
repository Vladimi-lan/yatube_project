from django.shortcuts import get_object_or_404, render

from .models import Group, Post


def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()[:10]
    context = {
        'posts': posts,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    title = {group.title}
    posts = group.group_posts.all()[:10]
    context = {
        'title': title,
        'group': group,
        'posts': posts,
    }
    return render(request, template, context)

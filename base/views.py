from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from .forms import PostForm
from .models import Tag, Post, Comment

#Used for old search method
#from django.db.models import Q
#from functools import reduce
#stop_words = {'of', 'and', 'on', 'a', 'is', 'an', 'at', 'the', 'in', 'my', 'i', 'as', 'that', 'it'}

# Create your views here.
def home(request):
    q = request.GET.get('q', '') .split()
    page_num = request.GET.get('page', '')
    page_num = int(page_num) if page_num else 1

    if q:
        '''OLD METHOD: LACK OF RELEVANCY SORTING USING | OR TOO EXCLUSIVE USING &
        querylist = list(filter(lambda a: True if not a.lower() in stop_words else False, q))
        print(querylist)
        query = reduce(lambda a, b: a & b, [Q(tags__name__icontains=query) | Q(user__username__icontains=query) | Q(title__icontains=query) for query in querylist])
        posts = Post.objects.filter(query).distinct()
        '''
        converted_q = [f"'{word}':*" for word in q]
        converted_q = ' | '.join(converted_q)
        #print(converted_q)

        search_vector = SearchVector('title') + SearchVector('tags__name') + SearchVector('user__username')
        search_query = SearchQuery(converted_q, search_type='raw')
        search_rank = SearchRank(search_vector, search_query)
        posts = Post.objects.annotate(search=search_vector, rank=search_rank).filter(search=search_query).order_by('-rank').distinct('rank', 'id')

        
        #returns all tags that share a post with given tag
        search_vector_tags = SearchVector('post__tags__name')
        search_rank_tags = SearchRank(search_vector_tags, search_query)
        tags = Tag.objects.annotate(search=search_vector_tags, rank=search_rank_tags).filter(search=search_query).order_by('-rank').distinct('rank','id')[0:50]
    else:
        posts = Post.objects.all()
        tags = Tag.objects.all()[:50]

    
    #get 50 tags/users in show posts
    #filter(post__in=posts) does not work because annotate fucking breaks it. Instead, we will get a constant runtime of 50 by creating a list - MORE RESULTS/LESS SELECTIVE
    post_ids = [post.id for post in posts[:50]]
    #tags = Tag.objects.filter(post__id__in=post_ids).distinct()
    
    users = User.objects.filter(posts__id__in=post_ids).distinct()
    
    
    

    pages = Paginator(posts, 3)
    posts_page = pages.page(page_num)
    query = ' '.join(q)
    return render(request, 'base/home.html', {'posts_page': posts_page, 'tags': tags, 'users':users, 'query': query, 'page_num': page_num})

def dfs(comment, queryset):
    queryset += [comment]
    #print('ADDED:', comment.body)
    if not comment.replies.all().exists():
        return

    for reply in comment.replies.all().filter().order_by('-created'):
        #print('REPLY, GOING INTO:', reply.body, 'COMMENTSET:', queryset)
        dfs(reply, queryset)

def post(request, pk):
    post = Post.objects.get(id=pk)
    root_comments = post.comment_set.filter(parent=None).order_by('-created').distinct('created', 'id')
    comments = []
    for comment in root_comments:
        #print('ROOT, GOING INTO:', comment.body, 'COMMENTSET:', comments)
        dfs(comment, comments)

    if request.method=='POST':
        if not request.user.is_authenticated:
            return redirect('login')
        else:
            body = request.POST.get('comment')
            comment = Comment.objects.create(user=request.user, post=post, body=body)
            comment.save()
            return redirect('post', pk=pk)

    return render(request, 'base/post.html', {'post':post, 'comments':comments})

@login_required(login_url='login')
def reply(request, post_pk, comment_pk):
    post = Post.objects.get(id=post_pk)
    comment = Comment.objects.get(id=comment_pk)
    body = request.POST.get('reply')
    depth = comment.depth + '1'

    reply = Comment.objects.create(user=request.user, parent=comment, post=post, body=body, depth=depth)
    reply.save()

    return redirect('post', pk=post_pk)

def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if not user == None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Incorrect Username or Password')
            
    return render(request, 'base/login.html')

def logout_user(request):
    logout(request)
    return redirect('home')

@login_required(login_url="login")
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post = form.save()

            tag_list_str = request.POST.get('tags').split(',')
            if tag_list_str[-1].isspace():
                tag_list_str = tag_list_str[:-1]

            #create a list of tag objects from the list of tag strings
            tag_list = list(map(lambda x: x[0], [Tag.objects.get_or_create(name=x.strip()) for x in tag_list_str]))

            for tag in tag_list:
                post.tags.add(tag)
            post.save()

            return redirect(f'home')
            
    form = PostForm()
    tags = Tag.objects.all()
    return render(request, 'base/create_post.html', {'form': form, 'tags':tags})

def delete(request, pk, obj):
    name = obj
    if name == 'post':
        obj = Post.objects.get(id=pk)
    else:
        obj = Comment.objects.get(id=pk)
        post = obj.post

    if request.user != obj.user:
        return HttpResponse('Wtf are you doing here?')
    
    if request.method == 'POST':
        obj.delete()
        if isinstance(obj, Post):
            return redirect('home')
        else:
            return redirect('post', post.id)

    return render(request, 'base/delete.html', {'obj':obj, 'name':name})

@login_required(login_url='login')
def favorite(request, pk):
    post = Post.objects.get(id=pk)

    if post.favorites.filter(username=request.user.username).exists():
        post.favorites.remove(request.user)
    else:
        post.favorites.add(request.user)

    return redirect(request.META['HTTP_REFERER'])

@login_required(login_url='login')
def like(request, pk, obj):
    if obj=='post':
        obj = Post.objects.get(id=pk)
    else:
        obj = Comment.objects.get(id=pk)

    if obj.likes.filter(username=request.user.username).exists():
        obj.likes.remove(request.user)
    else:
        obj.likes.add(request.user)

    return redirect(request.META['HTTP_REFERER'])
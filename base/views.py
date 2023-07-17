from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm

from django.core.paginator import Paginator
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Count, Q, functions
from .forms import PostForm, ProfileForm, RegistrationForm, EditUserForm, LoginForm
from .models import Tag, Post, Comment, Profile

from itertools import chain

#Used for old search method
from functools import reduce
stop_words = {'of', 'and', 'on', 'a', 'is', 'an', 'at', 'the', 'in', 'my', 'i', 'as', 'that', 'it'}

# Create your views here.
def home(request):
    q = request.GET.get('q', '') .split()
    page_num = int(request.GET.get('page', '1'))
    sort_by = request.GET.get('sort_by', '')

    if sort_by == 'feed':
        if not request.user.is_authenticated:
            return redirect('login')
        following = request.user.profile.following.all()
        posts = Post.objects.filter(Q(user__in=following) | Q(favorites__in=following)).order_by('-created').distinct('created', 'id')
        tags = Tag.objects.all()[:50]
    elif q:
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
        
        #returns all tags that share a post with given tag | UPDATE THIS: use method used in user search
        search_vector_tags = SearchVector('post__tags__name')
        search_rank_tags = SearchRank(search_vector_tags, search_query)

        if sort_by == 'popular': #USES OLD METHOD SEARCH SINCE REVELANCY IS NOT IMPORTANT, AND FULL TEXT SEARCH W/ ANNOTATIONS BREAKS IT
            querylist = list(filter(lambda a: True if not a.lower() in stop_words else False, q))
            post_query = reduce(lambda a, b: a & b, [Q(tags__name__icontains=query) | Q(user__username__icontains=query) | Q(title__icontains=query) for query in querylist])
            tag_query = reduce(lambda a, b: a & b, [Q(post__tags__name__icontains=query) for query in querylist])

            posts = Post.objects.annotate(c=Count('likes', distinct=True) + Count('favorites', distinct=True)).filter(post_query).order_by('-c').distinct()
            tags = Tag.objects.annotate(c=Count('post', distinct=True)).filter(tag_query).order_by('-c')
        elif sort_by == 'newest':
            posts = Post.objects.annotate(search=search_vector).filter(search=search_query).order_by('-created').distinct('created', 'id')
            tags = Tag.objects.annotate(search=search_vector_tags).filter(search=search_query).order_by('-updated').distinct('updated', 'id')
        else:
            posts = Post.objects.annotate(search=search_vector, rank=search_rank).filter(search=search_query).order_by('-rank').distinct('rank', 'id')
            tags = Tag.objects.annotate(search=search_vector_tags, rank=search_rank_tags).filter(search=search_query).order_by('-rank').distinct('rank','id')[0:50]
    else:
        if sort_by == 'popular':
            posts = Post.objects.annotate(c=Count('likes') + Count('favorites')).order_by('-c')
            tags = Tag.objects.annotate(c=Count('post')).order_by('-c')[:50]
        else:
            posts = Post.objects.all().order_by('-created')
            tags = Tag.objects.all().order_by('-updated')[:50]
        

    
    #get 50 tags/users in show posts
    #filter(post__in=posts) does not work because annotate fucking breaks it. Instead, we will get a constant runtime of 50 by creating a list - MORE RESULTS/LESS SELECTIVE
    post_ids = [post.id for post in posts[:50]]
    #tags = Tag.objects.filter(post__id__in=post_ids).distinct()
    users = User.objects.filter(posts__id__in=post_ids).distinct()
    
    pages = Paginator(posts, 3)
    if page_num <= pages.num_pages and page_num > 0:
        posts_page = pages.page(page_num) 
    else:
        return HttpResponse('You fuckin monkey')

    query = ' '.join(q)
    return render(request, 'base/home.html', {'posts_page': posts_page, 'tags': tags, 'users':users, 'query': query, 'page_num': page_num, 'sort_by': sort_by})

def users(request):
    q = request.GET.get('q', '')
    page_num = int(request.GET.get('page', '1'))

    if q and (not q.isspace()):
        users1 = User.objects.filter(username__startswith=q).order_by('username').distinct('username')
        users2 = User.objects.filter(username__icontains=q).exclude(username__startswith=q).order_by('username').distinct('username')

        users = list(chain(users1, users2))
    else:
        users = User.objects.all().order_by('username')

    pages = Paginator(users, 25)
    if page_num <= pages.num_pages and page_num > 0:
        users_page = pages.page(page_num)
    else:
        return HttpResponse('You fuckin monkey')

    return render(request, 'base/users.html', {'users_page': users_page, 'page_num':page_num, 'query': q})

def followers(request, username, page):
    user = User.objects.filter(username=username).first()
    page_num = int(request.GET.get('page', '1'))
    q = request.GET.get('q', '')

    if not user:
        return HttpResponse("This User doesn't exist, donkey")

    if q and (not q.isspace()):
        if page == 'followers':
            users1 = User.objects.filter(profile__in=user.followers.all(), username__startswith=q).order_by('username').distinct('username')
            users2 = User.objects.filter(profile__in=user.followers.all(), username__icontains=q).exclude(username__startswith=q).order_by('username').distinct('username')

            users = list(chain(users1, users2))
        else:
            users1 = user.profile.following.filter(username__startswith=q).order_by('username').distinct('username')
            users2 = user.profile.following.filter(username__icontains=q).exclude(username__startswith=q).order_by('username').distinct('username')

            users = list(chain(users1, users2))
    else:
        if page == 'followers':
            users = User.objects.filter(profile__in=user.followers.all())
        else:
            users = user.profile.following.all()

    pages = Paginator(users, 100)
    if page_num <= pages.num_pages and page_num > 0:
        users_page = pages.page(page_num)
    else:
        return HttpResponse("This page index doesn't exist, monkey")

    return render(request, 'base/users.html', {'users_page': users_page, 'page_num':page_num})

def tags(request):
    q = request.GET.get('q', '').split()
    sort_by = request.GET.get('sort_by', '')
    page_num = int(request.GET.get('page', '1'))

    if q:
        converted_q = [f"'{word}':*" for word in q]
        converted_q = ' | '.join(converted_q)

        search_vector = SearchVector('name')
        search_query = SearchQuery(converted_q, search_type='raw')
        search_rank = SearchRank(search_vector, search_query)

        if not sort_by:
            tags = Tag.objects.annotate(search=search_vector, rank=search_rank).filter(search=search_query).order_by('-rank').distinct('rank', 'id')
        elif sort_by == 'popular':
            tags = Tag.objects.annotate(search=search_vector, c=Count('post', distinct=True)).filter(search=search_query).order_by('-c')
        else:
            tags = Tag.objects.annotate(search=search_vector).filter(search=search_query).order_by('-updated').distinct('updated', 'id')
    else:
        if not sort_by:
            tags = Tag.objects.all().order_by('name')
        elif sort_by == 'popular':
            tags = Tag.objects.annotate(c=Count('post')).order_by('-c')
        else:
            tags = Tag.objects.all().order_by('-updated')

    query = ' '.join(q)

    pages = Paginator(tags, 50)
    if page_num <= pages.num_pages and page_num > 0:
        tags_page = pages.page(page_num)
    else:
        return HttpResponse('You fuckin monkey')
    
    return render(request, 'base/tags.html', {'tags_page': tags_page, 'query': query, 'page_num': page_num, 'sort_by': sort_by})

def profile(request, username):
    page_num = int(request.GET.get('page', '1'))

    user = User.objects.filter(username=username).first()
    if not user:
        return HttpResponse('This User doesnt exist, you fucking monkey')

    posts = Post.objects.filter(user=user).order_by('-created')

    pages = Paginator(posts, 3)
    posts_page = pages.page(page_num)
    return render(request, 'base/profile.html', {'user': user, 'posts_page':posts_page, 'page_num':page_num})

def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if not user == None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Incorrect Username or Password')
            
    form = LoginForm()
    return render(request, 'base/login.html', {'form':form})

def logout_user(request):
    logout(request)
    return redirect('home')

def register_user(request):
    if request.method == 'POST':
        user_form = RegistrationForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Something went wrong brudda')


    user_form = RegistrationForm()
    profile_form = ProfileForm()
    return render(request, 'base/register.html', {'user_form': user_form, 'profile_form': profile_form})

@login_required(login_url='login')
def edit_user(request):
    if request.method == 'POST':
        user_form = EditUserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile_form.save()
        return redirect('profile', user.username)

    profile_form = ProfileForm(instance=request.user.profile)
    user_form = EditUserForm(instance=request.user)
    return render(request, 'base/edit_user.html', {'profile_form': profile_form, 'user_form': user_form})

@login_required(login_url='login')
def edit_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user = request.user, data = request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return redirect('profile', request.user)
        else:
            messages.error(request, 'Seomthing went wrong, brudda(maybe the passwords be incorrect)')

    form = PasswordChangeForm(user = request.user)
    return render(request, 'base/edit_password.html', {'form': form})

def dfs(comment, queryset):
    queryset += [comment]
    #print('ADDED:', comment.body)
    if not comment.replies.all().exists():
        return

    for reply in comment.replies.all().filter().order_by('-created'):
        #print('REPLY, GOING INTO:', reply.body, 'COMMENTSET:', queryset)
        dfs(reply, queryset)

def post(request, pk):
    post = Post.objects.filter(id=pk).first()
    if not post:
        return HttpResponse('This Post doesnt exist, you fucking monkey')

    root_comments = post.comment_set.filter(parent=None).order_by('-created').distinct('created', 'id')
    comments = []
    for comment in root_comments:
        #print('ROOT, GOING INTO:', comment.body, 'COMMENTSET:', comments)
        dfs(comment, comments)

    if request.method=='POST':
        if not request.user.is_authenticated:
            return redirect('login')
        else:
            body = request.POST.get('comment', '')

            if not body:
                return redirect('post', pk=pk)
            
            comment = Comment.objects.create(user=request.user, post=post, body=body)
            comment.save()
            return redirect('post', pk=pk)

    return render(request, 'base/post.html', {'post':post, 'comments':comments})

@login_required(login_url='login')
def reply(request, post_pk, comment_pk):
    post = Post.objects.filter(id=post_pk).first()
    comment = Comment.objects.filter(id=comment_pk).first()
    body = request.POST.get('reply', '')
    
    if not (post and comment and body):
        return HttpResponse('The post or comment you are trying to respond to does not exist, donkey. Either that or you didnt write anything in the reply, donkey.')

    depth = comment.depth + '1'

    reply = Comment.objects.create(user=request.user, parent=comment, post=post, body=body, depth=depth)
    reply.save()

    return redirect('post', pk=post_pk)

def valid_tag(tag):
    if tag.isspace() or (not tag):
        return False
    return True

@login_required(login_url="login")
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post = form.save()

            tag_list_str = request.POST.get('tags').split(',')
            tag_list_str = list(filter(valid_tag, tag_list_str))

            #create a list of tag objects from the list of tag strings
            tag_list = list(map(lambda x: x[0], [Tag.objects.get_or_create(name=x.strip()) for x in tag_list_str]))

            for tag in tag_list:
                tag.save()
                post.tags.add(tag)
            post.save()

            return redirect(f'home')
            
    form = PostForm()
    tags = Tag.objects.all()
    return render(request, 'base/create_post.html', {'form': form, 'tags':tags})

def delete_unused_tags():
    tags = Tag.objects.annotate(c=Count('post')).filter(c=0).delete()

def edit_post(request, pk):
    post = Post.objects.filter(id=pk).first()

    if not post:
        return HttpResponse('The post you are trying to edit does not exist, monkey')
    if request.user != post.user:
        return HttpResponse('Dafuq you doing here?!?!')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save()

            post.tags.clear()
            tag_list_str = request.POST.get('tags').split(',')
            tag_list_str = list(filter(valid_tag, tag_list_str))

            #create a list of tag objects from the list of tag strings
            tag_list = list(map(lambda x: x[0], [Tag.objects.get_or_create(name=x.strip()) for x in tag_list_str]))

            for tag in tag_list:
                post.tags.add(tag)
            post.save()
            delete_unused_tags()

            return redirect(f'home')

    form = PostForm(instance=post)
    tags = Tag.objects.all()
    return render(request, 'base/create_post.html', {'form': form, 'tags': tags})

def delete(request, pk, obj):
    name = obj
    if name == 'post':
        obj = Post.objects.filter(id=pk).first()
    else:
        obj = Comment.objects.filter(id=pk).first()
        
    if not obj:
        return HttpResponse('This thing you are tring to delete does not exist, donkey')
    if request.user != obj.user:
        return HttpResponse('Wtf are you doing here?')
    
    if request.method == 'POST':
        if isinstance(obj, Post):
            #obj.picture.delete() done with signals in models.py
            obj.delete()
            delete_unused_tags()
            return redirect('home')
        else:
            post = obj.post
            obj.delete()
            return redirect('post', post.id)

    return render(request, 'base/delete.html', {'obj':obj, 'name':name})

@login_required(login_url='login')
def favorite(request, pk):
    post = Post.objects.filter(id=pk).first()

    if not post:
        return HttpResponse('This thing you are trying to favorite does not exist, donkey')

    if post.favorites.filter(username=request.user.username).exists():
        post.favorites.remove(request.user)
    else:
        post.favorites.add(request.user)

    return redirect('post', post.id)

@login_required(login_url='login')
def like(request, pk, obj):
    if obj=='post':
        obj = Post.objects.filter(id=pk).first()
        post = obj
    else:
        obj = Comment.objects.filter(id=pk).first()
        post = obj.post

    if not obj:
        return HttpResponse('This thing you are trying to like does not exist, donkey')
    print(obj)

    if obj.likes.filter(username=request.user.username).exists():
        obj.likes.remove(request.user)
    else:
        obj.likes.add(request.user)

    return redirect('post', post.id)

@login_required(login_url='login')
def follow(request, username):
    user = User.objects.filter(username=username).first()

    if not user:
        return HttpResponse('The User you are trying to follow does not exist, donkey')

    if request.user.profile.following.filter(username=user.username).exists():
        request.user.profile.following.remove(user)
    else:
        request.user.profile.following.add(user)

    return redirect('profile', user.username)


        
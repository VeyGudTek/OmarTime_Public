from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.login_user, name='login'),
    path('logout', views.logout_user, name='logout'),
    path('register', views.register_user, name='register'),
    path('edit_user', views.edit_user, name='edit_user'),
    path('edit_password', views.edit_password, name='edit_password'),

    path('profile/<str:username>', views.profile, name='profile'),
    path('follow/<str:username>', views.follow, name='follow'),
    path('followers/<str:username>/<str:page>', views.followers, name='followers'),
    path('users', views.users, name='users'),
    path('tags', views.tags, name='tags'),

    path('create_post', views.create_post, name="create_post"),
    path('edit_post/<str:pk>', views.edit_post, name='edit_post'),
    path('post/<str:pk>', views.post, name="post"),

    path('delete/<str:pk>/<str:obj>', views.delete, name='delete'),
    path('reply/<str:post_pk>/<str:comment_pk>', views.reply, name='reply'),
    path('like/<str:pk>/<str:obj>', views.like, name="like"),
    path('favorite/<str:pk>', views.favorite, name='favorite')
]
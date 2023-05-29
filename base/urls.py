from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.login_user, name='login'),
    path('logout', views.logout_user, name='logout'),
    path('create_post', views.create_post, name="create_post"),
    path('post/<str:pk>', views.post, name="post"),

    path('delete/<str:pk>/<str:obj>', views.delete, name='delete'),
    path('reply/<str:post_pk>/<str:comment_pk>', views.reply, name='reply'),
    path('like/<str:pk>/<str:obj>', views.like, name="like"),
    path('favorite/<str:pk>', views.favorite, name='favorite')
]
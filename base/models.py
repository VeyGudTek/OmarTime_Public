from django.db import models
from django.contrib import admin
from tree_queries.models import TreeNode
from django.contrib.auth.models import User

from django.dispatch import receiver


class Tag(models.Model):
    name = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class TagAdmin(admin.ModelAdmin):
    search_fields = ['name']

 
class Post(models.Model):
    user = models.ForeignKey(User, related_name="posts", on_delete=models.CASCADE, null=True)
    tags = models.ManyToManyField(Tag)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    picture = models.ImageField(upload_to="images", null=True)
    likes = models.ManyToManyField(User, related_name="liked_posts", blank=True)
    favorites = models.ManyToManyField(User, related_name="favorited_posts", blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.title}'

@receiver(models.signals.pre_delete, sender=Post)
def delete_image(sender, instance, **kwargs):
    if instance.picture:
        instance.picture.delete()

@receiver(models.signals.pre_save, sender=Post)
def delete_old_image(sender, instance, **kwargs):
    old = sender.objects.filter(pk=instance.pk).first()
    if old and (not old.picture == instance.picture):
        old.picture.delete(save=False)

class PostAdmin(admin.ModelAdmin):
    search_fields = ['id', 'title', 'user__username']


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey('self', related_name="replies", on_delete=models.CASCADE, blank=True, null=True)
    depth = models.CharField(max_length=50, blank=True)
    body = models.TextField(max_length=2000)
    likes = models.ManyToManyField(User, related_name="liked_comments", blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.body[0:50]

    class Meta:
        ordering=['created']

class CommentAdmin(admin.ModelAdmin):
    search_fields = ['id', 'body', 'user__username']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    bio = models.TextField(max_length=2000, blank=True)
    following = models.ManyToManyField(User, related_name="followers", blank=True)
    avatar = models.ImageField(upload_to="avatars", null=True, blank=True)
    

    def __str__(self):
        return self.user.username

@receiver(models.signals.pre_delete, sender=Profile)
def delete_avatar(sender, instance, **kwargs):
    if instance.avatar:
        instance.avatar.delete()

@receiver(models.signals.pre_save, sender=Profile)
def delete_old_avatar(sender, instance, **kwargs):
    old = sender.objects.filter(pk=instance.pk).first()
    if old and (not old.avatar == instance.avatar):
        old.avatar.delete(save=False)

@receiver(models.signals.post_delete, sender=Profile)
def delete_user(sender, instance, **kwargs):
    try:
        instance.user.delete()
    except:
        pass

class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username']

   


from django.db import models
from tree_queries.models import TreeNode
from django.contrib.auth.models import User


class Tag(models.Model):
    name = models.CharField(max_length=200)
    
    def __str__(self):
        return self.name

 
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


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey('self', related_name="replies", on_delete=models.CASCADE, blank=True, null=True)
    depth = models.CharField(max_length=50, blank=True)
    body = models.TextField(max_length=2000)
    likes = models.ManyToManyField(User, related_name="liked_comments", symmetrical=False, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.body[0:50]

    class Meta:
        ordering=['created']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    bio = models.TextField(max_length=2000, blank=True)
    following = models.ManyToManyField('self', related_name="followers", symmetrical = False, blank=True)
    

    def __str__(self):
        return self.user.username

   


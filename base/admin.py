from django.contrib import admin
from .models import Profile, Post, Comment, Tag
from .models import ProfileAdmin, PostAdmin, CommentAdmin, TagAdmin

# Register your models here.
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Tag, TagAdmin)

from django.db import models

class User(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    profile_pic = models.CharField(max_length=255, default='default.png')
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
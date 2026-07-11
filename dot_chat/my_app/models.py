from django.db import models

class User(models.Model):
    id = models.AutoField(primary_key=True)
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        null=False, 
        blank=False,
        db_index=True,
        help_text="Supports international numbers"
    )
    username = models.CharField(
        max_length=50, 
        unique=True, 
        null=False, 
        blank=False,
        db_index=True
    )
    profile_pic = models.CharField(
        max_length=255, 
        default='default.png',
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


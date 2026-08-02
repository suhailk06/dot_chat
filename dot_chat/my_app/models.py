from django.db import models
from django.conf import settings

class UserData(models.Model):
    id = models.AutoField(primary_key=True)  # Primary key starting from 1001 (set via migration)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    profile_pic = models.CharField(max_length=255, default='default.png')
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    

    
    def __str__(self):
        return self.username

class MessageData(models.Model):
    message = models.TextField(max_length=4000)
    sender = models.ForeignKey(
        UserData, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
        # No to_field parameter - defaults to primary key (id)
    )
    receiver = models.ForeignKey(
        UserData, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
        # No to_field parameter - defaults to primary key (id)
    )
    message_time = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
    
class FriendListDATA(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        UserData, 
        on_delete=models.CASCADE, 
        related_name='friends'
    )
    friend = models.ForeignKey(
        UserData, 
        on_delete=models.CASCADE, 
        related_name='friend_of'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status=models.CharField(default="pending",max_length=100)
    
    
    def __str__(self):
        return f"{self.user.username} <-> {self.friend.username}"
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password

from my_app.models import UserData

class UserForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    bio = forms.CharField(widget=forms.Textarea, required=False)
    profile_pic = forms.ImageField(required=False)
    
    class Meta:
        model = UserData
        fields = ['username', 'email', 'password1', 'confirm_password', 'bio', 'profile_pic']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if UserData.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if UserData.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password1 and confirm_password and password1 != confirm_password:
            raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data['password1'])  # Hash the password
        if commit:
            user.save()
        return user
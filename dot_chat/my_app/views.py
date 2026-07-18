from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password
from my_app.forms import UserForm
from my_app.models import UserData

def index(request):

    return render(request, 'index.html')

# @login_required(login_url='login')
def home(request):
    users = UserData.objects.all()  # Changed to UserData
    return render(request, 'home.html', {'users': users})

def register_page(request):
    # If user is already logged in, redirect to home
    if 'user_id' in request.session:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Save the user with hashed password
            user = form.save()
            
            # Handle profile pic upload
            if 'profile_pic' in request.FILES:
                profile_pic = request.FILES['profile_pic']
                # Save the file (you need to handle file storage)
                # For now, just save the filename
                user.profile_pic = profile_pic.name
                user.save()
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    
    else:
        form = UserForm()
    
    return render(request, 'register.html', {'form': form})

def login_page(request):
    # If user is already logged in, redirect to home
    if 'user_id' in request.session:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate using custom UserData model
        try:
            user_data = UserData.objects.get(username=username)
            # Check password using Django's check_password
            if check_password(password, user_data.password):
                messages.success(request, f'Welcome {username}! You are now logged in.')
                # Store user_id in session
                request.session['user_id'] = user_data.id
                request.session['username'] = user_data.username
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        except UserData.DoesNotExist:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')



def logout_page(request):
    # Method 1: Clear specific session keys
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'username' in request.session:
        del request.session['username']
    if 'user_email' in request.session:
        del request.session['user_email']
    logout(request)
    

    messages.success(request, 'You have been logged out successfully.')

    return redirect('login')
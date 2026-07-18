from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from my_app.forms import UserForm
from my_app.models import MessageData, UserData

def index(request):
    return render(request, 'index.html')

def home(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    users = UserData.objects.exclude(id=request.session.get('user_id'))
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
    # Clear session keys
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'username' in request.session:
        del request.session['username']
    if 'user_email' in request.session:
        del request.session['user_email']
    
    # Flush the session completely
    request.session.flush()
    
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def message_page(request, receiver_id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        messages.error(request, 'Please login first.')
        return redirect('login')
    
    sender_id = request.session.get('user_id')
    sender = UserData.objects.get(id=sender_id)
    receiver = UserData.objects.get(id=receiver_id)
 
    
    # Handle POST request - Sending a message
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if message_text:
            # Create new message
            new_message = MessageData.objects.create(
                message=message_text,
                sender=sender,
                receiver=receiver
            )
            messages.success(request, f'Message sent to {receiver.username}!')
        else:
            messages.error(request, 'Message cannot be empty.')
        
        # Redirect to the same page to avoid form resubmission
        return redirect('message_page', receiver_id=receiver_id)
    
    # Handle GET request - Display the chat page
    # Get all messages between sender and receiver
    messages_list = MessageData.objects.filter(
        Q(sender=sender, receiver=receiver) |
        Q(sender=receiver, receiver=sender)
    ).order_by('message_time')
    
    return render(request, 'message_page.html', {
        'sender': sender,
        'receiver': receiver,
        'receiver_id': receiver_id,
        'sender_id': sender_id,
        'messages': messages_list,
        'username': sender.username,
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from my_app.forms import UserForm
from my_app.models import MessageData, UserData, FriendListDATA
from django.db.models import Q

def index(request):
    return render(request, 'index.html')

def home(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    # Get list of friend IDs where status is 'friend'
    friend_ids = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') | 
        Q(friend_id=user_id, status='friend')
    ).values_list('friend_id', flat=True)
    
    # Also get users who have added the current user as friend
    friend_ids_from_others = FriendListDATA.objects.filter(
        Q(friend_id=user_id, status='friend')
    ).values_list('user_id', flat=True)
    
    # Combine both lists
    all_friend_ids = list(friend_ids) + list(friend_ids_from_others)
    # Remove duplicates and self
    all_friend_ids = [fid for fid in set(all_friend_ids) if fid != user_id]
    
    # Get user data for those friends
    friends = UserData.objects.filter(id__in=all_friend_ids)
    
    return render(request, 'home.html', {'friends': friends})

def search_page(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    # Get IDs of users who are already friends
    friend_ids = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') | 
        Q(friend_id=user_id, status='friend')
    ).values_list('friend_id', flat=True)
    
    # Get user_ids from reversed friendships
    friend_ids_from_others = FriendListDATA.objects.filter(
        Q(friend_id=user_id, status='friend')
    ).values_list('user_id', flat=True)
    
    # Combine and remove duplicates
    all_friend_ids = set(friend_ids) | set(friend_ids_from_others)
    all_friend_ids.discard(user_id)  # Remove self
    
    # Get users excluding friends
    users = UserData.objects.exclude(id=user_id).exclude(id__in=all_friend_ids)
    
    # Add status for each user
    for user in users:
        # Check for pending requests
        pending_sent = FriendListDATA.objects.filter(
            user_id=user_id, 
            friend_id=user.id, 
            status='pending'
        ).exists()
        
        pending_received = FriendListDATA.objects.filter(
            user_id=user.id, 
            friend_id=user_id, 
            status='pending'
        ).exists()
        
        if pending_sent:
            user.status = 'pending_sent'
        elif pending_received:
            user.status = 'pending_received'
        else:
            user.status = 'none'
    
    return render(request, 'search_page.html', {'users': users})

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
    
    # Check if users are friends (optional but recommended)
    are_friends = FriendListDATA.objects.filter(
        Q(user_id=sender_id, friend_id=receiver_id, status='friend') |
        Q(user_id=receiver_id, friend_id=sender_id, status='friend')
    ).exists()
    
    if not are_friends:
        messages.warning(request, f'You are not friends with {receiver.username}. Messages may be limited.')
    
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
        'are_friends': are_friends,
    })

def add_friend(request, receiver_id):
    if 'user_id' not in request.session:
        messages.error(request, 'Please login first.')
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    if user_id == receiver_id:
        messages.error(request, "You cannot add yourself as a friend.")
        return redirect('search_page')
    
    try:
        user = UserData.objects.get(id=user_id)
        friend = UserData.objects.get(id=receiver_id)
        
        # Check if friendship already exists in either direction
        existing_friendship = FriendListDATA.objects.filter(
            Q(user_id=user_id, friend_id=receiver_id) |
            Q(user_id=receiver_id, friend_id=user_id)
        ).first()
        
        if existing_friendship:
            if existing_friendship.status == 'friend':
                messages.warning(request, f"You are already friends with {friend.username}.")
            elif existing_friendship.status == 'pending':
                # If the other user sent the request, accept it
                if existing_friendship.user_id == receiver_id:
                    existing_friendship.status = 'friend'
                    existing_friendship.save()
                    messages.success(request, f"You accepted {friend.username}'s friend request!")
                else:
                    messages.info(request, f"You already sent a friend request to {friend.username}.")
            elif existing_friendship.status == 'blocked':
                messages.error(request, f"You cannot add {friend.username} to your friends.")
            else:
                messages.warning(request, f"You are already in {friend.username}'s friend list.")
        else:
            # Create new friend request
            friendship = FriendListDATA.objects.create(
                user=user,
                friend=friend,
                status='pending'
            )
            messages.success(request, f"Friend request sent to {friend.username}!")
            
    except UserData.DoesNotExist:
        messages.error(request, "User not found.")
    
    return redirect('search_page')
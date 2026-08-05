from email.mime import message
import random

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
from django.core.mail import send_mail
from django.conf import settings

def index(request):
    return render(request, 'index.html')

def home(request):
    # Check if user is logged in
    if 'user_id' not in request.session or not UserData.objects.filter(
        id=request.session['user_id'], 
        is_verified=True
    ).exists():
        return redirect('login')

    user_id = request.session.get('user_id')
    users = UserData.objects.exclude(id=user_id)
    req=0
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
            
            if pending_received:
                user.status = 'pending_received'
                req+=1

    
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
    unseen_messages = set(MessageData.objects.filter(
    receiver_id=user_id, seen=False).values_list('sender_id', flat=True))
    print("Unseen messages from user IDs:", unseen_messages)
    return render(request, 'home.html', {'friends': friends,'req':req,'unseen_messages': unseen_messages})


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
    req=0
    
    # Create lists to categorize users
    pending_received_users = []
    pending_sent_users = []
    no_status_users = []
    
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
            pending_sent_users.append(user)
        elif pending_received:
            user.status = 'pending_received'
            pending_received_users.append(user)
            req += 1
        else:
            user.status = 'none'
            no_status_users.append(user)
    
    # Combine the lists in the desired order
    ordered_users = pending_received_users + pending_sent_users + no_status_users
    
    return render(request, 'search_page.html', {'users': ordered_users, 'req': req})

def verify_otp(request, user_id,otp_code):
    if request.method == 'POST':
        otp= request.POST.get('otp')
        if otp==otp_code:
            user = UserData.objects.get(id=user_id)
            user.is_verified = True
            user.save()
            messages.success(request, 'Your account has been verified. You can now log in.')
            return redirect('login')
    return render(request, 'verify_otp.html', {'user_id': user_id, 'otp_code': otp_code})

def register_page(request):
    # If user is already logged in, redirect to home
    UserData.objects.filter(is_verified=False).delete()
    if 'user_id' in request.session:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES)
        email = request.POST.get('email')
        if form.is_valid():
            # Save the user with hashed password
            user = form.save()
            otp=str(random.randint(100000, 999999))  # Generate a random 6-digit OTP
            message = f"Your verification code is: {otp}"
            send_mail(
                    "Verification Code",
                    message,  # Now this is a string
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,)
            
            
            # Handle profile pic upload
            if 'profile_pic' in request.FILES:
                profile_pic = request.FILES['profile_pic']
                # Save the file (you need to handle file storage)
                # For now, just save the filename
                user.profile_pic = profile_pic.name
                user.save()
            
            return redirect('verify_otp', user_id=user.id, otp_code=otp)
        else:
            messages.error(request, 'Something went wrong!')
    
    else:
        form = UserForm()
    
    return render(request, 'register.html', {'form': form})

def login_page(request):
    # If user is already logged in, redirect to home
    UserData.objects.filter(is_verified=False).delete()
    if 'user_id' in request.session:
        return redirect('home')  # Redirect to home if already logged in
    
    # Rest of your login page logic (show login form, etc.)
    # Rest of your view logic...
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate using custom UserData model
        try:
            user_data = UserData.objects.get(username=username)
            # Check password using Django's check_password
            if check_password(password, user_data.password):
                # Store user_id in session
                request.session['user_id'] = user_data.id
                request.session['username'] = user_data.username
                return redirect('home')
            else:
                messages.error(request, 'Wrong username or password!') # Invalid credentials will be handled in template
        except UserData.DoesNotExist:
            messages.error(request, 'Username does not exist!') # Invalid credentials will be handled in template
    
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
    
    return redirect('login')

def message_page(request, receiver_id):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    sender_id = request.session.get('user_id')
    sender = UserData.objects.get(id=sender_id)
    receiver = UserData.objects.get(id=receiver_id)
    
    # Check if users are friends (optional but recommended)
    are_friends = FriendListDATA.objects.filter(
        Q(user_id=sender_id, friend_id=receiver_id, status='friend') |
        Q(user_id=receiver_id, friend_id=sender_id, status='friend')
    ).exists()
    pending_message=MessageData.objects.filter(
        Q(sender=receiver, receiver=sender, seen=False)
    )
    
    for msg in pending_message:
        msg.seen=True
        msg.save()
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
        else:
            pass  # Empty message will be handled in template
        
        # Redirect to the same page to avoid form resubmission
        return redirect('message_page', receiver_id=receiver_id,)
    
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
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    if user_id == receiver_id:
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
                pass  # Already friends
            elif existing_friendship.status == 'pending':
                # If the other user sent the request, accept it
                if existing_friendship.user_id == receiver_id:
                    existing_friendship.status = 'friend'
                    existing_friendship.save()
                else:
                    pass  # Request already sent
            elif existing_friendship.status == 'blocked':
                pass  # Cannot add blocked user
            else:
                pass  # Already in friend list
        else:
            # Create new friend request
            friendship = FriendListDATA.objects.create(
                user=user,
                friend=friend,
                status='pending'
            )
            
    except UserData.DoesNotExist:
        pass  # User not found
    
    return redirect('search_page')

def delete_friend(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    try:
        # Check if friendship exists in either direction
        friendship = FriendListDATA.objects.filter(
            Q(user_id=user_id, friend_id=receiver_id) |
            Q(user_id=receiver_id, friend_id=user_id)
        ).first()
        
        if friendship:
            friendship.delete()  # Delete the friendship
    except FriendListDATA.DoesNotExist:
        pass  # Friendship not found
    
    return redirect('home')
def cancel_friend_request(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    try:
        # Check if a pending friend request exists from the current user to the receiver
        pending_request = FriendListDATA.objects.filter(
            user_id=user_id,
            friend_id=receiver_id,
            status='pending'
        ).first()
        
        if pending_request:
            pending_request.delete()  # Cancel the friend request
    except FriendListDATA.DoesNotExist:
        pass  # No pending request found
    
    return redirect('search_page')
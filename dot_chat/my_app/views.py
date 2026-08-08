from email.mime import message
import random
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q
from numpy import append
from my_app.forms import UserForm
from my_app.models import MessageData, UserData, FriendListDATA
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.storage import default_storage

def index(request):
    # Clear all session data
    session_keys = ['user_id', 'username', 'user_email']
    for key in session_keys:
        if key in request.session:
            del request.session[key]
    request.session.flush()
    return render(request, 'index.html')

def home(request):
    if 'user_id' not in request.session or not UserData.objects.filter(
        id=request.session['user_id'], 
        is_verified=True
    ).exists():
        return redirect('login')

    user_id = request.session.get('user_id')
    users = UserData.objects.exclude(id=user_id)
    req = 0
    
    for user in users:
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
            req += 1

    # Get friend IDs
    friend_ids = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') | 
        Q(friend_id=user_id, status='friend')
    ).values_list('friend_id', flat=True)
    
    friend_ids_from_others = FriendListDATA.objects.filter(
        Q(friend_id=user_id, status='friend')
    ).values_list('user_id', flat=True)
    
    all_friend_ids = list(set(friend_ids) | set(friend_ids_from_others))
    all_friend_ids = [fid for fid in all_friend_ids if fid != user_id]
    
    friends = UserData.objects.filter(id__in=all_friend_ids)
    unseen_messages = set(MessageData.objects.filter(
        receiver_id=user_id, seen=False).values_list('sender_id', flat=True))
    
    user = UserData.objects.get(id=user_id)
    return render(request, 'home.html', {
        'friends': friends, 
        'req': req, 
        'unseen_messages': unseen_messages, 
        'user': user
    })

def user_profile(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user = UserData.objects.get(id=user_id)
    
    # Get friend relationships
    friend_list = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') |
        Q(friend_id=user_id, status='friend')
    )

    friend_ids = set()
    for friendship in friend_list:
        if friendship.user_id == user_id:
            friend_ids.add(friendship.friend_id)
        else:
            friend_ids.add(friendship.user_id)
            
    # Determine friend status
    current_user_id = request.session.get('user_id')
    if user_id == current_user_id:
        friend_status = "self"
    elif FriendListDATA.objects.filter(
        user_id=current_user_id, friend_id=user_id, status='friend'
    ).exists() or FriendListDATA.objects.filter(
        user_id=user_id, friend_id=current_user_id, status='friend'
    ).exists():
        friend_status = "friend"
    elif FriendListDATA.objects.filter(
        user_id=current_user_id, friend_id=user_id, status='pending'
    ).exists():
        friend_status = "pending_sent"
    elif FriendListDATA.objects.filter(
        user_id=user_id, friend_id=current_user_id, status='pending'
    ).exists():
        friend_status = "pending_received"
    
    return render(request, 'user_profile_page.html', {
        'user': user,
        'friend_ids': friend_ids,
        'friend_status': friend_status
    })

def friend_list(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')

    req = 0
    friends_list = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') |
        Q(friend_id=user_id, status='friend')
    )
    
    friends_ids = set()
    for friendship in friends_list:
        if friendship.user_id == user_id:
            friends_ids.add(friendship.friend_id)
        else:
            friends_ids.add(friendship.user_id)
    
    friends_idx = UserData.objects.filter(id__in=friends_ids)
    
    # Categorize users
    self_user = []
    friend_users = []
    pending_received_users = []
    pending_sent_users = []
    no_status_users = []
    
    current_user_id = request.session.get('user_id')
    
    for user in friends_idx:
        friend = FriendListDATA.objects.filter(
            Q(user_id=current_user_id, friend_id=user.id) | 
            Q(user_id=user.id, friend_id=current_user_id)
        ).first()
        
        pending_sent = FriendListDATA.objects.filter(
            user_id=current_user_id, 
            friend_id=user.id, 
            status='pending'
        ).exists()
        
        pending_received = FriendListDATA.objects.filter(
            user_id=user.id, 
            friend_id=current_user_id, 
            status='pending'
        ).exists()
        
        if user.id == current_user_id:
            user.status = 'self'
            self_user.append(user)
        elif friend:
            user.status = 'friend'
            friend_users.append(user)
        elif pending_sent:
            user.status = 'pending_sent'
            pending_sent_users.append(user)
        elif pending_received:
            user.status = 'pending_received'
            pending_received_users.append(user)
            req += 1
        else:
            user.status = 'none'
            no_status_users.append(user)
    
    ordered_users = self_user + friend_users + pending_received_users + pending_sent_users + no_status_users
    return render(request, 'friend_list_page.html', {'friends': ordered_users})

def search_page(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    # Get friend IDs
    friend_ids = FriendListDATA.objects.filter(
        Q(user_id=user_id, status='friend') | 
        Q(friend_id=user_id, status='friend')
    ).values_list('friend_id', flat=True)
    
    friend_ids_from_others = FriendListDATA.objects.filter(
        Q(friend_id=user_id, status='friend')
    ).values_list('user_id', flat=True)
    
    all_friend_ids = set(friend_ids) | set(friend_ids_from_others)
    all_friend_ids.discard(user_id)
    
    # Get non-friend users
    users = UserData.objects.exclude(id=user_id).exclude(id__in=all_friend_ids)
    req = 0
    
    pending_received_users = []
    pending_sent_users = []
    no_status_users = []
    
    for user in users:
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
    
    ordered_users = pending_received_users + pending_sent_users + no_status_users
    return render(request, 'search_page.html', {'users': ordered_users, 'req': req})

def verify_otp(request, user_id):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        if otp == request.session.get('otp'):
            user = UserData.objects.get(id=user_id)
            user.is_verified = True
            user.save()
            messages.success(request, 'Your account has been verified. You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp', user_id=user_id)
    return render(request, 'verify_otp.html', {'user_id': user_id})

def register_page(request):
    UserData.objects.filter(is_verified=False).delete()
    
    if 'user_id' in request.session:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('conform_password', '')
        profile_pic = request.FILES.get('profile_pic')
        
        errors = {}
        
        # Validate username
        if not username:
            errors['username'] = 'Username is required.'
        elif UserData.objects.filter(username=username).exists():
            errors['username'] = 'This username is already taken.'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters long.'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors['username'] = 'Username can only contain letters, numbers, and underscores.'
        
        # Validate email
        if not email:
            errors['email'] = 'Email is required.'
        elif UserData.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered.'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors['email'] = 'Please enter a valid email address.'
        
        # Validate password
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters long.'
        elif password.isdigit():
            errors['password'] = 'Password cannot be entirely numeric.'
        elif not any(char.isupper() for char in password):
            errors['password'] = 'Password must contain at least one uppercase letter.'
        elif not any(char.islower() for char in password):
            errors['password'] = 'Password must contain at least one lowercase letter.'
        elif not any(char.isdigit() for char in password):
            errors['password'] = 'Password must contain at least one number.'
        
        # Validate confirm password
        if not confirm_password:
            errors['confirm_password'] = 'Please confirm your password.'
        elif password and confirm_password and password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'
        
        if errors:
            context = {
                'username': username,
                'email': email,
                'errors': errors
            }
            return render(request, 'register.html', context)
        
        try:
            otp = str(random.randint(100000, 999999))
            
            user = UserData.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                verified_otp=otp,
                is_verified=False
            )
            
            if profile_pic:
                try:
                    file_path = default_storage.save(f'profile_pics/{profile_pic.name}', profile_pic)
                    user.profile_pic = file_path
                    user.save()
                except Exception as e:
                    print(f"Profile picture upload failed: {e}")
            
            request.session['otp'] = otp
            request.session['user_id'] = user.id
            
            try:
                email_message = f"Your verification code is: {otp}"
                send_mail(
                    "Email Verification Code",
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'Registration successful! Please verify your email.')
            except Exception as e:
                messages.warning(request, f'Registration successful but email failed: {str(e)}')
            
            return redirect('verify_otp', user_id=user.id)
            
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'register.html')
    
    return render(request, 'register.html')

def login_page(request):
    UserData.objects.filter(is_verified=False).delete()
    
    if 'user_id' in request.session:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user_data = UserData.objects.get(username=username)
            if check_password(password, user_data.password):
                request.session['user_id'] = user_data.id
                request.session['username'] = user_data.username
                return redirect('home')
            else:
                messages.error(request, 'Wrong username or password!')
        except UserData.DoesNotExist:
            messages.error(request, 'Username does not exist!')
    
    return render(request, 'login.html')

def logout_page(request):
    session_keys = ['user_id', 'username', 'user_email']
    for key in session_keys:
        if key in request.session:
            del request.session[key]
    request.session.flush()
    return redirect('login')

def message_page(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    sender_id = request.session.get('user_id')
    sender = UserData.objects.get(id=sender_id)
    receiver = UserData.objects.get(id=receiver_id)
    
    # Mark messages as seen
    pending_messages = MessageData.objects.filter(
        Q(sender=receiver, receiver=sender, seen=False)
    )
    for msg in pending_messages:
        msg.seen = True
        msg.save()
    
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if message_text:
            new_message = MessageData.objects.create(
                message=message_text,
                sender=sender,
                receiver=receiver
            )

        
        return redirect('message_page', receiver_id=receiver_id)
    
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

def add_friend(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    if user_id == receiver_id:
        return redirect('search_page')
    
    try:
        user = UserData.objects.get(id=user_id)
        friend = UserData.objects.get(id=receiver_id)
        
        existing_friendship = FriendListDATA.objects.filter(
            Q(user_id=user_id, friend_id=receiver_id) |
            Q(user_id=receiver_id, friend_id=user_id)
        ).first()
        
        if existing_friendship:
            if existing_friendship.status == 'pending' and existing_friendship.user_id == receiver_id:
                existing_friendship.status = 'friend'
                existing_friendship.save()
                
                # Send email notification for accepted friend request
                try:
                    subject = f"Friend request accepted by {user.username}"
                    email_body = f"Your friend request to {user.username} has been accepted! You are now friends on Dot Chat."
                    send_mail(
                        subject,
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [friend.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Email notification failed: {e}")
        else:
            FriendListDATA.objects.create(
                user=user,
                friend=friend,
                status='pending'
            )
            
            # Send email notification for new friend request
            try:
                subject = f"New friend request from {user.username}"
                email_body = f"You have received a new friend request from {user.username} on Dot Chat.\n\nLog in to accept or reject this request."
                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [friend.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Email notification failed: {e}")
            
    except UserData.DoesNotExist:
        pass
    
    return redirect('search_page')

def delete_friend(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    try:
        friendship = FriendListDATA.objects.filter(
            Q(user_id=user_id, friend_id=receiver_id) |
            Q(user_id=receiver_id, friend_id=user_id)
        ).first()
        
        if friendship:
            friendship.delete()
    except FriendListDATA.DoesNotExist:
        pass
    
    return redirect('home')

def cancel_friend_request(request, receiver_id):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session.get('user_id')
    
    try:
        pending_request = FriendListDATA.objects.filter(
            user_id=user_id,
            friend_id=receiver_id,
            status='pending'
        ).first()
        
        if pending_request:
            pending_request.delete()
    except FriendListDATA.DoesNotExist:
        pass
    
    return redirect('search_page')
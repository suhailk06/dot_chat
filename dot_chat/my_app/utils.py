# utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_otp_email(user, otp_code, purpose="login"):
    """Send OTP via email"""
    
    subject = f"Your OTP for {purpose}"
    context = {
        'user': user,
        'otp_code': otp_code,
        'purpose': purpose,
        'expiry_minutes': settings.EMAIL_OTP_EXPIRY_MINUTES
    }
    
    # HTML email template
    html_message = render_to_string('email/otp_email.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}")
        return False
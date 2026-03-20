"""
E-GameScout OTP Authentication Service
Secure, centralized OTP management with industry-standard practices

Features:
- Hashed OTP storage (not plaintext)
- Automatic expiry tracking
- Brute-force protection
- Rate limiting
- Clean session management
"""

import random
import time
from typing import Tuple, Dict, Optional
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """
    Centralized OTP Service
    Handles generation, storage, validation, and security
    """

    # Configuration pulled from Django settings
    OTP_EXPIRY = getattr(settings, 'OTP_EXPIRY_SECONDS', 300)  # 5 minutes default
    OTP_MAX_ATTEMPTS = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)  # Max verification attempts
    OTP_REQUEST_LIMIT = getattr(settings, 'OTP_REQUEST_LIMIT', 3)  # Max OTP requests
    OTP_REQUEST_LIMIT_WINDOW = getattr(settings, 'OTP_REQUEST_LIMIT_WINDOW', 900)  # 15 minutes
    OTP_LENGTH = getattr(settings, 'OTP_LENGTH', 6)  # 6-digit OTP

    @staticmethod
    def generate_otp() -> str:
        """
        Generate a random OTP of specified length (default 6 digits)
        Returns: String OTP (e.g., "123456")
        """
        min_value = 10 ** (OTPService.OTP_LENGTH - 1)
        max_value = (10 ** OTPService.OTP_LENGTH) - 1
        return str(random.randint(min_value, max_value))

    @staticmethod
    def _get_otp_cache_key(email: str, key_type: str = "otp") -> str:
        """
        Generate cache key for OTP storage
        Prevents conflicts with other cache keys
        """
        return f"otp_{key_type}_{email.lower()}"

    @staticmethod
    def _get_attempt_cache_key(email: str) -> str:
        """Generate cache key for tracking failed attempts"""
        return f"otp_attempts_{email.lower()}"

    @staticmethod
    def _get_request_limit_cache_key(email: str) -> str:
        """Generate cache key for rate limiting OTP requests"""
        return f"otp_requests_{email.lower()}"

    @classmethod
    def store_otp(cls, email: str) -> Tuple[bool, str, Dict]:
        """
        Generate and store OTP securely
        
        Returns:
            Tuple of (success: bool, otp: str or error_message, metadata: dict)
        
        Example:
            success, otp, metadata = OTPService.store_otp('user@example.com')
            if success:
                print(f"OTP stored, expires in {metadata['expiry_seconds']}s")
        """
        email = email.lower().strip()
        
        # ===== RATE LIMITING CHECK =====
        # Prevent OTP request spam
        request_limit_key = cls._get_request_limit_cache_key(email)
        request_count = cache.get(request_limit_key, 0)
        
        if request_count >= cls.OTP_REQUEST_LIMIT:
            error_msg = f"Too many OTP requests. Please try again after 15 minutes."
            logger.warning(f"OTP request limit exceeded for {email}")
            return False, error_msg, {"error_code": "rate_limit_exceeded"}
        
        # Generate OTP
        otp = cls.generate_otp()
        
        # ===== SECURE STORAGE =====
        # Hash the OTP before storing (never store plaintext)
        hashed_otp = make_password(otp)
        
        # Create metadata with timestamp
        otp_metadata = {
            "hashed_otp": hashed_otp,
            "created_at": time.time(),  # Store as Unix timestamp
            "expiry_seconds": cls.OTP_EXPIRY
        }
        
        # Store in cache with auto-expiry
        cache_key = cls._get_otp_cache_key(email)
        cache.set(cache_key, otp_metadata, timeout=cls.OTP_EXPIRY)
        
        # Reset failed attempts counter
        attempts_key = cls._get_attempt_cache_key(email)
        cache.delete(attempts_key)
        
        # Update request counter
        request_count += 1
        cache.set(request_limit_key, request_count, timeout=cls.OTP_REQUEST_LIMIT_WINDOW)
        
        # Log for audit trail (without exposing OTP)
        logger.info(f"OTP generated for {email} (hash: {hashed_otp[:20]}...)")
        
        return True, otp, {
            "expiry_seconds": cls.OTP_EXPIRY,
            "expiry_minutes": cls.get_otp_expiry_minutes()
        }

    @classmethod
    def verify_otp(cls, email: str, otp_input: str) -> Tuple[bool, str]:
        """
        Verify OTP with security checks
        
        Returns:
            Tuple of (success: bool, message: str)
        
        Security checks:
        1. OTP exists and not expired
        2. OTP hasn't exceeded max attempts
        3. OTP matches (timing-safe comparison)
        """
        email = email.lower().strip()
        otp_input = str(otp_input).strip()
        
        cache_key = cls._get_otp_cache_key(email)
        otp_metadata = cache.get(cache_key)
        
        # ===== CHECK 1: OTP EXISTS =====
        if not otp_metadata:
            logger.warning(f"OTP verification failed: OTP not found or expired for {email}")
            return False, "OTP expired or invalid. Please request a new one."
        
        # ===== CHECK 2: CHECK EXPIRY =====
        created_at = otp_metadata.get("created_at")
        current_time = time.time()
        elapsed = current_time - created_at
        
        if elapsed > cls.OTP_EXPIRY:
            cls.clear_otp(email)
            logger.warning(f"OTP verification failed: OTP expired for {email} (elapsed: {elapsed}s)")
            return False, "OTP has expired. Please request a new one."
        
        # ===== CHECK 3: CHECK ATTEMPT COUNT =====
        attempts_key = cls._get_attempt_cache_key(email)
        failed_attempts = cache.get(attempts_key, 0)
        
        if failed_attempts >= cls.OTP_MAX_ATTEMPTS:
            cls.clear_otp(email)
            logger.error(f"OTP verification blocked: Max attempts exceeded for {email}")
            return False, f"Too many failed attempts. OTP has been invalidated. Please request a new one."
        
        # ===== CHECK 4: VERIFY OTP (TIMING-SAFE) =====
        # Use Django's check_password for timing-safe comparison
        # This prevents timing attacks where attacker can determine correct OTP char by char
        stored_hash = otp_metadata.get("hashed_otp")
        
        if not check_password(otp_input, stored_hash):
            # Increment failed attempts
            failed_attempts += 1
            cache.set(attempts_key, failed_attempts, timeout=cls.OTP_EXPIRY)
            
            remaining_attempts = cls.OTP_MAX_ATTEMPTS - failed_attempts
            logger.warning(f"OTP verification failed for {email}: Invalid OTP (attempts: {failed_attempts}/{cls.OTP_MAX_ATTEMPTS})")
            
            if remaining_attempts > 0:
                return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
            else:
                cls.clear_otp(email)
                return False, "Too many failed attempts. OTP has been invalidated. Please request a new one."
        
        # ===== SUCCESS: OTP VERIFIED =====
        cls.clear_otp(email)
        logger.info(f"OTP verified successfully for {email}")
        return True, "OTP verified successfully"

    @classmethod
    def clear_otp(cls, email: str) -> None:
        """
        Clear all OTP-related session/cache data
        Should be called after successful verification or expiry
        
        Clears:
        - OTP hash and metadata
        - Attempt counter
        """
        email = email.lower().strip()
        
        # Delete OTP metadata
        otp_key = cls._get_otp_cache_key(email)
        cache.delete(otp_key)
        
        # Delete attempt counter
        attempts_key = cls._get_attempt_cache_key(email)
        cache.delete(attempts_key)
        
        logger.debug(f"OTP data cleared for {email}")

    @classmethod
    def get_otp_expiry_minutes(cls) -> int:
        """Return OTP expiry time in minutes"""
        otp_expiry_seconds = int(cls.OTP_EXPIRY or 300)
        return max(1, (otp_expiry_seconds + 59) // 60)

    @classmethod
    def is_otp_expired(cls, email: str) -> bool:
        """Check if OTP for email has expired or doesn't exist"""
        cache_key = cls._get_otp_cache_key(email)
        otp_metadata = cache.get(cache_key)
        
        if not otp_metadata:
            return True
        
        created_at = otp_metadata.get("created_at")
        elapsed = time.time() - created_at
        return elapsed > cls.OTP_EXPIRY

    @classmethod
    def get_otp_attempts_remaining(cls, email: str) -> Optional[int]:
        """
        Get remaining OTP verification attempts
        Returns None if OTP doesn't exist
        """
        attempts_key = cls._get_attempt_cache_key(email)
        failed_attempts = cache.get(attempts_key, 0)
        
        cache_key = cls._get_otp_cache_key(email)
        if not cache.get(cache_key):
            return None
        
        return cls.OTP_MAX_ATTEMPTS - failed_attempts


class EmailService:
    """Email sending with secure OTP delivery"""

    @staticmethod
    def send_otp_email(email: str, otp: str, template_name: str = 'web/emails/otp_verification.html',
                      context_extras: Dict = None, subject: str = 'Your E-Game Scout Verification Code') -> Tuple[bool, str]:
        """
        Send OTP via email with proper headers and security
        
        Args:
            email: Recipient email
            otp: Plain OTP (will be shown in email)
            template_name: Email template path
            context_extras: Additional template context
            subject: Email subject
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            context = {
                "otp": otp,
                "email": email,
                "expiry_minutes": OTPService.get_otp_expiry_minutes(),
                "logo_url": None,  # Will be set by template context processor
            }
            
            # Merge with additional context
            if context_extras:
                context.update(context_extras)
            
            # Render HTML template
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Create email
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@egamescout.com',
                to=[email],
            )
            
            # Add HTML alternative
            email_obj.attach_alternative(html_message, "text/html")
            
            # Add security headers
            email_obj.extra_headers = {
                'X-Priority': '1',
                'X-MSMail-Priority': 'High',
            }
            
            # Send email
            email_obj.send(fail_silently=False)
            
            logger.info(f"OTP email sent successfully to {email}")
            return True, "OTP sent successfully"
            
        except Exception as e:
            error_msg = f"Failed to send OTP email to {email}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def send_admin_otp_email(email: str, otp: str, user_name: str = None) -> Tuple[bool, str]:
        """Send OTP email for admin login"""
        context = {
            "otp": otp,
            "user": {"email": email, "username": user_name or email},
            "expiry_minutes": OTPService.get_otp_expiry_minutes(),
        }
        
        return EmailService.send_otp_email(
            email=email,
            otp=otp,
            template_name='web/emails/admin_otp.html',
            context_extras=context,
            subject='Admin Secure Login OTP - E-GameScout'
        )


# =====================================================
# USAGE EXAMPLES (for reference)
# =====================================================
"""
# === GENERATE & SEND OTP ===
success, otp, metadata = OTPService.store_otp('user@example.com')
if success:
    email_sent, msg = EmailService.send_otp_email('user@example.com', otp)
    if email_sent:
        # Pass metadata['expiry_minutes'] to template
        return render(request, 'verify.html', {'expiry_minutes': metadata['expiry_minutes']})

# === VERIFY OTP ===
success, message = OTPService.verify_otp('user@example.com', '123456')
if success:
    # User authenticated, proceed with login
    login(request, user)
    return redirect('dashboard')
else:
    # Show error message
    messages.error(request, message)
    return render(request, 'verify.html')

# === CHECK REMAINING ATTEMPTS ===
attempts = OTPService.get_otp_attempts_remaining('user@example.com')
if attempts is not None:
    print(f"Attempts remaining: {attempts}")

# === MANUAL CLEANUP ===
OTPService.clear_otp('user@example.com')
"""

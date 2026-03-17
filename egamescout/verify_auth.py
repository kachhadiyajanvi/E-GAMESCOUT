import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

def verify_auth_flow():
    client = Client()
    print("--- Starting Admin Auth Verification ---")

    # 1. Test Login with Valid Credentials
    print("1. Submitting Login Form...")
    response = client.post(reverse('admin_login'), {
        'email': 'admin.egamescout@gmail.com',
        'password': 'Admin@612'
    })
    
    if response.status_code == 302 and response.url == reverse('admin_verify_otp'):
        print("[SUCCESS] Redirected to OTP validation.")
    else:
        print(f"[FAIL] Unexpected response: {response.status_code} - {response.url}")
        return False
        
    # Retrieve the OTP from the session
    session = client.session
    otp = session.get('admin_login_otp')
    if not otp:
        print("[FAIL] OTP not set in session.")
        return False
    print(f"[SUCCESS] OTP Generated: {otp}")

    # 2. Test OTP Verification
    print("2. Submitting OTP...")
    response = client.post(reverse('admin_verify_otp'), {
        'otp': otp
    })
    
    if response.status_code == 302 and response.url == reverse('admin_dashboard'):
        print("[SUCCESS] OTP verified, redirected to Admin Dashboard.")
    else:
        print(f"[FAIL] OTP verification failed: {response.status_code}")
        return False

    # 3. Test Change Password Request
    print("3. Requesting Password Change...")
    response = client.get(reverse('admin_change_password_request'))
    
    if response.status_code == 302 and response.url == reverse('admin_change_password_verify'):
        print("[SUCCESS] Password change requested, redirected to OTP verification.")
    else:
        print(f"[FAIL] Password change request failed: {response.status_code}")
        return False
        
    # Retrieve new OTP
    session = client.session
    change_otp = session.get('admin_password_otp')
    if not change_otp:
        print("[FAIL] Change Password OTP not set in session.")
        return False
    print(f"[SUCCESS] Change Password OTP Generated: {change_otp}")
    
    # 4. Test Invalid Password Rules
    print("4. Testing Password Validators...")
    response = client.post(reverse('admin_change_password_verify'), {
        'otp': change_otp,
        'new_password': 'weak',
        'confirm_password': 'weak'
    })
    
    # Should not redirect (should render form with errors)
    if response.status_code == 200:
        content = response.content.decode('utf-8', errors='ignore')
        if '8 characters long' in content:
            print("[SUCCESS] Weak password correctly rejected.")
        else:
            print("[FAIL] Did not find expected validation error message.")
            return False
    else:
        print(f"[FAIL] Expected 200 OK with form errors, got {response.status_code}")
        return False
        
    # 5. Test Valid Password Change
    print("5. Submitting Valid New Password...")
    valid_password = 'NewSecureAdmin@2026'
    response = client.post(reverse('admin_change_password_verify'), {
        'otp': change_otp,
        'new_password': valid_password,
        'confirm_password': valid_password
    })
    
    if response.status_code == 302 and response.url == reverse('admin_profile'):
        print("[SUCCESS] Password changed successfully, redirected to profile.")
    else:
        print(f"[FAIL] Valid password change failed: {response.status_code}")
        return False
        
    # Reset Password internally to original so user can login normally
    u = User.objects.get(email='admin.egamescout@gmail.com')
    if u.check_password(valid_password):
        print("[SUCCESS] Database updated with new password.")
        u.set_password('Admin@612')
        u.save()
        print("[SUCCESS] Restored original test password.")
    else:
        print("[FAIL] Database password does not match new password.")
        return False
        
    print("\n--- All Tests Passed Successfully! ---")
    return True

if __name__ == '__main__':
    verify_auth_flow()

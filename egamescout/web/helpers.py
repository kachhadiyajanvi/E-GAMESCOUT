import base64
import os
import json
import datetime
import re
import time
import requests
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.html import strip_tags

def send_mail_async(subject, message, from_email, recipient_list, fail_silently=False, html_message=None):
    """
    Non-blocking wrapper for Django's send_mail / EmailMultiAlternatives using threading.
    """
    def _send():
        try:
            if html_message:
                msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently)
            else:
                send_mail(subject, message, from_email, recipient_list, fail_silently=fail_silently)
            print(f"EMAIL SENT (Async): '{subject}' to {recipient_list}")
        except Exception as e:
            print(f"EMAIL ASYNC ERROR: {str(e)}")
            
    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()


def send_platform_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Sends a platform email using a standard HTML template and auto-generated plain text version.
    
    Args:
        subject (str): Email subject.
        template_name (str): Path to template within 'web/emails/', e.g., 'welcome.html'.
        context (dict): Context data for template rendering.
        recipient_list (list): List of recipient email addresses.
        from_email (str, optional): Sender email. Defaults to settings.DEFAULT_FROM_EMAIL.
        
    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL or 'noreply@egamescout.com'

    # Ensure context has common variables if not provided
    if 'year' not in context:
        context['year'] = datetime.datetime.now().year
    
    # Template path handling
    if template_name.startswith('web/emails/'):
        full_template_path = template_name
    elif template_name.startswith('emails/'):
        full_template_path = f'web/{template_name}'
    else:
        full_template_path = f'web/emails/{template_name}'
    
    try:
        # Render HTML content
        html_content = render_to_string(full_template_path, context)
        # Create plain text alternative
        text_content = strip_tags(html_content)
        
        # Create Email Value Object
        msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        
        # Dispatch in Background to prevent UI blocking
        def _send():
            try:
                msg.send()
                print(f"EMAIL SENT (Async): '{subject}' to {recipient_list}")
            except Exception as thread_err:
                print(f"EMAIL ASYNC ERROR: {str(thread_err)}")
                
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()
        
        return True
    except Exception as e:
        print(f"EMAIL ERROR: Failed to prepare '{subject}' for {recipient_list}. Error: {str(e)}")
        return False


def extract_aadhar_details(image_file):
    """
    Extracts name, age, and Aadhar number from an Aadhar card image.
    Tries Gemini 2.5 Flash first, then Groq meta-llama/llama-4-scout as fallback.
    Returns: {'success': bool, 'data': dict, 'message': str}
    """
    print(f"DEBUG: extract_aadhar_details called with {image_file.name}")

    # Read and Encode Image
    image_content = image_file.read()
    encoded_string = base64.b64encode(image_content).decode('utf-8')

    # Determine Mime Type
    file_extension = os.path.splitext(image_file.name)[1].lower()
    mime_type = 'image/jpeg'  # Default
    if file_extension == '.png':
        mime_type = 'image/png'
    elif file_extension == '.webp':
        mime_type = 'image/webp'

    print(f"DEBUG: Processing image {image_file.name} ({mime_type})")

    prompt = """
Analyze this Aadhar Card image and extract the following details:
1. Full Name (Name of the person)
2. Date of Birth (DOB) or Year of Birth. Calculate Age based on the current year (2026).
3. Aadhar Number (12 digit unique ID)

STRICTLY return ONLY a JSON object. Do not write any other text.

Format:
{
    "full_name": "John Doe",
    "aadhar_number": "1234 5678 9012",
    "dob_found": "DD/MM/YYYY",
    "age": 25,
    "is_valid_aadhar": true
}

If it is NOT a valid Aadhar card or details are unreadable, set "is_valid_aadhar": false.
"""

    response_content = None
    used_model = None
    last_error = None

    # ── 1. Try Gemini 2.5 Flash (primary) ──────────────────────────────────
    gemini_keys = getattr(settings, 'GEMINI_API_KEYS', [])
    if not gemini_keys and getattr(settings, 'GEMINI_API_KEY', ''):
        gemini_keys = [settings.GEMINI_API_KEY]

    for i, gemini_key in enumerate(gemini_keys):
        if response_content:
            break
        try:
            print(f"DEBUG: Trying Gemini 2.5 Flash (key #{i+1})...")
            gemini_payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": encoded_string
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            model_name = "gemini-2.5-flash"
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            gemini_resp = requests.post(
                gemini_url,
                headers={"Content-Type": "application/json"},
                json=gemini_payload,
                timeout=30
            )
            gemini_resp.raise_for_status()
            candidates = gemini_resp.json().get("candidates", [])
            if candidates:
                response_content = candidates[0]["content"]["parts"][0]["text"].strip()
                used_model = f"gemini-2.5-flash (key #{i+1})"
                print(f"DEBUG: Gemini success with key #{i+1}")
        except Exception as e:
            last_error = e
            print(f"DEBUG: Gemini key #{i+1} failed: {e}")

    # ── 2. Try Groq meta-llama/llama-4-scout as fallback ───────────────────
    if not response_content:
        groq_key = getattr(settings, 'GROQ_API_KEY', '')
        if groq_key:
            model = "meta-llama/llama-4-scout-17b-16e-instruct"
            print(f"DEBUG: Trying Groq model {model}...")
            for attempt in range(3):
                try:
                    headers = {
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{mime_type};base64,{encoded_string}",
                                        },
                                    },
                                ],
                            }
                        ],
                        "model": model,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                    }
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers, json=payload, timeout=30
                    )
                    response.raise_for_status()
                    response_content = response.json()["choices"][0]["message"]["content"]
                    used_model = model
                    print(f"DEBUG: Groq success with {model}")
                    break
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    if "503" in str(e) or "429" in str(e) or "capacity" in error_str:
                        wait_time = 2 * (attempt + 1)
                        print(f"DEBUG: Groq busy (Attempt {attempt+1}/3). Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    print(f"DEBUG: Groq failed: {e}")
                    break

    # ── 3. Final check ───────────────────────────────────────────────────────
    if not response_content:
        print(f"ERROR: All AI providers failed. Last error: {last_error}")
        return {
            'success': False,
            'data': None,
            'message': "AI Service is currently unavailable. Please try again later."
        }

    print(f"DEBUG: AI Response ({used_model}): {response_content}")

    # Parse JSON response (strip markdown fences if present)
    try:
        clean = re.sub(r'^```(?:json)?\s*', '', response_content.strip(), flags=re.MULTILINE)
        clean = re.sub(r'```\s*$', '', clean.strip(), flags=re.MULTILINE)
        data = json.loads(clean.strip())
    except json.JSONDecodeError:
        age_match = re.search(r'"age":\s*(\d+)', response_content)
        if age_match:
            data = {'age': int(age_match.group(1)), 'is_valid_aadhar': True}
        else:
            data = {}

    if not data.get('is_valid_aadhar', False):
        return {
            'success': False,
            'data': None,
            'message': "Could not detect a valid Aadhar card. Please upload a clear image."
        }

    return {
        'success': True,
        'data': data,
        'message': f"Verification successful via {used_model}."
    }

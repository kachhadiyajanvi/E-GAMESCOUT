import base64
import os
import json
import datetime
import re
import time
from django.conf import settings
from groq import Groq

def verify_age_with_groq(image_file):
    """
    Verifies age from an Aadhar card image using Groq's Vision model.
    Returns a dictionary: {'success': bool, 'age': int, 'message': str}
    """
    print(f"DEBUG: verify_age_with_groq called with {image_file.name}")
    
    if not settings.GROQ_API_KEY:
        print("DEBUG: GROQ_API_KEY is missing.")
        return {
            'success': False,
            'age': None,
            'message': "Server Configuration Error: Groq API Key missing."
        }
        
    try:
        # Initialize Groq Client
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Read and Encode Image
        image_content = image_file.read()
        encoded_string = base64.b64encode(image_content).decode('utf-8')
        
        # Determine Mime Type
        file_extension = os.path.splitext(image_file.name)[1].lower()
        mime_type = 'image/jpeg' # Default
        if file_extension == '.png':
            mime_type = 'image/png'
        elif file_extension == '.webp':
            mime_type = 'image/webp'
            
        print(f"DEBUG: Processing image {image_file.name} ({mime_type})")

        # Construct Prompt
        prompt = """
        Analyze this Aadhar Card image. 
        1. Find the Date of Birth (DOB). It is usually in format DD/MM/YYYY or Year of Birth: YYYY.
        2. Calculate the person's age based on today's date (assuming today is 2026).
        3. STRICTLY return ONLY a JSON object. Do not write any other text.
        
        Format:
        {
            "dob_found": "DD/MM/YYYY" or "YYYY",
            "age": 25,
            "is_valid_aadhar": true
        }
        
        If you cannot read the DOB or if it's not a valid ID card, set "is_valid_aadhar": false.
        """
        
        # List of models to try in order of preference
        models_to_try = [
            "meta-llama/llama-4-scout-17b-16e-instruct",     # Best quality
            "meta-llama/llama-4-maverick-17b-128e-instruct", # Alternative high quality
            "llava-v1.5-7b-4096-preview"                     # Fallback (lower quality but stable)
        ]
        
        response_content = None
        used_model = None
        last_error = None

        for model in models_to_try:
            print(f"DEBUG: Trying model {model}...")
            # Retry logic for each model (handle 503/429)
            for attempt in range(3):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
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
                        model=model, 
                        temperature=0,
                        response_format={"type": "json_object"},
                    )
                    
                    response_content = chat_completion.choices[0].message.content
                    used_model = model
                    break # Success! Break retry loop
                    
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # If model decommissioned (400), don't retry this model, break to next model
                    if "model_decommissioned" in error_str or "400" in str(e):
                        print(f"DEBUG: Model {model} decommissioned. Skipping.")
                        break
                        
                    # If rate limited or server busy (503, 429), retry with backoff
                    if "503" in str(e) or "429" in str(e) or "capacity" in error_str:
                        wait_time = 2 * (attempt + 1)
                        print(f"DEBUG: Model {model} busy (Attempt {attempt+1}/3). Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue # Retry same model
                    
                    # Other unknown errors
                    print(f"DEBUG: Model {model} failed with error: {e}")
                    break # Break retry loop, try next model
            
            if response_content:
                break # Success! Break model loop
        
        if not response_content:
            # All models failed
            print(f"ERROR: All AI models failed. Last error: {last_error}")
            return {
                'success': False,
                'age': None,
                'message': f"AI Service is currently busy. Please try again later. (Ref: {str(last_error)[:50]}...)"
            }

        print(f"DEBUG: Groq Response ({used_model}): {response_content}")
        
        # Parse JSON
        try:
            data = json.loads(response_content)
        except json.JSONDecodeError:
            # Fallback regex if JSON is malformed
            age_match = re.search(r'"age":\s*(\d+)', response_content)
            if age_match:
                data = {'age': int(age_match.group(1)), 'is_valid_aadhar': True}
            else:
                data = {}

        if not data.get('is_valid_aadhar', False) and data.get('age') is None:
             return {
                'success': False,
                'age': None,
                'message': "Could not detect a valid Aadhar card or DOB. Please upload a clear image."
            }
            
        age = data.get('age')
        
        if age is not None:
            return {
                'success': True,
                'age': int(age),
                'message': f"Age verified successfully via {used_model}."
            }
        else:
             return {
                'success': False,
                'age': None,
                'message': "Could not calculate age from the image."
            }

    except Exception as e:
        print(f"ERROR: verify_age_with_groq critical failure: {str(e)}")
        return {
            'success': False,
            'age': None,
            'message': "An system error occurred during verification. Please try again."
        }

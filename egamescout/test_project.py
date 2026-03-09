import os
import django
import re
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from django.template.loader import get_template
from django.template.utils import get_app_template_dirs
from django.urls import reverse, NoReverseMatch, get_resolver
from django.conf import settings

def find_templates():
    template_files = []
    # Add from app templates
    for d in get_app_template_dirs('templates'):
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.html'):
                    template_files.append(os.path.join(root, file))
    # Add from settings.TEMPLATES DIRS
    if settings.TEMPLATES and settings.TEMPLATES[0].get('DIRS'):
        for d in settings.TEMPLATES[0]['DIRS']:
             for root, _, files in os.walk(d):
                for file in files:
                    if file.endswith('.html'):
                        template_files.append(os.path.join(root, file))
    return template_files

templates = find_templates()
print(f"Found {len(templates)} templates.")

url_regex = re.compile(r'{%\s*url\s+[\'"]([a-zA-Z0-9_:-]+)[\'"]')
static_regex = re.compile(r'{%\s*static\s+[\'"]([^\'"]+)[\'"]')

errors = []
resolver = get_resolver()
valid_url_names = set(resolver.reverse_dict.keys())

for t_path in templates:
    # Get rel_path relative to a 'templates' directory
    parts = Path(t_path).parts
    try:
        idx = parts.index('templates')
        rel_path = os.path.join(*parts[idx+1:])
    except ValueError:
        rel_path = os.path.basename(t_path)
        
    # 1. Syntax check
    try:
        get_template(rel_path)
    except Exception as e:
        errors.append(f"[SyntaxError] {rel_path}: {type(e).__name__} - {e}")

    with open(t_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # 2. Check URLs
        for match in url_regex.finditer(content):
            url_name = match.group(1)
            if url_name not in valid_url_names:
                errors.append(f"[ReverseError] {rel_path}: URL name '{url_name}' not found.")
                
        # 3. Check static files
        for match in static_regex.finditer(content):
            static_path = match.group(1)
            found = False
            for d in settings.STATICFILES_DIRS:
                if os.path.exists(os.path.join(d, static_path)):
                    found = True
                    break
            # Also check app static dirs
            from django.contrib.staticfiles.finders import find
            if not found and find(static_path):
                found = True

            if not found:
                 errors.append(f"[StaticError] {rel_path}: '{static_path}' does not exist.")

for e in errors:
    print(e)
if not errors:
    print("No errors found in templates, urls, or static references.")

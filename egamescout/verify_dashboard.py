import os
import sys

# Setup Database Driver (Standard boilerplate from manage.py)
# MUST be done before importing django or calling django.setup()
import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
# Monkey patch the version to satisfy Django's requirement
if hasattr(MySQLdb, 'version_info'):
    MySQLdb.version_info = (2, 2, 7, 'final', 0)
else:
    pymysql.version_info = (2, 2, 7, 'final', 0)

import django
from django.conf import settings

# Setup Django environment
# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')

# Bypass MariaDB version check for older XAMPP versions (Copied from manage.py)
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    
    # Disable RETURNING support for MariaDB < 10.5
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = False
except ImportError:
    pass

django.setup()

# Allow testserver for client
settings.ALLOWED_HOSTS += ['testserver']

from django.test import Client
from web.models import Organization

def verify():
    # 1. Create or Get Test User
    email = "verify_bot@example.com"
    org, created = Organization.objects.get_or_create(
        Organization_Email=email,
        defaults={
            'Organization_UserName': 'verifybot',
            'Organization_Name': 'Verify Bot',
            'Organization_Contact': 9876543210
        }
    )
    print(f"Test Org: {org.Organization_Name} ({org.Organization_Email}) ID: {org.id}")

    # 2. Simulate Login using Client Session
    client = Client()
    session = client.session
    session['organizer_id'] = org.id
    session.save()

    # 3. Request Dashboard
    try:
        response = client.get('/dashboard/')
        content = response.content.decode('utf-8')
        
        print(f"Response Status: {response.status_code}")
        
        # 4. Analyze Content
        if response.status_code != 200:
            print("ERROR: Dashboard returned non-200 status.")
            return

        # Check for literal template tags (The Bad Thing)
        if "{{ org.Organization_Email }}" in content:
            print("FAIL: Found literal template tag '{{ org.Organization_Email }}' in output!")
        else:
            print("PASS: No literal key template tags found.")

        # Check for actual email (The Good Thing)
        if email in content:
            print(f"PASS: Found computed email '{email}' in output.")
            
            # Show context
            idx = content.find(email)
            start = max(0, idx - 100)
            end = min(len(content), idx + 100)
            print(f"\nContext:\n...{content[start:end]}...\n")
        else:
            print(f"FAIL: Could not find email '{email}' in output.")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    verify()

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from django.contrib.auth.models import User

try:
    if User.objects.filter(username='admin@gmail.com').exists():
        print("User already exists")
    else:
        User.objects.create_superuser('admin@gmail.com', 'admin@gmail.com', 'admin@123')
        print("Superuser created successfully")
except Exception as e:
    print(f"Error: {e}")

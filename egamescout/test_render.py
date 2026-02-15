import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
setattr(MySQLdb, 'version_info', (2, 2, 7, 'final', 0))
setattr(pymysql, 'version_info', (2, 2, 7, 'final', 0))

# Bypass MariaDB version check
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = False
except ImportError:
    pass

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from django.template.loader import render_to_string
from web.models import Tournament, Organization
from django.test import RequestFactory

print("Rendering Template...")
last_tourney = Tournament.objects.last()
org = last_tourney.Organization_Name
upcoming = Tournament.objects.filter(
    Organization_Name=org,
    Status__in=['Scheduled', 'Ongoing'],
    is_published=True
).order_by('start_date')

factory = RequestFactory()
request = factory.get('/')

context = {'tournaments': upcoming, 'org': org, 'request': request}

try:
    rendered = render_to_string('web/Organization/org_upcoming_list.html', context)
    print("Render Success!")
    if last_tourney.Name in rendered:
        print(f"FOUND TOURNAMENT NAME '{last_tourney.Name}' IN OUTPUT.")
    else:
        print(f"FAILED TO FIND '{last_tourney.Name}' IN OUTPUT.")
        print(rendered[:500])
except Exception as e:
    print(f"Render Failed: {e}")

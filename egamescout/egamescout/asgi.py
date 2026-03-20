"""
ASGI config for egamescout project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import pymysql

# PyMySQL and MariaDB patches matching manage.py
pymysql.install_as_MySQLdb()
import MySQLdb
if hasattr(MySQLdb, 'version_info'):
    MySQLdb.version_info = (2, 2, 7, 'final', 0)
else:
    pymysql.version_info = (2, 2, 7, 'final', 0)

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')

# Bypass MariaDB version check and disable RETURNING for older MariaDB
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = False
except ImportError:
    pass

application = get_asgi_application()

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import pymysql

pymysql.install_as_MySQLdb()
import MySQLdb
# Monkey patch the version to satisfy Django's requirement
if hasattr(MySQLdb, 'version_info'):
    MySQLdb.version_info = (2, 2, 7, 'final', 0)
else:
    pymysql.version_info = (2, 2, 7, 'final', 0)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')

    # Bypass MariaDB version check for older XAMPP versions
    try:
        from django.db.backends.mysql.base import DatabaseWrapper
        DatabaseWrapper.check_database_version_supported = lambda self: None
        
        # Disable RETURNING support for MariaDB < 10.5
        from django.db.backends.mysql.features import DatabaseFeatures
        DatabaseFeatures.can_return_columns_from_insert = False
    except ImportError:
        pass

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

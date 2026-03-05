import pymysql

pymysql.install_as_MySQLdb()
import MySQLdb

if hasattr(MySQLdb, 'version_info'):
    MySQLdb.version_info = (2, 2, 7, 'final', 0)
else:
    pymysql.version_info = (2, 2, 7, 'final', 0)

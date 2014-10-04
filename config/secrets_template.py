"""
Secret settings local to this machine.
"""
SECRET_KEY = '{{secret_key}}'
DEBUG = {{debug}}
TEMPLATE_DEBUG = {{template_debug}}
DATABASE_NAME = '{{django_db_name}}'
DATABASE_USER = '{{django_db_user}}'
DATABASE_PASSWORD = '{{django_db_pwd}}'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'
MAIL_USER = '{{username_email}}'
MAIL_PASSWORD = '{{password_email}}'
ADDITIONAL_TEMPLATE_DIRS = []

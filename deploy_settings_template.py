# Change these settings to match your deployment environment and
# put them in a deploy_settings.py file.

# NOTE: Illegal user names
# root, daemon, bin, sys, sync, games, man, lp, mail, news, uucp, proxy,
# www-data, backup, list, irc, gnats, nobody, libuuid, syslog, messagebus,
# sshd
username_main = 'username'
username_email = 'mailname'
email_address_webmaster = 'webmaster@example.com'
django_db_name = 'django_db'
django_db_user = 'django'
django_db_test_name = 'django_db_test'
django_db_test_user = 'django_test'
ip_address = '0.0.0.0'
domain = 'example.com'
make_new_project = True
push_existing_repo = False & (not make_new_project)
existing_repo_location = '/home/me/workspace/domain/'
app_name = 'myapp'
server_name = 'www'
dkim_selector = 'web'
python_version = '3.4'
python_req_file = None  # On local machine
postgres_version = '9.3'
password_login = 'no'
use_https = True
local_test_db = True
remove_temp_files = True
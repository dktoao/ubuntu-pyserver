"""
Deployment script to turn a Ubuntu 14.04 LTS machine into a fully capable web
server with the following components:

    ## Computing ##
    - Python / Django, Set up with proper settings/environmental variables, a super
    user account and a migration ready connection to a PostgreSQL database
        - Django
        - Numpy
        - Scipy
        - Matplotlib
        - uWSGI
        - psycopg2
        - South (depreciated with Django 1.7)
        
    ## Database ##
    - PostgreSQL
    
    ## Server Stack ##
    - uWSGI
    - nginx
    
    ## Email ##
    - Exim (send only)
    - Authentication via DKIM
    - Reminder to manually configure SPF
    
    ## Interface ##
    - A pretty Django website that makes it easy to create navigation links to 
    created apps
    
    ## App Deployment ##
    - Git, set up to automatically deploy to a production server
    
    ## Security ##
    - iptables firewall
    - appropriate user accounts
    - fail2ban
    - https with self signed ssl cert
    
Author: Daniel Kuntz
"""

#Settings
username_main = 'dktoao'
username_email = 'robomailer'
email_address_webmaster = 'daniel.kuntz@dk-cloud.net'
django_db_name = 'dkcloud_db'
django_db_user = 'dkcloud_django'
ip_address = '198.58.125.218'
domain = 'dk-cloud.net'
app_name = 'dkcloud'
server_name = 'electrode'
dkim_selector = 'web'
#web_directory = '/var/www'
#repo_directory = '/var/repo'
python_version = '3.4'
postgres_version = '9.3'
password_login = 'yes'
use_https = True


# Imports
from fabric.api import run, get, put, env, sudo, hosts, local
from fabric.operations import reboot
from fabric.context_managers import cd
from jinja2 import Environment, FileSystemLoader
from string import ascii_letters, digits
from random import SystemRandom
import json

# Set up Jinja environment
template_env = Environment(loader=FileSystemLoader('config'))

@hosts('root@%s' % ip_address)
def full_deploy1():
    '''
    Runs all root deployment scripts
    '''
    # Initial Setup
    setup_hosts()
    upgrade()
    setup_users()
    setup_firewall()
    setup_fail2ban()
    remove_root_login()
    restart()
    
@hosts('%s@%s' % (username_main, ip_address))
def full_deploy2():
    '''
    Runs all primary user deployment scripts
    '''
    
    # Advanced Setup
    install_postgres()
    install_exim()
    install_nginx()
    install_python()
    configure_django()
    setup_repo()
    restart()
    
@hosts('root@%s' % ip_address)
def setup_hosts():
    '''
    Set up host configurations
    '''
    
    print("Setting up basic settings:")
    
    # Set the hostname and mailname
    run('echo "%s" > /etc/hostname' % (server_name + "." + domain))
    run('hostname -F /etc/hostname')
    run('echo "%s" > /etc/mailname' % domain)
    
    # Update the /etc/hosts file
    upload_config('/etc', 'hosts', {
        'server_name': server_name,
        'domain': domain,
        'ip_address': ip_address,
    })
    
@hosts('root@%s' % ip_address)
def upgrade():
    '''
    Upgrade server software
    '''
    print("Upgrading server with latest software")
    
    #Update Repository
    run('apt-get update')
    run('apt-get -y upgrade')
    
@hosts('root@%s' % ip_address)
def setup_users():
    '''
    Set up users and groups with super user and rsa key access to server
    '''
    print("Setting up users and access")
    
    #Create super user
    run('adduser --gecos "" %s' % username_main)
    # Add to sudo and www-data groups
    run('usermod -a -G sudo %s' % username_main)
    run('usermod -a -G www-data %s' % username_main)
    # copy local public key to .ssh/authorized_keys
    run('mkdir /home/%s/.ssh' % username_main)
    put('~/.ssh/id_rsa.pub', '/home/%s/.ssh/authorized_keys' % username_main)
    # Change ownership and permissions for uploaded file
    run('chown -R %s:%s /home/%s/.ssh'% (username_main, username_main, username_main))
    run('chmod 500 /home/%s/.ssh' % username_main)
    run('chmod 400 /home/%s/.ssh/authorized_keys' % username_main)
    
    # Create mail user
    mail_password = random_password('MAIL USER')
    run('adduser --gecos "" --disabled-password %s' % username_email)
    run('echo "%s:%s" | chpasswd' % (username_email, mail_password))
    
    # Create git user
    git_password = random_password('GIT USER')
    run('adduser --gecos "" --disabled-password git')
    run('echo "git:%s" | chpasswd' % git_password)
    # copy local public key to .ssh/authorized_keys
    run('mkdir /home/git/.ssh')
    put('~/.ssh/id_rsa.pub', '/home/git/.ssh/authorized_keys')
    # Change ownership and permissions for uploaded file
    run('chown -R git:git /home/git/.ssh')
    run('chmod 500 /home/git/.ssh')
    run('chmod 400 /home/git/.ssh/authorized_keys')
    
@hosts('root@%s' % ip_address)
def setup_firewall():
    '''
    Setup iptables firewall with basic security settings
    '''
    print("Setting up basic firewall")
    
    # Updload firewall rules file
    put('config/iptables.firewall.rules', '/etc')
    # Load firewall rules
    run('iptables-restore < /etc/iptables.firewall.rules')
    # Load startup file
    put('config/firewall', '/etc/network/if-pre-up.d')
    run('chmod +x /etc/network/if-pre-up.d/firewall')
    
@hosts('root@%s' % ip_address)
def setup_fail2ban():
    '''
    Install and setup fail2ban software
    '''
    print("Installing fail2ban")
    
    run('apt-get install -y fail2ban')
    
@hosts('root@%s' % ip_address)
def remove_root_login():
    '''
    Removing ability to log-in as root and set password login ability
    '''
    
    print('Diabling root login')
    
    upload_config('/etc/ssh', 'sshd_config', {
        'password_login': password_login,
    })

@hosts('root@%s' % ip_address)
def restart():
    '''
    Restart the server
    '''
    print('Restarting the server')
    #reboot()
    sudo('reboot')
    
@hosts('%s@%s' % (username_main, ip_address))
def install_postgres():
    '''
    Install and configure postgres with a user for Django
    '''
    print('Installing/Configuring PostgreSQL server')
    
    # Install postgres
    sudo('apt-get install -y postgresql-%s postgresql-contrib-%s' %(postgres_version, postgres_version))
    # Install the adminpack extension
    sudo('psql -c "CREATE EXTENSION adminpack"', user='postgres')
    # Create a django database user
    sudo('psql -c "CREATE USER %s WITH PASSWORD \'%s\'"' % (django_db_user, random_password('DJANGO DATABASE')), user='postgres')
    # Create a database for django to use
    sudo('createdb -O %s %s' % (django_db_user, django_db_name), user='postgres')
    # Update the postgres pg_hba.conf file
    upload_config('/etc/postgresql/%s/main' % postgres_version, 'pg_hba.conf', {
        'django_db_user': django_db_user,
    })
    # Restart the postgres server
    sudo('service postgresql restart')
    
@hosts('%s@%s' % (username_main, ip_address))
def install_exim():
    '''
    Install exim4 mailer in a send only configuration
    '''
    
    print('Installing email system')
    
    # install the system
    sudo('apt-get install -y exim4-daemon-light mailutils')
    # Initial Setup of Exim
    upload_config('/etc/exim4', 'update-exim4.conf.conf', {
        'domain': domain,
        'server_name': server_name,
    })
    
    # Set up a security certificate
    with cd('/etc/exim4'):
        # Generate the private key
        sudo('openssl genrsa -out dkim.private.key 1024')
        # Generate the private key
        sudo('openssl rsa -in dkim.private.key -out dkim.public.key -pubout -outform PEM')
        # Change ownership and privleges of the private key
        sudo('chown root:Debian-exim dkim.private.key')
        sudo('chmod 640 dkim.private.key')
        # Download the public key
        get('/etc/exim4/dkim.public.key', local_path='info')
        
    # Update Exim configuration to use DKIM signing
    upload_config('/etc/exim4/conf.d/main', '00_local_settings', {
        'domain': domain,
        'dkim_selector': dkim_selector,
    })
    
    # Configure email addresses for primary users
    upload_config('/etc', 'email-addresses', {
        'domain': domain,
        'username_main': username_main,
        'username_email': username_email,
    })
    
    # Restart exim
    sudo('update-exim4.conf')
    sudo('service exim4 restart')

@hosts('%s@%s' % (username_main, ip_address))
def install_nginx():
    '''
    Installs and configures nginx server
    '''
    
    print('Installing and configuring nginx')
    
    # Install server software from repository
    sudo('apt-get install -y nginx-full')
    
    # Create directory for nginx logs
    sudo('mkdir -p /var/log/%s' % domain)
    
    # Create a self-signed SSL certificate if required
    if use_https:
        with cd('/etc/nginx'):
            sudo('openssl genrsa -out https.key 1024')
            sudo('openssl req -new -key https.key -out https.csr')
            sudo('openssl x509 -req -days 365 -in https.csr -signkey https.key -out https.cert')
            
            # Change ownership and priveleges
            sudo('chown www-data:www-data https.key https.cert https.csr')
            sudo('chmod 400 https.key https.cert https.csr')
        
        nginx_config_file = 'nginx_settings_ssl'
        
    else:
        nginx_config_file = 'nginx_settings'
            
    # Configure nginx
    upload_config('/etc/nginx/sites-available', nginx_config_file, {
        'domain': domain,
        'app_name': app_name,
    }, rename=domain)
    
    # enable the site
    sudo('rm /etc/nginx/sites-enabled/default')
    sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (domain, domain))
    
@hosts('%s@%s' % (username_main, ip_address))
def install_python():
    '''
    Install Python and desired packages in a virtualenv at /var/www/env
    '''
    
    print('Installing python virtualenv')
    
    # Get the Python development headers
    sudo('apt-get install -y python%s-dev' % python_version)
    # Get required libraries for uWSGI
    sudo('apt-get install -y libpcre3-dev libssl-dev')
    # Get postgres development headers
    sudo('apt-get install -y postgresql-server-dev-%s' % postgres_version)
    # Get the scipy prequisites
    sudo('apt-get install -y gfortran libopenblas-dev liblapack-dev')
    # Get the matplotlib prequisites
    sudo('apt-get install -y libfreetype6-dev libxft-dev')
    # Get virtualenv
    sudo('apt-get install -y python-virtualenv')
    
    # Make a virtual environment for the user and activate it
    sudo('mkdir -p /var/www/env')
    sudo('virtualenv --python=python%s /var/www/env/%s' % (python_version, domain))
    sudo('chown -R %s:www-data /var/www' % username_main)
    sudo('chmod -R 750 /var/www')
    
    # Install python packages
    python_env = 'source /var/www/env/%s/bin/activate && ' % domain
    run(python_env + 'pip install django')
    run(python_env + 'pip install uwsgi')
    run(python_env + 'pip install psycopg2')
    run(python_env + 'pip install south')
    run(python_env + 'pip install numpy')
    run(python_env + 'pip install scipy')
    run(python_env + 'pip install matplotlib')
    
    # Start a Django Project
    run('mkdir /var/www/%s' % domain)
    with cd('/var/www/%s' % domain):
        run(python_env + 'django-admin.py startproject %s' %  app_name)
        
    # Create Upstart file to run uWSGI
    upload_config('/etc/init', 'uwsgi.conf', {
        'app_name': app_name,
        'domain': domain,
    })
    
@hosts('%s@%s' % (username_main, ip_address))
def configure_django():
    
    print("Configuring Django")
    
    # Configure app directory and make appropriate files and sub directories
    python_env = 'source /var/www/env/%s/bin/activate && ' % domain
    with cd('/var/www/%s/%s' % (domain, app_name)):
        run('mkdir static') # Static files
        run('mkdir templates') # Template files
        #put('config/.gitignore', '..') # .gitignore file
        upload_config('/var/www/%s' % domain, '.gitignore', {
            'app_name': app_name,
        })
        run(python_env + 'pip freeze >> ../requirements.txt') # requirements file
        
        # Upload new django config file
        password_email = random_password('MAIL USER')
        upload_config(app_name,'settings.py', {
            'domain': domain,
            'app_name': app_name,
            
        })
    
        # Set up secrets.py file and change ownership to root
        upload_config(app_name, 'secrets.py', {
            'secret_key': random_password('DJANGO SECRETKEY',80,120),
            'debug': 'False',
            'template_debug': 'False',
            'django_db_name': django_db_name,
            'django_db_user': django_db_user,
            'django_db_pwd': random_password('DJANGO DATABASE'),
            'username_email': username_email,
            'password_email': random_password('MAIL USER'),
        })
        sudo('chown root:www-data %s/secrets.py' % app_name)
        sudo('chmod 640 %s/secrets.py' % app_name)
        
        # Collect static files
        run(python_env + 'python manage.py collectstatic')
        
        # Create a database migration
        run(python_env + 'python manage.py syncdb')
        #run(python_env + 'python manage.py schemamigration %s --initial' % app_name)
        #run(python_env + 'python manage.py migrate %s' % app_name)
        
@hosts('%s@%s' % (username_main, ip_address))
def setup_repo():
    '''
    Sets up a git repository where the website code can live and be deployed from
    '''
    
    print("Setting up a git repository for website code")
    
    # Install git
    sudo('apt-get -y install git')
    
    # Set up a directory and change ownership
    sudo('mkdir -p /var/repo/%s.git' % domain)
    sudo('chown git:git /var/repo/%s.git' % domain)
    
    # Set up repository
    with cd('/var/repo/%s.git' % domain):
        sudo('git --bare init', user='git')
        
    with cd('/var/www/%s' % domain):
        run('git config --global user.email "%s"' % email_address_webmaster)
        run('git config --global user.name "%s"' % username_main)
        run('git init')
        run('git add .')
        run('git commit -m "initial commit"')
        run('git remote add origin git@localhost:/var/repo/%s.git' % domain)
        run('git push origin master')
        
    
# Helper functions
def upload_config(upload_location, local_file, values, rename=None):
    '''
    Creates a backup of the original file on the server, fills in the given
    template and then uploads it to the desired location.
    '''
    if rename != None:
        external_file = rename
    else:
        external_file = local_file
    
    sudo('mv %s/%s %s/%s.backup' % (upload_location, external_file, upload_location, external_file), warn_only=True)
    template = template_env.get_template(local_file)
    file = template.render(values)
    with open('tmp/%s' % external_file, 'wb') as fh:
        fh.write(file)
    put('tmp/%s' % external_file, '~')
    sudo('mv ~/%s %s' % (external_file, upload_location))
    local('rm tmp/%s' % external_file)
    
def random_password(description, min_chars=10, max_chars=20):
    '''
    Creates a random password from uppercase letters, lowercase letters and
    digits with a length between min_chars and max_chars
    '''
    
    # Open saved passwords file or create new one.
    try:
        fh = open('info/passwords.json', 'r+')
        passwords = json.load(fh)
    except IOError:
        fh = open('info/passwords.json', 'w+')
        passwords = {}
        
    # Return password if it exists already
    if description in passwords:
        fh.close()
        return passwords[description]
    
    # Create new password if it does not exist
    else:
        seeded_random = SystemRandom()
        chars = ascii_letters + digits
        password_length = seeded_random.randint(min_chars, max_chars)
        password = ''.join(seeded_random.choice(chars) for _ in range(password_length))
        passwords[description] = password
        fh.seek(0)
        json.dump(passwords, fh, indent=4)
        fh.close()

        return password
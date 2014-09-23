"""
Fabric file for the deployment of a fully capable web server on an 
Ubuntu 14.04 LTS machine.
    
Author: Daniel Kuntz
"""

# Import settings
import deploy_settings as ds

# Imports
from fabric.api import run, get, put, env, sudo, hosts, local, settings
from fabric.context_managers import cd
from jinja2 import Environment, FileSystemLoader
from string import ascii_letters, digits
from random import SystemRandom
import json

# Set up Jinja environment
template_env = Environment(loader=FileSystemLoader('config'))


@hosts('root@%s' % ds.ip_address)
def full_setup():
    """
    Runs all root deployment scripts
    """
    # Initial Setup
    setup_hosts()
    upgrade()
    setup_users()
    setup_firewall()
    setup_fail2ban()
    remove_root_login()
    restart()


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def full_deploy():
    """
    Runs all primary user deployment scripts
    """
    # Advanced Setup
    install_postgres()
    #install_exim()
    install_nginx()
    install_python()
    configure_django_workspace()
    setup_repo()
    setup_production_code()
    setup_bash_aliases()
    restart()


@hosts('root@%s' % ds.ip_address)
def setup_hosts():
    """
    Set up host configurations
    """
    
    # Set the hostname and mailname
    run('echo "%s" > /etc/hostname' % (ds.server_name + "." + ds.domain))
    run('hostname -F /etc/hostname')
    run('echo "%s" > /etc/mailname' % ds.domain)
    
    # Update the /etc/hosts file
    upload_config('/etc', 'hosts', {
        'server_name': ds.server_name,
        'domain': ds.domain,
        'ip_address': ds.ip_address,
    })


@hosts('root@%s' % ds.ip_address)
def upgrade():
    """
    Upgrade server software
    """
    
    #Update Repository
    run('apt-get update')
    run('apt-get -y upgrade')


@hosts('root@%s' % ds.ip_address)
def setup_users():
    """
    Set up users and groups with super user and rsa key access to server
    """
    
    #Create super user
    run('adduser --gecos "" %s' % ds.username_main)
    # Add to sudo and www-data groups
    run('usermod -a -G sudo %s' % ds.username_main)
    run('usermod -a -G www-data %s' % ds.username_main)
    # copy local public key to .ssh/authorized_keys
    run('mkdir /home/%s/.ssh' % ds.username_main)
    with cd('/home/%s/.ssh' % ds.username_main):
        put('~/.ssh/id_rsa.pub', 'authorized_keys')
        # Create own private key
        run('ssh-keygen -t rsa -C "%s@%s" -f id_rsa -N ""' % (ds.username_main, ds.server_name))
        # Change ownership and permissions for uploaded file
        run('chown -R %s:%s .'% (ds.username_main, ds.username_main))
        run('chmod 500 .')
        run('chmod 600 authorized_keys')
        run('chmod 600 id_rsa')
        run('chmod 644 id_rsa.pub')
    
    # Create mail user
    mail_password = random_password('MAIL USER')
    run('adduser --gecos "" --disabled-password %s' % ds.username_email)
    run('echo "%s:%s" | chpasswd' % (ds.username_email, mail_password))
    
    # Create git user
    git_password = random_password('GIT USER')
    run('adduser --gecos "" --disabled-password git')
    run('echo "git:%s" | chpasswd' % git_password)
    # copy remote public key to .ssh/authorized_keys
    run('mkdir /home/git/.ssh')
    put('~/.ssh/id_rsa.pub', '/home/git/.ssh/authorized_keys')
    # add local public key to .ssh/authorized_keys
    run('cat /home/%s/.ssh/id_rsa.pub >> /home/git/.ssh/authorized_keys' % ds.username_main)
    # Change ownership and permissions for uploaded file
    run('chown -R git:git /home/git/.ssh')
    run('chmod 500 /home/git/.ssh')
    run('chmod 600 /home/git/.ssh/authorized_keys')


@hosts('root@%s' % ds.ip_address)
def setup_firewall():
    """
    Setup iptables firewall with basic security settings
    """
    
    # Updload firewall rules file
    put('config/iptables.firewall.rules', '/etc')
    # Load firewall rules
    run('iptables-restore < /etc/iptables.firewall.rules')
    # Load startup file
    put('config/firewall', '/etc/network/if-pre-up.d')
    run('chmod +x /etc/network/if-pre-up.d/firewall')


@hosts('root@%s' % ds.ip_address)
def setup_fail2ban():
    """
    Install and setup fail2ban software
    """

    install_software(['fail2ban'], root=True)


@hosts('root@%s' % ds.ip_address)
def remove_root_login():
    """
    Removing ability to log-in as root and set password login ability
    """
    
    upload_config('/etc/ssh', 'sshd_config', {
        'password_login': ds.password_login,
    })


@hosts('root@%s' % ds.ip_address)
def restart():
    """
    Restart the server
    """
    #reboot()
    sudo('reboot')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_postgres():
    """
    Install and configure postgres with a user for Django
    """
    
    # Install postgres
    install_software([
        'postgresql-%s' % ds.postgres_version,
        'postgresql-contrib-%s' % ds.postgres_version,
        'postgre-server-dev-%s' % ds.postgres_version,
    ])
    # Install the adminpack extension
    sudo('psql -c "CREATE EXTENSION adminpack"', user='postgres')
    # Create a django database user
    sudo('psql -c "CREATE USER %s WITH PASSWORD \'%s\'"' % (ds.django_db_user, random_password('DJANGO DATABASE')), user='postgres')
    # Create a database for django to use
    sudo('createdb -O %s %s' % (ds.django_db_user, ds.django_db_name), user='postgres')
    # Create a test database and test user
    if ds.local_test_db:
        sudo('psql -c "CREATE USER %s WITH PASSWORD \'%s\'"' % (ds.django_db_test_user, random_password('DJANGO TEST DATABASE')), user='postgres')
        sudo('createdb -O %s %s' % (ds.django_db_test_user, ds.django_db_test_name), user='postgres')
    # Update the postgres pg_hba.conf file
    upload_config('/etc/postgresql/%s/main' % ds.postgres_version, 'pg_hba.conf', {
        'django_db_user': ds.django_db_user,
        'django_db_test_user': ds.django_db_test_user,
    })
    # Restart the postgres server
    sudo('service postgresql restart')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_mail_server():
    """
    Installs and configures the postfix SMTP server and other components
    required for email
    """

    # Set the initial configuration options for postfix
    sudo('debconf-set-selections <<< "postfix postfix/mailname string %s"' % ds.domain)
    sudo('debconf-set-selections <<< "postfix postfix/main_mailer_type string \'Internet Site\'"')

    # Install the required software
    install_software(['postfix'])

    # Change the config file
    upload_config('/etc/postfix', 'main.cf', {
        'server_name': ds.server_name,
        'domain': ds.domain,
    })

    # START HERE



@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_exim():
    """
    Install exim4 mailer in a send only configuration.  Can be used as an alternate to
    postfix.
    """
    
    # install the system
    install_software([
        'exim4-daemon-light',
        'mailutils',
    ])
    # Initial Setup of Exim
    upload_config('/etc/exim4', 'update-exim4.conf.conf', {
        'domain': ds.domain,
        'server_name': ds.server_name,
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
        'domain': ds.domain,
        'dkim_selector': ds.dkim_selector,
    })
    
    # Configure email addresses for primary users
    upload_config('/etc', 'email-addresses', {
        'domain': ds.domain,
        'username_main': ds.username_main,
        'username_email': ds.username_email,
    })
    
    # Restart exim
    sudo('update-exim4.conf')
    sudo('service exim4 restart')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_nginx():
    """
    Installs and configures nginx server
    """
    
    # Install server software from repository
    install_software(['nginx-full'])
    
    # Create directory for nginx logs
    sudo('mkdir -p /var/log/%s' % ds.domain)
    
    # Create a self-signed SSL certificate if required
    if ds.use_https:
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
        'domain': ds.domain,
        'app_name': ds.app_name,
    }, rename=ds.domain)
    
    # enable the site
    sudo('rm /etc/nginx/sites-enabled/default')
    sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (ds.domain, ds.domain))


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_python():
    """
    Install Python and desired packages in a virtualenv at /var/venv
    """
    
    # Get the required software
    install_software([
        'python%s-dev' % ds.python_version,
        'libpcre3-dev',
        'libssl-dev',
        'gfortran',
        'libopenblas-dev',
        'liblapack-dev',
        'libfreetype6-dev',
        'libxft-dev',
        'python-virtualenv'
    ])
    
    # Make a virtual environment for the user and activate it
    sudo('mkdir -p /var/venv')
    sudo('chown %s:www-data /var/venv' % ds.username_main)
    with cd('/var/venv'):
        sudo('virtualenv --python=python%s %s' % (ds.python_version, ds.domain), user=ds.username_main, group='www-data')
    
    # Install python packages
        python_env = 'source %s/bin/activate && ' % ds.domain
        sudo(python_env + 'pip install django', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install uwsgi', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install psycopg2', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install south', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install numpy', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install scipy', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install matplotlib', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install pandas', user=ds.username_main, group='www-data')
        sudo(python_env + 'pip install sympy', user=ds.username_main, group='www-data')
        
    # Create Upstart file to run uWSGI
    upload_config('/etc/init', 'uwsgi.conf', {
        'app_name': ds.app_name,
        'domain': ds.domain,
    })


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def configure_django_workspace():
    
    # Configure app directory and make appropriate files and sub directories
    python_env = 'source /var/venv/%s/bin/activate && ' % ds.domain
    run('mkdir -p workspace/%s' % ds.domain)
    with cd('/home/%s/workspace/%s' % (ds.username_main, ds.domain)):
        run(python_env + 'django-admin.py startproject %s' % ds.app_name)
        
        upload_config('.', '.gitignore', {
            'app_name': ds.app_name,
        }, user=ds.username_main)
        run(python_env + 'pip freeze >> requirements.txt') # requirements file
        
        # Upload new django config file
        upload_config('%s/%s' % (ds.app_name, ds.app_name), 'settings.py', {
            'domain': ds.domain,
        }, user=ds.username_main)
    
        # Set up secrets.py file and change ownership to root
        password_email = random_password('MAIL USER')
        put('config/secrets_template.py', '%s/%s/secrets_template.py' % (ds.app_name, ds.app_name))
        upload_config('%s/%s' % (ds.app_name, ds.app_name), 'secrets_template.py', {
            'secret_key': random_password('DJANGO TEST SECRETKEY',80,120),
            'debug': 'True',
            'template_debug': 'True',
            'django_db_name': ds.django_db_test_name,
            'django_db_user': ds.django_db_test_user,
            'django_db_pwd': random_password('DJANGO TEST DATABASE'),
            'username_email': ds.username_email,
            'password_email': random_password('MAIL USER'),
        }, rename="secrets.py", user=ds.username_main, permissions='600')
        
        # Sync the database
        run(python_env + 'python %s/manage.py syncdb' % ds.app_name)
        #run(python_env + 'python manage.py schemamigration %s --initial' % app_name)
        #run(python_env + 'python manage.py migrate %s' % app_name)


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def setup_repo():
    """
    Sets up a git repository where the website code can live and be deployed from
    """
    
    # Install git
    install_software(['git'])
    
    # Set up a directory
    sudo('mkdir -p /home/git/%s.git' % ds.domain, user='git')
    with cd('/home/git/%s.git' % ds.domain):
        # Set up repository
        sudo('git --bare init', user='git')
        
    # Push to the git repository
    with cd('/home/%s/workspace/%s' % (ds.username_main, ds.domain)):
        run('git init')
        run('git config --global user.email "%s"' % ds.email_address_webmaster)
        run('git config --global user.name "%s"' % ds.username_main)
        run('git init')
        run('git add .')
        run('git commit -m "initial commit"')
        run('git remote add origin git@localhost:/home/git/%s.git' % ds.domain)
        run('git push origin master')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def setup_production_code():
    """
    Sets up production code on the server
    """
    
    # Deploy to webserver domain (via tutorial at 
    # http://grimoire.ca/git/stop-using-git-pull-to-deploy)
    sudo('mkdir -p /var/www/%s' % ds.domain)
    sudo('chown -R %s:www-data /var/www' % ds.username_main)
    with cd('/var/www/%s' % ds.domain):
        sudo('git init', user=ds.username_main, group='www-data')
        sudo('git remote add origin git@localhost:/home/git/%s.git' % ds.domain, user=ds.username_main, group='www-data')
        sudo('git fetch --all', user=ds.username_main, group='www-data')
        sudo('git checkout --force "origin/master"', user=ds.username_main, group='www-data')
        
        # Add production secrets file
        upload_config('%s/%s' % (ds.app_name, ds.app_name), 'secrets_template.py', {
            'secret_key': random_password('DJANGO SECRETKEY',80,120),
            'debug': 'False',
            'template_debug': 'False',
            'django_db_name': ds.django_db_name,
            'django_db_user': ds.django_db_user,
            'django_db_pwd': random_password('DJANGO DATABASE'),
            'username_email': ds.username_email,
            'password_email': random_password('MAIL USER'),
        }, rename="secrets.py", user=ds.username_main, group='www-data', permissions='640')
        
        # Create a static folder
        sudo('mkdir static', user=ds.username_main, group='www-data')
        
        python_env = 'source /var/venv/%s/bin/activate && ' % ds.domain
        
        # Syncdb
        sudo(python_env + 'python %s/manage.py syncdb' % ds.app_name, user=ds.username_main, group='www-data')
        
        # Collect static
        sudo(python_env + 'python %s/manage.py collectstatic' % ds.app_name, user=ds.username_main, group='www-data')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def setup_bash_aliases():
    """
    Sets up useful bash aliases for the main user
    """
    upload_config('.', '.profile', {
        'domain': ds.domain,
        'username_main': ds.username_main,
        'app_name': ds.app_name,
    }, user=ds.username_main)


# Helper functions
def upload_config(upload_location, local_file, values, rename=None, user='root', group=None, permissions='644'):
    """
    Creates a backup of the original file on the server, fills in the given
    template and then uploads it to the desired location.
    """
    if rename != None:
        external_file = rename
    else:
        external_file = local_file
        
    if group == None:
        group = user
    
    # Create and upload a configuration file
    sudo('mv %s/%s %s/%s.backup' % (upload_location, external_file, upload_location, external_file), warn_only=True)
    template = template_env.get_template(local_file)
    file = template.render(values)
    with open('tmp/%s' % external_file, 'wb') as fh:
        fh.write(file)
    put('tmp/%s' % external_file, '~')
    sudo('mv ~/%s %s' % (external_file, upload_location), warn_only=True)
    sudo('chown %s:%s %s/%s' % (user, group, upload_location, external_file))
    sudo('chmod %s %s/%s' % (permissions, upload_location, external_file))
    
    # remove the temp file if needed
    if ds.remove_temp_files:
        local('rm tmp/%s' % external_file)


def random_password(description, min_chars=10, max_chars=20):
    """
    Creates a random password from uppercase letters, lowercase letters and
    digits with a length between min_chars and max_chars
    """
    
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


def install_software(pkg_list, root=False):
    """
    Installs packages in the pkg_list

    :param pkg_list: packages to be installed
    :type pkg_list: list
    :param root: is the user installing the program root?
    :type root: boolean
    """

    # Check to see if packages are already installed
    install_pkgs = []
    for pkg in pkg_list:
        cmd_f = 'dpkg-query -l "%s" | grep -q ^.i'
        cmd = cmd_f % pkg
        with settings(warn_only=True):
            result = run(cmd)
            is_installed = result.succeeded
        if not is_installed:
            install_pkgs.append(pkg)

    # Install each package
    if install_pkgs:
        install_str = ' '.join(install_pkgs)
        if root:
            run('apt-get install -y %s' % install_str)
        else:
            sudo('apt-get install -y %s' % install_str)


def get_host():
    """
    Utility function get get the current operating user
    """
    return env.host_string.split('@')[0]

@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def temp():

    get('/etc/postfix/main.cf')
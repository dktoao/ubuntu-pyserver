"""
Fabric file for the deployment of a fully capable scientific web server on an
Ubuntu machine.
    
Author: Daniel Kuntz
"""

# Import settings
import deploy_settings as ds

# Imports
from os import path
from fabric.api import run, get, put, sudo, hosts, local, settings
from fabric.context_managers import cd, lcd
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
    upgrade()
    setup_config_version_control()
    setup_hosts()
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
    make_ssl_keys()
    install_postgres()
    install_mail_system()
    install_nginx()
    install_python()
    setup_repo()
    configure_local_workspace()
    setup_production_code()
    setup_bash_aliases()
    restart()


@hosts('root@%s' % ds.ip_address)
def upgrade():
    """
    Upgrade server software
    """
    
    #Update Repository
    run('apt-get update')
    run('apt-get -y upgrade')

@hosts('root@%s' % ds.ip_address)
def setup_config_version_control():
    """
    Setup a git repository that keeps track of changes to the /etc and /home
    folders
    """
    install_software(['git'], root=True)
    upload_config('/', '.gitignore_config', {}, rename='.gitignore')
    run('git config --global user.name "%s"' % ds.username_main)
    run('git config --global user.emal "%s@%s"' % (ds.username_main, ds.domain))
    with cd('/'):
        run('git init')
        run('git add .')
        run('git commit -m "setup_config_version_control"')
        
@hosts('root@%s' % ds.ip_address)
def setup_hosts():
    """
    Set up host configurations
    """
    
    # Set the hostname and mailname
    run('echo "%s" > /etc/hostname' % ds.server_name)
    run('hostname -F /etc/hostname')
    run('echo "%s" > /etc/mailname' % ds.domain)
    
    # Update the /etc/hosts file
    upload_config('/etc', 'hosts', {
        'server_name': ds.server_name,
        'domain': ds.domain,
        'ip_address': ds.ip_address,
    })
    do_git_commit('setup_hosts')

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
        run('chown -R %s:%s .' % (ds.username_main, ds.username_main))
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
    do_git_commit('setup_users')


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
    do_git_commit('setup_firewall')


@hosts('root@%s' % ds.ip_address)
def setup_fail2ban():
    """
    Install and setup fail2ban software
    """

    install_software(['fail2ban'], root=True)
    # Not necessary to commit because install_software already does


@hosts('root@%s' % ds.ip_address)
def remove_root_login():
    """
    Removing ability to log-in as root and set password login ability
    """
    
    config_edit('/etc/ssh/sshd_config', 
        '^PermitRootLogin.*$', 'PermitRootLogin no')
    config_edit('/etc/ssh/sshd_config',
        '^PasswordAuthentication.*$', 
        'PasswordAuthentication %s' %ds.password_login)
    do_git_commit('remove_root_login')


@hosts('root@%s' % ds.ip_address)
def restart():
    """
    Restart the server
    """
    sudo('reboot')


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def make_ssl_keys():
    """
    Creates a security keys, certificates and a group with permissions
    """
    # Create directory for public certs
    sudo('mkdir /etc/ssl/universal')
    sudo('mkdir /etc/ssl/universal/private')
    sudo('mkdir /etc/ssl/universal/certs')
    sudo('mkdir /etc/ssl/universal/public')

    # Create group for programs that need to access certificates
    sudo('addgroup secured')

    # Create keys and certificates needed for https, and email
    sudo('openssl genrsa -out private.key 1024')
    sudo('openssl rsa -in private.key -out public.key -pubout -outform PEM')
    sudo('openssl req -new -key private.key -out server.csr')
    sudo('openssl x509 -req -days 3650 -in server.csr -signkey private.key -out server.crt')

    # Download a copy of the public key
    #get('public.key', local_path='info')

    # Change access permissions for files
    sudo('chown root:secured private.key public.key server.crt')
    sudo('chmod 640 private.key public.key server.crt')

    # Move files to ssl location
    sudo('mv private.key /etc/ssl/universal/private/')
    sudo('mv public.key /etc/ssl/universal/public/')
    sudo('mv server.crt /etc/ssl/universal/certs/')
    sudo('mv server.csr /etc/ssl/universal/')

    do_git_commit("make_ssl_keys")


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_postgres():
    """
    Install and configure postgres with a user for Django
    """
    
    # Install postgres
    install_software([
        'postgresql-%s' % ds.postgres_version,
        'postgresql-contrib-%s' % ds.postgres_version,
        'postgresql-server-dev-%s' % ds.postgres_version,
    ])
    # Install the adminpack extension
    sudo('psql -c "CREATE EXTENSION adminpack"', user='postgres')
    # Create a django database user
    sudo('psql -c "CREATE USER %s WITH PASSWORD \'%s\'"' %
         (ds.django_db_user, random_password('DJANGO DATABASE')), user='postgres')
    # Create a database for django to use
    sudo('createdb -O %s %s' % (ds.django_db_user, ds.django_db_name), user='postgres')
    # Create a test database and test user
    if ds.local_test_db:
        sudo('psql -c "CREATE USER %s WITH PASSWORD \'%s\'"' %
             (ds.django_db_test_user, random_password('DJANGO TEST DATABASE')), user='postgres')
        sudo('createdb -O %s %s' % (ds.django_db_test_user, ds.django_db_test_name), user='postgres')
    # Update the postgres pg_hba.conf file
    config_append('/etc/postgresql/%s/main/pg_hba.conf' % ds.postgres_version, 
        '^\s*#\s*TYPE\s*DATABASE\s*USER\s*ADDRESS\s*METHOD\s*$',
        ['local  all  %s  md5' % ds.django_db_user, 
         'local  all  %s  md5' % ds.django_db_test_user])
    # Restart the postgres server
    sudo('service postgresql restart')
    
    #do_git_commit('install_postgres')

@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def install_mail_system():
    """
    Installs and configures the postfix SMTP server and other components
    required for email.  A very special thanks to grawity on the StackOverflow
    Super User boards, for the best simple email tutorial ever written.  I am sorry that
    I don't have any commenting power on those boards or I would have thanked you profusely!
    (http://superuser.com/questions/605521/the-simplest-way-to-set-up-a-secure-imap-email-server)
    """

    # Set the initial configuration options for installation
    # Postfix
    sudo('debconf-set-selections <<< "postfix postfix/mailname string %s"' % ds.domain)
    sudo('debconf-set-selections <<< "postfix postfix/main_mailer_type string \'Internet Site\'"')
    # Dovecot
    sudo('debconf-set-selections <<< "dovecot-core dovecot-core/create-ssl-cert string false"')

    # Install the required software
    install_software(['postfix', 'dovecot-imapd', 'opendkim', 'opendkim-tools'])

    # Add postfix and dovecot to the secured group
    sudo('usermod -G secured postfix')
    sudo('usermod -G secured dovecot')
    sudo('usermod -G secured dovenull')

    # Configure Postfix
    upload_config('/etc/postfix', 'main.cf', {
        'domain': ds.domain,
    })
    upload_config('/etc/postfix', 'master.cf', {})

    # Configure Dovecot
    upload_config('/etc/dovecot/conf.d', '10-auth.conf', {})
    upload_config('/etc/dovecot/conf.d', '10-mail.conf', {})
    upload_config('/etc/dovecot/conf.d', '10-master.conf', {})
    upload_config('/etc/dovecot/conf.d', '10-ssl.conf', {})

    # Create a DKIM key
    sudo('mkdir /etc/ssl/mail')
    sudo('opendkim-genkey -t -s %s -d %s' % (ds.dkim_selector, ds.domain))
    get('%s.txt' % ds, local_path='info')
    sudo('chown root:opendkim %s.private' % ds.dkim_selector)
    sudo('chmod 640 %s.private')
    sudo('mv %s.private /etc/ssl/mail/' % ds.dkim_selector)
    sudo('mv %s.txt /etc/ssl/mail' % ds.dkim_selector)

    # Configure OpenDKIM
    upload_config('/etc', 'opendkim.conf', {
        'domain': ds.domain,
        'dkim_selector': ds.dkim_selector,
    })
    upload_config('/etc/default', 'opendkim', {})

    # Restart programs
    sudo('service dovecot restart')
    sudo('service opendkim restart')
    sudo('service postfix restart')


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
        sudo('usermod -G secured www-data')
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
        sudo('virtualenv --python=python%s %s' %
             (ds.python_version, ds.domain), user=ds.username_main, group='www-data')
    
    # Install python packages
        python_env = 'source %s/bin/activate && ' % ds.domain
        if ds.python_req_file:
            put(ds.python_req_file, '~')
            sudo(python_env + 'pip install -r ~/%s' % path.split(ds.python_req_file)[1])
            run('rm ~/%s' % path.split(ds.python_req_file)[1])

        else:
            sudo(python_env + 'pip install django', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install uwsgi', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install psycopg2', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install numpy', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install scipy', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install matplotlib', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install pandas', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install sympy', user=ds.username_main, group='www-data')
            sudo(python_env + 'pip install django-treebeard', user=ds.username_main, group='www-data')
        
    # Create Upstart file to run uWSGI
    upload_config('/etc/init', 'uwsgi.conf', {
        'app_name': ds.app_name,
        'domain': ds.domain,
    })


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

    # Push provided local git project
    if (not ds.make_new_project) and ds.existing_repo_location:
        with lcd(ds.existing_repo_location):
            local('git remote add %s git@%s:/home/git/%s.git' % (ds.server_name, ds.domain, ds.domain))
            local('git push %s master' % ds.server_name)


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def configure_local_workspace():

    # Configure app directory and make appropriate files and sub directories
    python_env = 'source /var/venv/%s/bin/activate && ' % ds.domain
    run('mkdir -p workspace/%s' % ds.domain, warn_only=True)

    with cd('/home/%s/workspace/%s' % (ds.username_main, ds.domain)):

        # Setup a local git repository
        run('git init')
        run('git config --global user.email "%s"' % ds.email_address_webmaster)
        run('git config --global user.name "%s"' % ds.username_main)
        run('git remote add origin git@localhost:/home/git/%s.git' % ds.domain)

        # If we are making a new project
        if ds.make_new_project:
            run(python_env + 'django-admin.py startproject %s' % ds.app_name)

            upload_config('.', '.gitignore', {
                'app_name': ds.app_name,
            }, user=ds.username_main)

            run(python_env + 'pip freeze >> requirements.txt')  # requirements file

            # Upload new django config file
            upload_config('%s/%s' % (ds.app_name, ds.app_name), 'settings.py', {
                'domain': ds.domain,
            }, user=ds.username_main)

        else:
            run('git pull origin master')

        # Set up secrets.py file and change the ownership to root
        if ds.make_new_project:
            put('config/secrets_template.py', '%s/%s/secrets_template.py' % (ds.app_name, ds.app_name))

        upload_config('%s/%s' % (ds.app_name, ds.app_name), 'secrets_template.py', {
            'secret_key': random_password('DJANGO TEST SECRETKEY', 80, 120),
            'debug': 'True',
            'template_debug': 'True',
            'django_db_name': ds.django_db_test_name,
            'django_db_user': ds.django_db_test_user,
            'django_db_pwd': random_password('DJANGO TEST DATABASE'),
            'username_email': ds.username_email,
            'password_email': random_password('MAIL USER'),
        }, rename="secrets.py", user=ds.username_main, permissions='600')

        # Push to the repository if new project was created, pull from repository if project already exists
        if ds.make_new_project:
            run('git add .')
            run('git commit -m "Inital Commit"')
            run('git push origin master')

        # Syncdb to be done manually with launched project
        if ds.local_test_db and ds.make_new_project:
            run(python_env + 'python %s/manage.py syncdb' % ds.app_name)


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
        sudo('git remote add origin git@localhost:/home/git/%s.git' %
             ds.domain, user=ds.username_main, group='www-data')
        sudo('git fetch --all', user=ds.username_main, group='www-data')
        sudo('git checkout --force "origin/master"', user=ds.username_main, group='www-data')

        # Add production secrets file
        upload_config('%s/%s' % (ds.app_name, ds.app_name), 'secrets_template.py', {
            'secret_key': random_password('DJANGO SECRETKEY', 80, 120),
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

        # Syncdb (to be done manually with deployment of existing code
        if ds.make_new_project:
            sudo(python_env + 'python %s/manage.py syncdb' % ds.app_name, user=ds.username_main, group='www-data')

            # Collect static
            sudo(python_env + 'python %s/manage.py collectstatic' %
                 ds.app_name, user=ds.username_main, group='www-data')


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
    if rename is not None:
        external_file = rename
    else:
        external_file = local_file
        
    if group is None:
        group = user
    
    # Create and upload a configuration file
    # Still need to do this even though we are under version control?
    #sudo('mv %s/%s %s/%s.backup' % (upload_location, external_file, upload_location, external_file), warn_only=True)
    template = template_env.get_template(local_file)
    config_file = template.render(values)
    with open('tmp/%s' % external_file, 'wb') as fh:
        fh.write(config_file)
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


def install_software(pkg_list, root=False, update_repo=True):
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
    if not install_pkgs:
        return

    install_str = ' '.join(install_pkgs)
    if root:
        run('apt-get install -y %s' % install_str)
    else:
        sudo('apt-get install -y %s' % install_str)

    # Update the repo if needed
    if update_repo:
        do_git_commit('installed: %s' % install_str)

def do_git_commit(message):
    with cd('/'):
        sudo('git add .')
        sudo('git commit -m "%s"' % message)

def config_edit(filename, original, replace):
    run("sed -i 's/%s/%s/' %s" % (original, replace, filename))

def config_append(filename, search_for, append_lines):
    line_number = sudo('grep -n "%s" -e "%s"' % (filename, search_for))
    line_number = int(line_number.split(':')[0])
    for (idx, line) in enumerate(append_lines):
        sudo("sed -i '%da %s' %s" % (line_number+idx, line, filename))


@hosts('%s@%s' % (ds.username_main, ds.ip_address))
def temp():
    config_append('/etc/postgresql/%s/main/pg_hba.conf' % ds.postgres_version, 
        '^\s*#\s*TYPE\s*DATABASE\s*USER\s*ADDRESS\s*METHOD\s*$',
        ['local   all             %-30s          md5' % ds.django_db_user, 
         'local   all             %-30s          md5' % ds.django_db_test_user])

ubuntu-pyserver
=====================

_Fabric file for the deployment of a personal, fully capable, web server on an with Ubuntu LTS linux distro._

## USE
1. Insure that you have a public ssh key at ~/.ssh/
2. Make a copy of deploy\_settings\_template.py in deploy\_settings.py and put in the appropriate server settings
3. Install the requirements listed below
4. run "fab full\_setup" to setup server
5. Wait for restart
6. run "fab full\_deploy" to configures server and install pakages.
7. Enjoy!

## REQUIREMENTS
- fabric
- jinja2

## SERVER SPECS

### Computing
- Python / Django, Set up with proper virtualenv, a super
user account and a migration ready connection to a PostgreSQL database
    - Django
    - psycopg2
    - (or via supplied "requriements.txt" file)
        
### Database
- PostgreSQL
    
### Server Stack
- uWSGI
- nginx
    
### Email
- Postfix (SMTP)
- Dovecot (IMAP)
- Authentication via DKIM
    
### App Deployment
- Git, set up to automatically deploy to a production server
- On server workspace that is easily connected to Cloud9 IDE.
    
### Security
- iptables firewall
- appropriate user accounts
    - outside ssl access to all users
    - internal ssl access to git user from main user account
- fail2ban
- https with self signed ssl cert (optional)

### Utilities
- Alias for one time run in virtualenv "runenv"
- Alias for loading virtualenv "loadenv"
- Alias to run the test server on port 8080 "runtestserver"
- Varios goto-* aliases to move around filesystem
    - (goto-)env: virtualenv root
    - www: web root directory
    - live: production code root
    - wspc: on-server workspace
    - repo: git repository

## ADDITIONAL MANUAL DEPLOYMENT STEPS

### Important install considerations
1. Make sure that the app_name variable in the fabfile is a legal python
application name
2. If you do not have an ssh key setup in your home directory at
~/.ssh/id_rsa.pub then you will need to do so before you run this script.

### TODO Manually after install
1. Update the DNS DKIM records with the contents of info/dkim.public.key
2. Update the DNS SPF records to show send ip addresses
3. After running create a local repository and connect it to remote 
git@{ip\_address}:~/{domain\_name}.git
4. Create a local secrets.py file 
5. Tweak the values in /etc/init/uwsgi.conf to match server specs
6. Replace the self signed certificates and keys at /etc/ssl/universal/certs/server.crt
to a non self-signed certificate

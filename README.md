Ubuntu14LTS-SciServer
=====================

_Fabric file for the deployment of a fully capable web server on an 
Ubuntu 14.04 LTS machine._

## Requirements
- fabric
- jinja2

## SERVER SPECS

### Computing
- Python / Django, Set up with proper virtualenv, a super
user account and a migration ready connection to a PostgreSQL database
    - Django
    - Numpy
    - Scipy
    - Pandas
    - Matplotlib
    - psycopg2
    - South (depreciated with Django 1.7)
        
### Database
- PostgreSQL
    
### Server Stack
- uWSGI
- nginx
    
### Email
- Exim (send only)
- Authentication via DKIM
    
### App Deployment
- Git, set up to automatically deploy to a production server
- On server workspace that is easily connected to Cloud9 ide.
    
### Security
- iptables firewall
- appropriate user accounts
    - outside ssl access to all users
    - internal ssl access to git user from main user account
- fail2ban
- https with self signed ssl cert (optional)

### Utilities
- Setup alias for virtualenv "loadenv"

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
git@{ip_address}:/{repository_root}/{domain name}.git
4. Create a local secrets.py file 
5. Tweak the values in /etc/init/uwsgi.conf to match server specs
6. Replace the self signed certificates and keys at /etc/cert/ to a non self-signed 
certificate

Ubuntu14LTS-SciServer
=====================

This is a fabric file that can be used to automate the setup and deployment of a scientific web server with Python (Django, numpy, scipy, matplotlib), Postgresql and nginx web server

## INFO FOR NEWLY INSTALLED SERVER ##

## Important install considerations ##
1. Make sure that the app_name variable in the fabfile is a legal python
application name
2. If you do not have an ssh key setup in your home directory at
~/.ssh/id_rsa.pub then you will need to do so before you run this script.

## TODO Manually after install ##
1. Update the DNS DKIM records with the contents of info/dkim.public.key
2. Update the DNS SPF records to show send ip addresses
3. After running create a local repository and connect it to remote 
git@<ip address>:/var/repo/<domain name>.git
4. Create a local secrets.py file 
5. Tweak the values in /etc/init/uwsgi.conf to match server specs
6. Replace the self signed certificates and keys at /etc/cert/ to a non self-signed 
certificate

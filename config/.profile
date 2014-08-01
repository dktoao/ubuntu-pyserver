# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.
# see /usr/share/doc/bash/examples/startup-files for examples.
# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask
# for ssh logins, install and configure the libpam-umask package.
#umask 022

# if running bash
if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
	. "$HOME/.bashrc"
    fi
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

# Aliases and functions for commonly used commands
alias runenv="env - PATH=\"/var/venv/{{domain}}/bin:$PATH\" "
alias loadenv="source /var/venv/{{domain}}/bin/activate"
alias runtestserver="runenv python /home/{{username_main}}/workspace/{{domain}}/{{app_name}}/manage.py runserver 0.0.0.0:8080"
alias goto-env="cd /var/venv/{{domain}}"
alias goto-www="cd /var/www"
alias goto-live="cd /var/www/{{domain}}"
alias goto-wspc="cd /home/{{username_main}}/workspace/{{domain}}"
alias goto-repo="cd /home/git/{{domain}}.git"

installpypkg ()
{
    newgrp www-data
    runenv pip install $1
    runenv pip freeze >> /var/www/{{domain}}/requirements.txt
    exit
}

livedeploy ()
{
    newgrp www-data
    cd /var/www/{{domain}}
    git fetch --all
    git checkout --force \"origin/master\"
    exit
}

migrateproddb ()
{
    cd /var/www/{{domain}}
    runenv python {{app_name}}/manage.py syncdb
    runenv python {{app_name}}/manage.py migrate
    cd ~
}

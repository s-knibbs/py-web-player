#!/usr/bin/python
import os
import sys
import shutil
from subprocess import check_call, CalledProcessError

from cast_server.config import config

APACHE_SITES_DIR = '/etc/apache2/sites-available/'
SITE_CONFIG_FILE = 'html5_cast_server.conf'


def setup_apache():
    with open(os.path.join(APACHE_SITES_DIR, SITE_CONFIG_FILE), 'w') as config_fd:
        config
    check_call(['a2ensite', SITE_CONFIG_FILE[:-5]])
    # Restart apache
    print "Restarting apache..."
    check_call(['apache2ctl', 'restart'])


def create_environment():
  """Creates the initial enviroment."""

def discover_files()
    print 'Discovering media...'
    # TODO Get login user
    USER = None
    default_search_path = os.path.expanduser('~%s/Music' % USER)
    if not os.path.exists(default_search_path):
        default_search_path = os.getcwd()
    path = raw_input('Media directory [%s]: ' % default_search_path)
    path = path or default_search_path


if __name__ == '__main__':
  pass

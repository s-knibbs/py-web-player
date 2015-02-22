#!/usr/bin/python
"""Script for configuring the server and importing the initial data.
This script must be run as root.
"""
import sys
import os
import pwd
import logging
from subprocess import check_call, check_output, CalledProcessError

from config import config
from discover import MediaDiscovery
from model import MediaLibrary


def create_environment():
    """Creates the initial enviroment."""
    print "Creating environment..."
    os.umask(0002)  # rw-rw-r--
    os.makedirs(config.ENV_DIR)
    entry = pwd.getpwnam('www-data')
    os.chown(config.ENV_DIR, entry.pw_uid, entry.pw_gid)
    config.create_wsgi_script(entry.pw_uid, entry.pw_gid)
    os.mkdir(config.CACHE_DIR)
    os.chown(config.CACHE_DIR, entry.pw_uid, entry.pw_gid)


def setup_apache():
    """Create the apache config and enables
    the site.
    """
    config.create_apache_config()
    try:
        # Enable wsgi
        check_call(['a2enmod', 'wsgi'])
        check_call(['a2ensite', config.APP_NAME])
        # Restart apache
        print "Restarting apache..."
        check_call(['apache2ctl', 'restart'])
    except CalledProcessError:
        print >> sys.stderr, "Failed to configure apache"


def discover_files():
    """Performs the initila file discovery"""
    print 'Discovering media...'
    USER = check_output(['logname']).strip()
    default_search_path = os.path.expanduser('~%s/Music' % USER)
    if not os.path.exists(default_search_path):
        default_search_path = os.getcwd()
    path = raw_input('Media directory [%s]: ' % default_search_path)
    path = path or default_search_path
    with MediaLibrary() as library:
        discovery = MediaDiscovery(library)
        items_found = discovery.search([path])
        print "Indexed %s items" % items_found


def main():
    """Entry point for the script"""
    logging.basicConfig(level=logging.WARNING, format=config.LOG_FORMAT)
    if not os.path.exists(config.ENV_DIR):
        create_environment()
    if not os.path.exists(config.APACHE_CONFIG):
        setup_apache()
    discover_files()


if __name__ == '__main__':
    main()

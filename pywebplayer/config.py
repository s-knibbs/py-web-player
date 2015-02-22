from ConfigParser import SafeConfigParser
import os
import logging
from distutils.util import strtobool


# TODO Finish apache configuration
_APACHE_CONF_TMPL = r"""
<VirtualHost *:81>

DocumentRoot %(install)s/htdocs/

Alias /cached/ %(cache_dir)s/
Alias /static/ %(install)s/htdocs/

WSGIScriptAlias / %(env)s/app.wsgi
WSGIDaemonProcess %(name)s user=www-data group=www-data processes=1 threads=5

LogFormat "%%h %%l %%u %%t \"%%r\" %%>s" access
CustomLog /var/log/apache2/access.log access

AddType audio/ogg .ogg
AddType audio/mp3 .mp3
AddType audio/mp4 .mp4
AddType audio/mp4 .m4a
AddType audio/wav .wav
AddType audio/webm .webm

XSendFile On
XSendFilePath %(cache_dir)s/

<Location />
  Require all granted
  <IfModule headers_module>
    Header set Access-Control-Allow-Origin "*"
  </IfModule>
</Location>

<Directory %(cache_dir)s>
  Options Indexes FollowSymlinks
  Header set Accept-Ranges bytes
</Directory>

</VirtualHost>
"""


_WSGI = """\
#!/usr/bin/python
from pywebplayer.config import config
from pywebplayer import web_ui

config.setup_logging()
web_ui.app.catchall = False  # Let mod_wsgi handle any exceptions
application = web_ui.app
"""


_APACHE_SITES_DIR = '/etc/apache2/sites-available'


_APP_NAME = 'PyWebPlayer'


_ENV_DIR = '/var/lib/%s' % _APP_NAME


class config(object):
    """Config file handling, plus global
    constants.
    """
    # Hardcoded constants
    VERSION = "0.1"
    # Application name
    APP_NAME = _APP_NAME
    # Data directory
    ENV_DIR = _ENV_DIR
    # Transcode cache directory
    CACHE_DIR = os.path.join(_ENV_DIR, 'cache')
    # Log file name
    LOG_FILE = os.path.join(_ENV_DIR, 'app.log')
    # Db file name
    DB_FILE = os.path.join(_ENV_DIR, 'library.db')
    # Config file name
    CONF_FILE = os.path.join(_ENV_DIR, 'app.ini')
    # Wsgi script file
    WSGI_FILE = os.path.join(_ENV_DIR, 'app.wsgi')
    # Apache config file
    APACHE_CONFIG = os.path.join(_APACHE_SITES_DIR, _APP_NAME + '.conf')
    # Log output format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s: %(message)s'

    @classmethod
    def setup_logging(cls, level=logging.WARNING):
        """Setup the log file with the given log level.
        Default is WARNING.
        """
        logging.basicConfig(
            filename=os.path.join(cls.ENV_DIR, cls.LOG_FILE),
            format=cls.LOG_FORMAT,
            level=level
        )

    @classmethod
    def load_config_section(cls, section):
        """Loads the config section. Returns
        a dict containing the values for that section.
        """
        parser = SafeConfigParser()
        parser.read(cls.CONF_FILE)
        if parser.has_section(section):
            return dict(parser.items(section))
        return None

    @classmethod
    def save_config_section(cls, section, config_dict):
        """Saves the options in config_dict under the given section"""
        pass

    @classmethod
    def create_apache_config(cls):
        """Writes the apache configuration"""
        install_dir = os.path.dirname(__file__)
        with open(cls.APACHE_CONFIG, 'w') as apache_config:
            apache_config.write(
                _APACHE_CONF_TMPL % {
                    'install': install_dir, 'env': cls.ENV_DIR, 'name': cls.APP_NAME,
                    'cache_dir': cls.CACHE_DIR
                }
            )

    @classmethod
    def create_wsgi_script(cls, uid, gid):
        """Create the WSGI script and assign the correct
        permissions
        """
        with open(cls.WSGI_FILE, 'w') as wsgi_file:
            wsgi_file.write(_WSGI)
        os.chmod(cls.WSGI_FILE, 0554)
        os.chown(cls.WSGI_FILE, uid, gid)


class ComponentBase(object):
    """Base class to provide config handling and logging
    facilities.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_config(self):
        """Loads the config for a given component"""
        conf = config.load_config_section(self.__class__.__name__.lower())
        if conf is not None:
            for key, value in conf.iteritems():
                # Set constants defined in the config
                try:
                    attr_type = type(getattr(self, key.upper()))
                    if type is int:
                        value = int(value)
                    elif type is bool:
                        value = strtobool(value)
                    setattr(self, key.upper(), value)
                except ValueError:
                    self.logger.warning(
                        "Invalid value for %s in config, expecting %s" % (key, attr_type.__name__)
                    )
        else:
            self.logger.info("No config section found, using default config")

    def save_default_config(self):
        """Saves the default configuration for a component"""
        raise NotImplementedError

    def _save_config(self, **kwargs):
        """Saves the config for the given component"""
        config_dict = {}
        for key, value in kwargs.items():
            config_dict[key.lower()] = str(value)
        config.save_config_section(self.__class__.__name__.lower(), config_dict)

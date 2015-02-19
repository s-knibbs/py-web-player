import ConfigParser
import os
import logging


# TODO Finish apache configuration
__APACHE_CONF_TMPL = """\
<VirtualHost *:81>

DocumentRoot %(install)s/htdocs/

Alias /cached/ %(env)s/cached/

WSGIScriptAlias / %(env)s/app.wsgi

LogFormat "%%h %%l %%u %%t \"%%r\" %%>s" access
CustomLog /var/log/apache2/access.log access

AddType audio/ogg .ogg

<Location />
  Require all granted
  <IfModule headers_module>
    Header set Access-Control-Allow-Origin "*"
  </IfModule>
</Location>

</VirtualHost>
"""

__WSGI = """\
from config import config
import web_ui

config.load_config()
application = web_ui.get_app()
"""


class config(object):
    """Config file handling, plus global
    constants.
    """
    # Hardcoded constants
    # Data directory
    ENV_DIR = '/var/lib/cast-server/'
    # Log file name
    LOG_FILE = 'app.log'
    # Db file name
    DB_FILE = os.path.join(ENV_DIR, 'library.db')
    # Config file name
    CONF_FILE = os.path.join(ENV_DIR, 'cast_server.ini')

    @classmethod
    def setup_logging(cls, level=logging.WARNING):
      """Setup the log file with the given log level.
      Default is WARNING.
      """
      # TODO Setup formatter
      logging.basicConfig(os.path.join(cls.ENV_DIR, cls.LOG_FILE), level)
      pass

    @classmethod
    def load_config_section(cls, section):
      """Loads the config section. Returns
      a dict containing the values for that section.
      """
      # TODO
      pass

    @classmethod
    def save_config_section(cls, section, config_dict):
      # TODO
      pass

    @classmethod
    def create_apache_config(cls):
        # TODO

    @classmethod
    def create_wsgi_script(cls):
        # TODO


class ComponentBase(object):
  """Base class to provide config handling and logging
  facilities.
  """

  def __init__(self):
    self.logger = logging.getLogger(self.__class__.__name__)


  def _load_config(self):
    conf = config.load_config_section(self.__class__.__name__.lower())
    if conf is not None:
        for key, value in conf.iteritems():
            # Set constants defined in the config
            setattr(self, key.upper(), value)
    else:
        self.logger.info("No config section found, using default config")

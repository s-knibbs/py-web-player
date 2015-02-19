import sqlite3
import os
from functools import wraps
from config import config, ComponentBase

__all__ = ["MediaLibrary"]


def with_rollback(func):
  """Decorator, providing auto rollback facilities"""
  @wraps(func)
  def wrapper(*args, **kwargs):
    self = args[0]
    try:
      func(*args, **kwargs)
    except Exception as e:
      self.logger.warning("Transaction failed, rolling back: %s" % str(e))
      self.conn.rollback()
      raise e
  return wrapper


class MediaItem(object):

  def __init__(self, media_id, name, path, length, size, mime_type, library):
    self.id = media_id
    self.path = path
    self.name = name
    self.length = length
    self.size = size
    self.mime_type = mime_type
    self.library = library  # Back reference to the media library class
    self.props = None  # Dict containing the media properties, lazily loaded.

  def __getitem__(self, key):
    if self.props is None:
      self.props = self.library._get_props(self.id)
    return self.props[key]


class MediaLibrary(ComponentBase):

  __SCHEMA = """\
create table media (
  id   integer primary key autoincrement,
  name text not null,
  path text not null,
  length integer not null, -- length in seconds
  size integer not null, -- size in bytes
  mime_type text,
  unique (path) on conflict replace
);

create table media_info (
  media_id integer, -- Foreign key: media.id
  name text,
  value text,
  primary key (media_id, name)
);
"""

  def __init__(self, db_file=config.DB_FILE):
    super(MediaLibrary, self).__init__()
    self.db_file = db_file
    self.conn = None

  def connect(self):
    schema_required = (not os.path.exists(self.db_file))
    try:
        self.conn = sqlite3.connect(self.db_file)
    except Exception as e:
        self.logger.error('Failed to connect to the database at %s: %s' % (self.db_file, str(e)))
        raise e 
    if schema_required:
      self._create_schema()

  def _get_max_id(self, cursor):
    cursor.execute("SELECT MAX(id) FROM media")
    res = cursor.fetchone()[0]
    if res is not None:
      return res
    return 0

  def save(self):
    """Commits any current transaction."""
    self.conn.commit()

  @with_rollback
  def insert(self, name, path, length, size, mime_type=None, props=None):
    cursor = self.conn.cursor()
    insert_id = self._get_max_id(cursor) + 1
    params = {'name': name, 'path': path, 'length': length,
              'size': size, 'mimetype': mime_type}
    cursor.execute("""INSERT INTO media ("name", "path", "length", "size", "mime_type")
                   VALUES (:name, :path, :length, :size, :mimetype)""",
                   params)
    if props is not None:
      for name, value in props.items():
        cursor.execute("""INSERT INTO media_info VALUES (:id, :name, :value)""",
                       {'id': insert_id, 'name': name, 'value': value})

  def get_all(self):
    cursor = self.conn.cursor()
    cursor.execute("""SELECT id, name, path, length, size, mime_type FROM media""")
    items = []
    for row in cursor.fetchall():
      items.append(MediaItem(*row, library=self))
    return items

  def get_item(self, media_id):
    cursor = self.conn.cursor()
    cursor.execute("""SELECT id, name, path, length, size, mime_type FROM media
                   WHERE id=:id""", {'id': media_id})
    res = cursor.fetchone()
    if res is not None:
      return MediaItem(*res, library=self)
    return None

  def _get_props(self, media_id):
    if self.conn is None:
      self.connect()
    cursor = self.conn.cursor()
    cursor.execute("""SELECT name, value FROM media_info WHERE id=:id""", {'id': media_id})
    props = {}
    for name, value in cursor.fetchall():
      props[name] = value
    return props

  def _create_schema(self):
    self.logger.info("Creating database schema")
    cursor = self.conn.cursor()
    try:
        cursor.executescript(self.__SCHEMA)
    except Exception as e:
        self.logger("Failed to create the database schema: %s" % str(e))
        raise e

  def __enter__(self):
    self.connect()
    return self

  def __exit__(self, *_):
    self.conn.close()
    self.conn = None

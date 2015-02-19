import os
import time
import logging
import sys

from config import ComponentBase
from model import MediaLibrary
from transcode import Transcoder


class DiscoveryError(object):
  pass


class MediaDiscovery(ComponentBase):

  # TODO Improve mime-type detection capabilities
  MIME_MAP = {
    '.mp3': 'audio/mp3',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.mp4': 'audio/mp4',
    '.aac': 'audio/aac'
  }
  DURATION_FORMAT = '%H:%M:%S'
  MAX_DEPTH = 4

  def __init__(self, library):
    super(MediaDiscovery, self).__init__()
    self.library = library

  def search(self, paths, depth=0):
    num_items = 0
    sub_paths = []
    transcoder = Transcoder()
    if len(paths) == 0 or depth >= self.MAX_DEPTH:
      return 0
    for path in paths:
      try:
        for entry in os.listdir(path):
          abspath = os.path.join(path, entry)
          if os.path.isdir(abspath):
            sub_paths.append(abspath)
            continue
          name, ext = os.path.splitext(entry)
          if ext in self.MIME_MAP:
            info = transcoder.get_media_info(abspath)
            if info is None:
              continue
            size = os.stat(abspath).st_size
            length = self._duration_to_secs(info['duration'])
            self.library.insert(name, abspath, length, size, self.MIME_MAP[ext], info)
            num_items += 1
      except OSError as e:
        self.logger.warning(str(e))
      self.library.save()
    return self.search(sub_paths, depth + 1) + num_items

  def _duration_to_secs(self, duration):
    ts = time.strptime(duration, self.DURATION_FORMAT)
    return ts.tm_hour * 3600 + ts.tm_min * 60 + ts.tm_sec

  def start_watching(self):
    pass
    # TODO - Implement file system watching


if __name__ == "__main__":
  with MediaLibrary() as library:
    discovery = MediaDiscovery(library)
    item_count = discovery.search([sys.argv[1]])
  print "Added %s items to the database" % item_count

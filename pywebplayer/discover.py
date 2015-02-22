import os
import time

from config import ComponentBase
from transcode import Transcoder


class MediaDiscovery(ComponentBase):

    DURATION_FORMAT = '%H:%M:%S'
    MAX_DEPTH = 4

    def __init__(self, library):
        super(MediaDiscovery, self).__init__()
        self.library = library

    def search(self, paths, depth=0):
        """Search the given paths for media files"""
        num_items = 0
        sub_paths = []
        tcoder = Transcoder()
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
                    ext = ext[1:]
                    if ext in tcoder.MIME_MAP:
                        info = tcoder.get_media_info(abspath)
                        if info is None:
                            continue
                        size = os.stat(abspath).st_size
                        length = self._duration_to_secs(info['duration'])
                        self.library.insert(name, abspath, length, size,
                                            tcoder.MIME_MAP[ext], info, ignore_duplicates=True)
                    num_items += 1
            except OSError as e:
                self.logger.warning(str(e))
            self.library.save()
        return self.search(sub_paths, depth + 1) + num_items

    def _duration_to_secs(self, duration):
        """Converts a duration string into seconds"""
        # TODO - Support sub second precision
        ts = time.strptime(duration, self.DURATION_FORMAT)
        return ts.tm_hour * 3600 + ts.tm_min * 60 + ts.tm_sec

    def start_watching(self):
        """Watch the filesystem for any new media files
        and add them to the database automatically.
        """
        pass
        # TODO - Implement file system watching

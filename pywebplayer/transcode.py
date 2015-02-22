import subprocess
import os
import re
import tempfile
from Queue import Queue, Empty
from config import ComponentBase, config


class Transcoder(ComponentBase):
    """Interacts with ffmpeg to handle transcoding of media items.
    Manages a cache of transcoded items.
    """

    AUDIO_CODEC = 'libvorbis'
    AUDIO_CONTAINER = 'webm'
    AUDIO_QUALITY = '4'
    BUF_SIZE = 4096
    MIME_MAP = {
      'mp3': 'audio/mp3',
      'ogg': 'audio/ogg',
      'flac': 'audio/flac',
      'm4a': 'audio/mp4',
      'mp4': 'audio/mp4',
      'aac': 'audio/aac',
      'webm': 'audio/webm',
      'wav': 'audio/wav'
    }

    def __init__(self):
        super(Transcoder, self).__init__()
        self._load_config()
        # TODO - Handle caching in a separate class
        self.transcode_cache = {}
        self._load_cached_items()
        # Regex's for parsing file metadata from ffmpeg / ffprobe
        # TODO - Use XML / JSON output from ffprobe
        self.metadata_re = re.compile(r'\s+([a-zA-Z]+)\s+: (.+)')
        self.metadata_start_re = re.compile(r'\s+Metadata:')
        self.duration_re = re.compile(r'\s+(Duration): ([0-9:]+)')
        self.process_queue = Queue()  # Queue to hold any background ffmpeg processes

    def _load_cached_items(self):
        """Load the existing cached files."""
        count = 0
        for entry in os.listdir(config.CACHE_DIR):
            name, ext = os.path.splitext(entry)
            if name.isdigit():
                count += 1
                self.add_cached_file(int(name), os.path.join(config.CACHE_DIR, entry), ext[1:])
        self.logger.info("Found %s existing items in the cache" % count)

    def get_output_type(self, item, accept_types, background=False):
        """Get the best available output type based
        on the item type and user-agent accept types.
        Returns None if the browser does not support any of the
        audio formats.
        """
        # TODO - Handle case where accept contains only '*/*'
        accept_type_names = [val.split(';') for val in accept_types]
        if item.mime_type in accept_type_names:
            # TODO - Use item.available instead of cached
            item.cached = True
            return item.mime_type
        else:
            cached_item = self.transcode_cache.get(item.id)
            if cached_item is not None:
                item.cached = True
                for container in cached_item:
                    return self.MIME_MAP[container]
            else:
                if background:
                    return self.MIME_MAP[self.AUDIO_CONTAINER]
                return self.MIME_MAP['wav']

    def check_background_processes(self):
        """Check on any ffmpeg processes running in the background"""
        running_items = []
        try:
            while True:
                proc, tmp, media_id, out_file = self.process_queue.get_nowait()
                proc.poll()
                if proc.returncode is None:
                    running_items.append((proc, tmp, media_id, out_file))
                else:
                    self._on_ffmpeg_complete(proc, tmp.name, media_id, out_file)
        except Empty:
            # Put any processes still running back on the queue
            for item in running_items:
                self.process_queue.put(item)
        return len(running_items) > 0

    def get_album_art(self, path, artist, album):
        """Get the album art for the given path and store to the album
        art cache. Extracts from the audio file if possible.
        """
        # TODO
        pass

    def start_transcode(self, path, media_id, background=False):
        """Transcode the audio to ogg vorbis only for
        now. Uses ffmpeg to perform the transcode.
        Returns a generator for reading the buffered data.
        """
        # Send stderr to a temporary file for later reading
        tmp = tempfile.NamedTemporaryFile()
        codec = self.AUDIO_CODEC
        container = self.AUDIO_CONTAINER
        if not background:  # Use wav format when streaming for low latency
            codec = 'pcm_s16le'
            container = 'wav'
        cache_file_name = self._get_cache_file_name(media_id, container)
        proc = self._start_ffmpeg(path, tmp, cache_file_name, codec, container)
        if True:
            self.process_queue.put((proc, tmp, media_id, cache_file_name))
            return proc
        else:
            return self._stream_generator(proc, tmp, cache_file_name, media_id)

    def _stream_generator(self, proc, tmp, cache_file_name, media_id):
        """Generator for streaming the output of the ffmpeg process"""
        # TODO - Find a way to enable seeking when streaming ffmpeg output.
        # Currently not possible, since ffmpeg does not set the file duration when piping
        cache_file = open(cache_file_name, 'w')
        terminated = False
        buf = bytes()
        try:
            try:
                while proc.returncode is None:
                    try:
                        buf = proc.stdout.read(self.BUF_SIZE)
                        cache_file.write(buf)
                        yield buf
                        proc.poll()  # Check return status
                    except IOError as e:  # Handle client closing the connection
                        proc.terminate()
                        terminated = True  # Return will be non-zero if we terminated
                        self.logger.warning(str(e))
            finally:
                cache_file.close()
            self._on_ffmpeg_complete(proc, tmp.name, media_id, cache_file_name, terminated)
        finally:
            tmp.close()
        raise StopIteration

    def _get_cache_file_name(self, media_id, container):
        """Returns the full path of the cache file."""
        return os.path.join(
            config.CACHE_DIR, "%s.%s" % (media_id, container)
        )

    def _on_ffmpeg_complete(self, ffmpeg_proc, tmp_name, media_id, cache_file_name, terminated=False):
        """Checks the return status of ffmpeg and updates the transcode cache"""
        if ffmpeg_proc.returncode != 0:
            os.unlink(cache_file_name)  # Remove incomplete files
        else:
            self.logger.info('Transcode complete, saving to cache')
            self.add_cached_file(media_id, cache_file_name)
        if ffmpeg_proc.returncode != 0 and not terminated:
            with open(tmp_name, 'r') as tmp_in:
                self.logger.error(
                    "ffmpeg returned %i\n%s" % (ffmpeg_proc.returncode, tmp_in.read())
                )

    def add_cached_file(self, media_id, path, file_format=None):
        """Add an item to the transcode cache"""
        if file_format is None:
            file_format = os.path.splitext(path)[1][1:]
        item_cache = self.transcode_cache.setdefault(media_id, {})
        item_cache[file_format] = path

    def get_cached_file(self, media_id, file_format):
        """Gets the file name of the cached transcode file or
        returns None if no file exists.
        """
        if media_id in self.transcode_cache:
            return self.transcode_cache[media_id].get(file_format)
        return None

    def _start_ffmpeg(self, path, tmp, out_file, codec, container):
        """Starts ffmpeg"""
        self.logger.info("Starting transcode for %s" % path)
        if out_file != '-':
            stdout = open(os.devnull, 'w')
        else:
            stdout = subprocess.PIPE
        if os.path.exists(out_file):
            os.unlink(out_file)
        cmd = ['ffmpeg', '-i', path, '-acodec', codec]
        if container is not 'wav':
            cmd.extend(['-aq', self.AUDIO_QUALITY])
        cmd.extend(['-map', 'a', '-f', container, out_file])
        return subprocess.Popen(cmd, bufsize=self.BUF_SIZE, stdout=stdout, stderr=tmp)

    def get_media_info(self, path):
        """Gets the media metadata using ffmpeg"""
        cmd = ['ffprobe', '-i', path]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            self.logger.error("ffprobe returned %i\n%s" % (proc.returncode, stderr))
            return None
        return self._parse_metadata(stderr)  # FFProbe outputs stderr normally

    def _parse_metadata(self, data):
        """Parse the output of ffprobe and return a dict of
        file metadata.
        """
        info = {}
        active_re = self.metadata_start_re
        for line in data.splitlines():
            match = active_re.match(line)
            if match:
                if active_re is self.metadata_start_re:
                    active_re = self.metadata_re
                    continue
                info[match.group(1).lower()] = match.group(2)
            else:
                if active_re is self.metadata_re:
                    active_re = self.duration_re
                elif active_re is self.duration_re:
                    break
        return info

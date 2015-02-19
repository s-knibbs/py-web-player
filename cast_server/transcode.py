import subprocess
import re
import logging
import tempfile
from config import ComponentBase


class Transcoder(ComponentBase):

    AUDIO_CODEC = 'libvorbis'
    AUDIO_CONTAINER = 'ogg'
    AUDIO_QUALITY = '4'
    BUF_SIZE = 4096

    def __init__(self):
        super(Transcoder, self).__init__()
        self._load_config()
        # Regex's for parsing file metadata from ffmpeg / ffprobe
        self.metadata_re = re.compile(r'\s+([a-zA-Z]+)\s+: (.+)')
        self.metadata_start_re = re.compile(r'\s+Metadata:')
        self.duration_re = re.compile(r'\s+(Duration): ([0-9:]+)')

    def start_transcode(self, path):
        """Transcode the audio to ogg vorbis only for
        now. Uses ffmpeg to perform the transcode.
        Returns a generator for reading the buffered data.
        """
        # TODO - Add support for a transcode cache
        terminated = False
        # Send stderr to a temporary file for later reading
        with tempfile.NamedTemporaryFile() as tmp:
            proc = self._start_ffmpeg(path, tmp)
            while proc.returncode is None:
                try:
                    yield proc.stdout.read(BUF_SIZE)
                    proc.poll()  # Check return status
                except IOError as e:  # Handle client closing the connection
                    proc.terminate()
                    terminated = True  # Return will be non-zero if we terminated
                    logger.warning(str(e))
            if proc.returncode != 0 and not terminated:
                with open(tmp.name, 'r') as tmp_in:
                    self.logger.error("ffmpeg returned %i\n%s" % (proc.returncode, tmp_in.read()))
        raise StopIteration

    def _start_ffmpeg(self, path, tmp):
        # Contruct the command
        self.logger.info("Starting transcode for %s" % path) 
        cmd = ['ffmpeg', '-i', path, '-acodec', self.AUDIO_CODEC,
               '-aq', self.AUDIO_QUALITY, '-map', 'a', '-f', self.AUDIO_CONTAINER, '-']
        return subprocess.Popen(cmd, bufsize=BUF_SIZE, stdout=subprocess.PIPE, stderr=tmp)

    def get_media_info(self, path):
      """Gets the media metadata using ffmpeg"""
      cmd = ['ffprobe', '-i', path]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _, stderr = proc.communicate()
      if proc.returncode != 0:
        self.logger.error("ffprobe returned %i\n%s" % (proc.returncode, stderr))
        return None
      return _parse_metadata(stderr)  # FFProbe outputs stderr normally

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

import os
import bottle
import logging
from bottle import response, request, view, HTTPError

from model import MediaLibrary
from transcode import Transcoder
from config import config
import templates

# Setup templates directory
bottle.TEMPLATE_PATH.append(os.path.dirname(templates.__file__))

app = bottle.app()
_transcoder = Transcoder()

_logger = logging.getLogger(__name__)


def _format_time(secs):
    """Format the time according to [hrs:]mins:secs
    """
    hours, secs = divmod(secs, 3600)
    mins, secs = divmod(secs, 60)
    time_str = "%02i:%02i" % (mins, secs)
    if hours != 0:
        time_str = "%s:%s" % (hours, time_str)
    return time_str


@app.route('/')
@view('listing')
def list_all():
    """List all items in the library"""
    data = {'items': [], 'listing_title': 'All Media'}
    with MediaLibrary() as library:
        items = library.get_all()
        for item in items:
            data['items'].append((item.id, item.name, _format_time(item.length)))
    return data


@app.route('/stream/<media_id>')
def play_item(media_id):
    """Sends the file directly if possible or
    transcodes the file into a format the browser
    supports
    """
    item = _get_item(media_id)
    receive_type = _transcoder.get_output_type(
        item, request.get_header('accept', default='').split(',')
    )
    if not item.cached:
        # Wait for item to finish transcoding
        proc = _transcoder.start_transcode(item.path, item.id)
        proc.wait()
    _transcoder.check_background_processes()
    _set_stream_header(item, receive_type)
    if not item.cached:
        # TODO - Not currently reached
        default_range = 'bytes=0-'
        request_range = request.get_header('range', default='bytes=0-')
        if request_range != '' and not request_range.startswith(default_range):
            raise HTTPError(
                code=416, output="Cannot handle range request, transcode still in progress"
            )
        return _transcoder.start_transcode(item.path, item.id)
    else:
        return


@app.route('/transcode', method='POST')
def start_background_transcode():
    """Handle a request for a background transcode"""
    ids = request.forms.get('media_ids')
    if ids is not None:
        for media_id in ids.split(','):
            item = _get_item(media_id)
            _transcoder.get_output_type(
                item, request.get_header('accept').split(','), background=True
            )
            if not item.cached:
                _transcoder.start_transcode(item.path, item.id, background=True)


def _create_media_symlink(item):
    """Creates a symlink to the media item in the cache directory
    and returns the symlink path
    """
    ext = os.path.splitext(item.path)[1]
    sym_path = os.path.join(config.CACHE_DIR, str(item.id) + ext)
    os.symlink(item.path, sym_path)
    _transcoder.add_cached_file(item.id, ext[1:], sym_path)
    return sym_path


def _set_stream_header(item, receive_type):
    """Sets the headers for the media stream,
    sets the X-Sendfile header if possible
    """
    file_path = _transcoder.get_cached_file(item.id, receive_type.split('/')[1])
    if receive_type == item.mime_type and file_path is None:
        file_path = _create_media_symlink(item)
    if file_path is not None:
        _logger.info('Retrieving item from cache')
        item.cached = True
        # TODO - Use bottle static file with the development server
        response.set_header('X-Sendfile', file_path)
        response.set_header('Content-Type', receive_type)
        return
    response.set_header('Pragma', 'no-cache')
    response.set_header('Content-Type', receive_type)
    # Set the accept ranges header to allow range requests once transcoding is complete
    response.set_header('Accept-Ranges', 'bytes')
    response.set_header('X-Content-Duration', str(item.length))


def _get_item(media_id):
    """Gets the item associated with the given id"""
    with MediaLibrary() as library:
        item = library.get_item(media_id)
    if item is None:
        raise HTTPError(code=404, output="Item %s was not found" % media_id)
    return item


@app.route('/player/<media_id>')
@view('player')
def show_player(media_id):
    """Show the player for the given media id"""
    item = _get_item(media_id)
    return {'id': media_id, 'name': item.name}


if __name__ == "__main__":
    # Run test server
    # Stop bottle from catching all exceptions
    app.catchall = False
    app.run(host='localhost', port=8080)

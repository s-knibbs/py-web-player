import os
from pkg_resources import resource_string
import bottle
from bottle import route, run, template, error, view, static_file, response, request

from model import MediaLibrary
from transcode import Transcoder

# Setup templates directory
try:
  bottle.TEMPLATE_PATH.append(resource_string(__name__, 'templates'))
except:
  bottle.TEMPLATE_PATH.append(os.path.join(os.path.dirname(__file__), 'templates'))

app = bottle.app()
_transcoder = Transcoder()


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
@app.view('listing')
def list_all():
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
  # TODO - Look at the Accept header here and determine the best recieve type
  receive_type = 'audio/ogg'
  item = _get_item(media_id)
  _set_stream_header(item, receive_type)
  if request.method == 'HEAD':
    return
  if item.mime_type == receive_type:
    pass # Use static file here
  else: 
    return _transcoder.start_transcode(item.path)


def _set_stream_header(item, receive_type):
  if receive_type == item.mime_type:
    response.set_header('Content-Length', str(item.size))
  else:  # Length not known in advance when transcoding, so use chunked encoding.
    # Development server does not support chunked encoding, so use a large content-length instead
    if __name__ == "__main__":
      response.set_header('Content-Length', str(10**8))
    else:
      response.set_header('Transfer-Encoding', 'chunked')
  response.set_header('Content-Type', receive_type)
  response.set_header('X-Content-Duration', str(item.length))


def _get_item(media_id):
  with MediaLibrary() as library:
    item = library.get_item(media_id)
  if item is None:
    pass  # Throw 404 error here
  return item


@app.route('/player/<media_id>')
@app.view('player')
def show_player(media_id):
  item = _get_item(media_id)
  return {'id': media_id, 'name': item.name}


@app.error(404)
def item_not_found(error):
  pass


if __name__ == "__main__":
  # Run test server
  # Stop bottle from catching all exceptions
  app.catchall = False
  app.run(host='localhost', port=8080)

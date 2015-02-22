PyWebPlayer
===========

PyWebPlayer is a web service for serving audio files with HTML5. The service will scan a given
media directory and serve any audio files within using a web interface.
The server backend will transcode audio files to a supported format on-demand with ffmpeg.

The project is currently a work in progress and has only a limited interface.

Installation
------------

Install the pre-requisites::

  sudo apt-get install apache2 libapache2-mod-wsgi libapach2-mod-xsendfile ffmpeg

**Note:** It will be necessary to add the following `PPA <https://launchpad.net/~jon-severinsson/+archive/ubuntu/ffmpeg>`_ to install ffmpeg in Ubuntu 14.04.

Build the package and install with pip::

  python setup.py sdist
  sudo pip install dist/PyWebPlayer-0.1.tar.gz

Setup the server with::

  sudo pywebplayer-setup

This will prompt for a media directory to scan. Defaulting to `~/Music`

If setup was successful, navigating to http://localhost/ should display a list of all media found.

Acknowledgements
----------------

PyWebPlayer uses the following libraries:
 * `Bottle <http://bottlepy.org/>`_
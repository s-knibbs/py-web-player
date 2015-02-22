#!/usr/bin/python
from setuptools import setup, find_packages
from pywebplayer.config import config

setup(
    name=config.APP_NAME,
    version=config.VERSION,
    packages=find_packages(),
    package_data={'': ['*.tpl', '*.js', '*.png']},
    install_requires=['bottle>=0.12'],
    entry_points={
        'console_scripts': ['pywebplayer-setup=pywebplayer.configure:main']
    }
)

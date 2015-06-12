#!/usr/bin/env python
from setuptools import setup

kwargs = {'name': 'Greg',
          'version':  '0.4.4.3',
          'install_requires': ['feedparser'],
          'description': 'A command-line podcast aggregator',
          'author': 'Manolo Martínez',
          'author_email': 'manolo@austrohungaro.com',
          'url': 'https://github.com/manolomartinez/greg',
          'packages': ['greg'],
          'entry_points': {'console_scripts': ['greg = greg.gregparser:main']},
          'package_data': {'': ['data/greg.conf']},
          'license': 'GPLv3'}

setup(**kwargs)

#!/usr/bin/env python

kwargs = {'name':'Greg',
        'version':'0.4.3',
        'description':'A command-line podcast aggregator',
        'author':'Manolo Martínez',
        'author_email':'manolo@austrohungaro.com',
        'url':'https://github.com/manolomartinez/greg',
        'packages':['greg'],
        'scripts':['bin/greg'],
        'data_files':[('/etc',['data/greg.conf'])],
        'license' : 'GPLv3'}

try:
    from setuptools import setup
    kwargs['install_requires'] = ['feedparser']
    setup(**kwargs)
except ImportError:
    from distutils.core import setup
    setup(**kwargs)

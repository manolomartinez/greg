#!/usr/bin/env python

from distutils.core import setup

setup(  name='Greg',
        version='0.1.0',
        description='A command-line podcast aggregator',
        author='Manolo Martínez',
        author_email='manolo@austrohungaro.com',
        url='https://github.com/manolomartinez/greg',
        packages=['greg'],
        scripts=['bin/greg'],
        data_files=[('/etc',['data/greg.conf'])]
        license = 'GPLv3'
        )

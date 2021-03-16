#!/usr/bin/env python
from setuptools import setup

setup(
    name='Greg',
    version='0.4.7',
    install_requires=['feedparser'],
    extras_require={
        'tagging': ['beautifulsoup4', 'stagger', 'lxml'],
    },
    description='A command-line podcast aggregator',
    author='Manolo Martínez',
    author_email='manolo@austrohungaro.com',
    url='https://github.com/manolomartinez/greg',
    packages=['greg'],
    entry_points={'console_scripts': ['greg = greg.parser:main']},
    package_data={'greg': ['data/*.conf']},
    license='GPLv3'
)

# Copyright (C) 2012, 2013  Manolo Martínez <manolo@austrohungaro.com>
#
# This file is part or Greg.
#
# Greg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Greg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Greg.  If not, see <http://www.gnu.org/licenses/>.
"""
Defines auxiliary functions to be used elsewhere
"""

import configparser
import os
import subprocess
import sys
import re
import time
import unicodedata
import string
from urllib.request import urlretrieve
from urllib.error import URLError

from pkg_resources import resource_filename
import feedparser

try:  # Stagger is an optional dependency
    import stagger
    from stagger.id3 import *
    staggerexists = True
except ImportError:
    staggerexists = False

try:  # beautifulsoup4 is an optional dependency
    from bs4 import BeautifulSoup
    beautifulsoupexists = True
except ImportError:
    beautifulsoupexists = False

config_filename_global = resource_filename(__name__, 'data/greg.conf')

# Registering a custom date handler for feedparser

_feedburner_date_pattern = re.compile(
    r'\w+, (\w+) (\d{,2}), (\d{4}) - (\d{,2}):(\d{2})')


def feedburner_date_handler(aDateString):
    months = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5,
              "June": 6, "July": 7, "August": 8, "September": 9, "October": 10,
              "November": 11, "December": 12}
    # Parse a date sucn as "Sunday, November 25, 2012 - 12:00"
    try:
        # feedparser is supposed to catch the exception on its own,
        # but it doesn't
        month, day, year, hour, minute = _feedburner_date_pattern.search(
            aDateString).groups()
        return (
            int(year), int(months[month]), int(
                day), int(hour), int(minute), 0, 0, 0, 0)
    except AttributeError:
        return None

feedparser.registerDateHandler(feedburner_date_handler)

# The following are some auxiliary functions


def sanitize(data):
    # sanestring = ''.join([x if x.isalnum() else "_" for x in string])
    sanestring = ''.join(x if x.isalnum() else "_" for x in
                         unicodedata.normalize('NFKD', data)
                         if x in string.printable)
    return sanestring


def ensure_dir(dirname):
    try:
        os.makedirs(dirname)
    except OSError:
        if not os.path.isdir(dirname):
            raise


def parse_podcast(url):
    """
    Try to parse podcast
    """
    try:
        podcast = feedparser.parse(url)
        wentwrong = "urlopen" in str(podcast["bozo_exception"])
    except KeyError:
        wentwrong = False
    if wentwrong:
        print("Error: ", url, ": ", str(podcast["bozo_exception"]))
    return podcast


def html_to_text(data):
    if beautifulsoupexists:
        beautify = BeautifulSoup(data, "lxml")
        sanitizeddata = beautify.get_text()
    else:
        sanitizeddata = data
    return sanitizeddata


def check_directory(placeholders):
    """
    Find out, and create if needed,
    the directory in which the feed will be downloaded
    """
    feed = placeholders.feed
    args = feed.args
    placeholders.directory = "This very directory"  # wink, wink
    placeholders.fullpath = os.path.join(
        placeholders.directory, placeholders.filename)
    try:
        if args["downloaddirectory"]:
            ensure_dir(args["downloaddirectory"])
            placeholders.directory = args["downloaddirectory"]
    except KeyError:
        pass
    download_path = os.path.expanduser(
        feed.retrieve_config("Download Directory", "~/Podcasts"))
    subdirectory = feed.retrieve_config(
        "Create subdirectory", "no")
    if "no" in subdirectory:
        placeholders.directory = download_path
    elif "yes" in subdirectory:
        subdnametemplate = feed.retrieve_config(
            "subdirectory_name", "{podcasttitle}")
        subdname = substitute_placeholders(
            subdnametemplate, placeholders)
        placeholders.directory = os.path.join(download_path, subdname)
    ensure_dir(placeholders.directory)
    placeholders.fullpath = os.path.join(
        placeholders.directory, placeholders.filename)
    return placeholders


def parse_for_download(args):
    """
    Turn an argument such as 4, 6-8, 10 into a list such as [4,6,7,8,10]
    """
    single_arg = ""
    # in the first bit we put all arguments
    # together and take out any extra spaces
    list_of_feeds = []
    for arg in args["number"]:
        single_arg = ''.join([single_arg, " ", arg])
    single_arg = single_arg.translate({32: None})  # eliminates spaces
    for group in single_arg.split(sep=","):
        if not("-" in group):
            list_of_feeds.append(group)
        else:
            extremes = group.split(sep="-")
            list_of_feeds = list_of_feeds + [str(x) for x in range(
                eval(extremes[0]), eval(extremes[1])+1)]
    return list_of_feeds


def tag(placeholders):
    """
    Tag the file at podpath with the information in podcast and entry
    """
    # We first recover the name of the file to be tagged...
    template = placeholders.feed.retrieve_config("file_to_tag", "{filename}")
    filename = substitute_placeholders(template, placeholders)
    podpath = os.path.join(placeholders.directory, filename)
    # ... and this is it

    # now we create a dictionary of tags and values
    tagdict = placeholders.feed.defaulttagdict  # these are the defaults
    try:  # We do as if there was a section with potential tag info
        feedoptions = placeholders.feed.config.options(placeholders.name)
        # this monstruous concatenation of classes... surely a bad idea.
        tags = [[option.replace("tag_", ""), placeholders.feed.config[
            placeholders.name][option]] for option in feedoptions if "tag_" in
                option]  # these are the tags to be filled
        if tags:
            for tag in tags:
                tagdict[tag[0]] = tag[1]
    except configparser.NoSectionError:
        pass
    for tag in tagdict:
        metadata = substitute_placeholders(
            tagdict[tag], placeholders)
        if metadata:
            stagger.util.set_frames(podpath, {tag: metadata})
        else:
            stagger.util.remove_frames(podpath, tag)


def filtercond(placeholders):
    template = placeholders.feed.retrieve_config("filter", "True")
    condition = substitute_placeholders(template, placeholders)
    return eval(condition)


def get_date(line):
    date = eval(line.split(sep=' ', maxsplit=1)[1])
    return date


def download_handler(feed, placeholders):
    import shlex
    """
    Parse and execute the download handler
    """
    value = feed.retrieve_config('downloadhandler', 'greg')
    if value == 'greg':
        while os.path.isfile(placeholders.fullpath):
            placeholders.fullpath = placeholders.fullpath + '_'
        urlretrieve(placeholders.link, placeholders.fullpath)
    else:
        value_list = shlex.split(value)
        instruction_list = [substitute_placeholders(part, placeholders) for
                            part in value_list]
        returncode = subprocess.call(instruction_list)
        if returncode:
            raise URLError


def parse_feed_info(infofile):
    """
    Take a feed file in .local/share/greg/data and return a list of links and
    of dates
    """
    entrylinks = []
    linkdates = []
    try:
        with open(infofile, 'r') as previous:
            for line in previous:
                entrylinks.append(line.split(sep=' ')[0])
                # This is the list of already downloaded entry links
                linkdates.append(eval(line.split(sep=' ', maxsplit=1)[1]))
                # This is the list of already downloaded entry dates
                # Note that entrydates are lists, converted from a
                # time.struct_time() object
    except FileNotFoundError:
        pass
    return entrylinks, linkdates


def pretty_print(session, feed):
    """
    Print the dictionary entry of a feed in a nice way.
    """
    if feed in session.feeds:
        print()
        feed_info = os.path.join(session.data_dir, feed)
        entrylinks, linkdates = parse_feed_info(feed_info)
        print(feed)
        print("-"*len(feed))
        print(''.join(["    url: ", session.feeds[feed]["url"]]))
        if linkdates != []:
            print(''.join(["    Next sync will download from: ", time.strftime(
                "%d %b %Y %H:%M:%S", tuple(max(linkdates))), "."]))
    else:
        print("You don't have a feed called {}.".format(feed), file=sys.stderr,
              flush=True)


def substitute_placeholders(inputstring, placeholders):
    """
    Take a string with placeholders, and return the strings with substitutions.
    """
    newst = inputstring.format(link=placeholders.link,
                               filename=placeholders.filename,
                               directory=placeholders.directory,
                               fullpath=placeholders.fullpath,
                               title=placeholders.title,
                               filename_title=placeholders.filename_title,
                               date=placeholders.date_string(),
                               podcasttitle=placeholders.podcasttitle,
                               filename_podcasttitle=
                               placeholders.filename_podcasttitle,
                               name=placeholders.name,
                               subtitle=placeholders.sanitizedsubtitle,
                               entrysummary=placeholders.entrysummary)
    return newst

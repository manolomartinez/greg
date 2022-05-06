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
import json

from pkg_resources import resource_filename
import feedparser
import requests

try:  # EyeD3 is an optional dependency
    import eyed3
    eyed3exists = True
except ImportError:
    eyed3exists = False

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
                         unicodedata.normalize('NFKD', data))
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
        subdname = placeholders.substitute(subdnametemplate)
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
    filename = placeholders.substitute(template)
    podpath = os.path.join(placeholders.directory, filename)
    # ... and this is it
    # We also retrieve the path of a cover image, if there is one
    coverart = placeholders.feed.retrieve_config("coverart", False)
    if coverart:
        import mimetypes
        coverart_filename = substitute_placeholders(coverart, placeholders)
        if not os.path.exists(coverart_filename):
            print("""The file that I was supposed to use as cover art does not
                    exist.""", file=sys.stderr, flush=True)
            coverart = False
        else:
            coverart_mime = mimetypes.guess_type(coverart_filename)[0]
            if not coverart_mime:
                print("""I couldn't guess the mimetype of this file, please use a
                        more perspicuous extension""", file=sys.stderr, flush=True)
                coverart = False
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
        metadata = placeholders.substitute(tagdict[tag])
        tagdict[tag] = metadata
    file_to_tag = eyed3.load(podpath)
    if file_to_tag.tag == None:
        file_to_tag.initTag()
    for mytag in tagdict:
        try:
            attribute = getattr(file_to_tag.tag, mytag)
            if isinstance(attribute, eyed3.id3.tag.DltAccessor):
                attribute.set(tagdict[mytag])
            else:
                setattr(file_to_tag.tag, mytag, tagdict[mytag])
        except AttributeError:
            setattr(file_to_tag.tag, mytag, tagdict[mytag])
    if coverart:
        with open(coverart_filename, 'rb') as imagefile:
            image = imagefile.read()
        file_to_tag.tag.images.set(
                type_=3, img_data=image, mime_type=coverart_mime)
    file_to_tag.tag.save()


def filtercond(placeholders):
    template = placeholders.feed.retrieve_config("filter", "True")
    condition = placeholders.substitute(template)
    return eval(condition)


def get_date(line):
    try:
        history = json.loads(line)
        if 'entrylink' in history and 'linkdate' in history:
            return history['linkdate']
        else:
            print("Error reading history entry for {}. Contents:"
                   "{}".format(infofile, history), file=sys.stderr,
                   flush=True)
            return False
    except json.JSONDecodeError:
        # Ignore JSONDecodeErrors as we'll fall through to our old method
        pass
    date = eval(line.split(sep=' ', maxsplit=1)[1])
    return date


def download_handler(feed, placeholders):
    import shlex
    """
    Parse and execute the download handler
    """
    value = feed.retrieve_config('downloadhandler', 'greg')
    if value == 'greg':
        with requests.get(placeholders.link) as fin:
            # check if request went ok
            fin.raise_for_status()
            # check if fullpath allready exists
            while os.path.isfile(placeholders.fullpath):
                placeholders.filename = placeholders.filename + '_'
                placeholders.fullpath = os.path.join(
                    placeholders.directory, placeholders.filename)
            # write content to file
            with open(placeholders.fullpath,'wb') as fout:
                fout.write(fin.content)
    else:
        value_list = shlex.split(value)
        instruction_list = [placeholders.substitute(part) for
                            part in value_list]
        returncode = subprocess.call(instruction_list)
        if returncode:
            print("There was a problem with your download handler:"
                    "{}".format(returncode), file=sys.stderr, flush=True)



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
                # Try importing as new json format
                try:
                    history = json.loads(line)
                    if 'entrylink' in history and 'linkdate' in history:
                        entrylinks.append(history['entrylink'])
                        # This is the list of already downloaded entry links
                        linkdates.append(history['linkdate'])
                        # This is the list of already downloaded entry dates
                        # Note that entrydates are lists, converted from a
                        # time.struct_time() object
                    else:
                        print("Error reading history entry for {}. Contents:"
                              "{}".format(infofile, history), file=sys.stderr,
                              flush=True) 
                    continue
                except json.JSONDecodeError:
                    # Ignore JSONDecodeErrors as we'll fall through to our old method
                    pass
                try:
                    # Fallback to old buggy format
                    entrylinks.append(line.split(sep=' ')[0])
                    # This is the list of already downloaded entry links
                    linkdates.append(eval(line.split(sep=' ', maxsplit=1)[1]))
                    # This is the list of already downloaded entry dates
                    # Note that entrydates are lists, converted from a
                    # time.struct_time() object
                except SyntaxError:
                    # this means the eval above failed. We just ignore it
                    print("Invalid history line. Possibly broken old format. Ignoring line, but this may cause an episode "
                          "to download again", file=sys.stderr, flush=True)
                    print(line)

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

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

import configparser
import os
import pickle
import subprocess
import sys
import time
import re
import unicodedata
import string
from itertools import filterfalse
from urllib.request import urlretrieve
from urllib.parse import urlparse
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


def FeedburnerDateHandler(aDateString):
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

feedparser.registerDateHandler(FeedburnerDateHandler)

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
        sys.exit(("I cannot check podcasts now."
                 "Are you connected to the internet?"))
    return podcast


def htmltotext(data):
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
        stagger.util.set_frames(podpath, {tag: metadata})


def filtercond(placeholders):
    template = placeholders.feed.retrieve_config("filter", "True")
    condition = substitute_placeholders(template, placeholders)
    return eval(condition)


def get_date(line):
    date = eval(line.split(sep=' ', maxsplit=1)[1])
    return date


def transition(args, feed, feeds):
    # A function to ease the transition to individual feed files
    if "downloadfrom" in feeds[feed]:
        edit({"downloadfrom": eval(feeds[feed]["downloadfrom"]), "name": feed})
        # edit() is usually called from the outside
        DATA_DIR = retrieve_data_directory(args)
        DATA_FILENAME = os.path.join(DATA_DIR, "data")
        feeds.remove_option(feed, "downloadfrom")
        with open(DATA_FILENAME, 'w') as configfile:
            feeds.write(configfile)


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

# The following are the functions that correspond to the different commands


def retrieveglobalconf(args):
    """
    Retrieve the global config path
    """
    print(config_filename_global)


def add(args):  # Adds a new feed
    session = Session(args)
    if args["name"] in session.feeds.sections():
        sys.exit("You already have a feed with that name.")
    if args["name"] in ["all", "DEFAULT"]:
        sys.exit(
            ("greg uses ""{}"" for a special purpose."
            "Please choose another name for your feed.").format(args["name"]))
    entry = {}
    for key, value in args.items():
        if value is not None and key != "func" and key != "name":
            entry[key] = value
    session.feeds[args["name"]] = entry
    with open(session.data_filename, 'w') as configfile:
        session.feeds.write(configfile)


def edit(args):  # Edits the information associated with a certain feed
    session = Session(args)
    feed_info = os.path.join(session.data_dir, args["name"])
    if not(args["name"] in session.feeds):
        sys.exit("You don't have a feed with that name.")
    for key, value in args.items():
        if value is not None and key == "url":
            session.feeds[args["name"]][key] = str(value)
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
        if value is not None and key == "downloadfrom":
            try:
                dateinfo = (session.feeds[
                    args["name"]]["date_info"] == "not available")
            except KeyError:
                session.feeds[args["name"]]["date_info"] = "available"
                # provisionally!
                with open(session.data_filename, 'w') as configfile:
                    session.feeds.write(configfile)
                dateinfo = False  # provisionally
            if dateinfo:
                print(("{} has no date information that I can use."
                       "Using --downloadfrom might not have the"
                       "results that you expect.").
                      format(args["name"]), file=sys.stderr, flush=True)
            line = ' '.join(["currentdate", str(value), "\n"])
            # A dummy entry with the new downloadfrom date.
            try:
                # Remove from the feed file all entries
                # after or equal to downloadfrom, then append line
                with open(feed_info, 'r') as previous:
                    previouslist = previous.readlines()
                    current = [aline for aline in previouslist if value >
                               get_date(aline)]
                    current.append(line)
                with open(feed_info, 'w') as currentfile:
                    currentfile.writelines(current)
            except FileNotFoundError:
                # Write the file with a dummy entry with the right date
                with open(feed_info, 'w') as currentfile:
                    currentfile.write(line)


def remove(args):
    """
    Remove the feed given in <args>
    """
    session = Session(args)
    if not args["name"] in session.feeds:
        sys.exit("You don't have a feed with that name.")
    inputtext = ("Are you sure you want to remove the {} "
                 " feed? (y/N) ").format(args["name"])
    reply = input(inputtext)
    if reply != "y" and reply != "Y":
        return 0
    else:
        session.feeds.remove_section(args["name"])
        with open(session.data_filename, 'w') as configfile:
            session.feeds.write(configfile)
        try:
            os.remove(os.path.join(session.data_dir, args["name"]))
        except FileNotFoundError:
            pass


def info(args):  # Provides information of a number of feeds
    session = Session(args)
    if "all" in args["names"]:
        feeds = session.list_feeds()
    else:
        feeds = args["names"]
    for feed in feeds:
        pretty_print(session, feed)


def pretty_print(session, feed):
    # Prints the dictionary entry of a feed in a nice way.
    print()
    feed_info = os.path.join(session.data_dir, feed)
    entrylinks, linkdates = parse_feed_info(feed_info)
    print(feed)
    print("-"*len(feed))
    print(''.join(["    url: ", session.feeds[feed]["url"]]))
    if linkdates != []:
        print(''.join(["    Next sync will download from: ", time.strftime(
            "%d %b %Y %H:%M:%S", tuple(max(linkdates))), "."]))


def list_for_user(args):
    session = Session(args)
    for feed in session.list_feeds():
        print(feed)
    print()


def sync(args):
    """
    Implement the 'greg sync' command
    """
    import operator
    session = Session(args)
    if "all" in args["names"]:
        targetfeeds = session.list_feeds()
    else:
        targetfeeds = []
        for name in args["names"]:
            if name not in session.feeds:
                print("You don't have a feed called {}."
                      .format(name), file=sys.stderr, flush=True)
            else:
                targetfeeds.append(name)
    for target in targetfeeds:
        feed = Feed(session, target, None)
        if not feed.wentwrong:
            try:
                title = feed.podcast.target.title
            except AttributeError:
                title = target
            print("Checking", title, end="...\n")
            currentdate, stop = feed.how_many()
            entrycounter = 0
            entries_to_download = feed.podcast.entries
            for entry in entries_to_download:
                feed.fix_linkdate(entry)
            # Sort entries_to_download, but only if you want to download as
            # many as there are
            if stop >= len(entries_to_download):
                entries_to_download.sort(key=operator.attrgetter("linkdate"),
                                         reverse=False)
            for entry in entries_to_download:
                if entry.linkdate > currentdate:
                    downloaded = feed.download_entry(entry)
                    entrycounter += downloaded
                if entrycounter >= stop:
                    break
            print("Done")
        else:
            msg = ''.join(["I cannot sync ", feed,
                           " just now. Are you connected to the internet?"])
            print(msg, file=sys.stderr, flush=True)


def check(args):
    """
    Implement the 'greg check' command
    """
    session = Session(args)
    if str(args["url"]) != 'None':
        url = args["url"]
        name = "DEFAULT"
    else:
        try:
            url = session.feeds[args["feed"]]["url"]
            name = args["feed"]
        except KeyError:
            sys.exit("You don't appear to have a feed with that name.")
    podcast = parse_podcast(url)
    for entry in enumerate(podcast.entries):
        listentry = list(entry)
        print(listentry[0], end=": ")
        try:
            print(listentry[1]["title"], end=" (")
        except:
            print(listentry[1]["link"], end=" (")
        try:
            print(listentry[1]["updated"], end=")")
        except:
            print("", end=")")
        print()
    dumpfilename = os.path.join(session.data_dir, 'feeddump')
    with open(dumpfilename, mode='wb') as dumpfile:
        dump = [name, podcast]
        pickle.dump(dump, dumpfile)


def download(args):
    """
    Implement the 'greg download' command
    """
    session = Session(args)
    issues = parse_for_download(args)
    if issues == ['']:
        sys.exit(
            "You need to give a list of issues, of the form ""a, b-c, d...""")
    dumpfilename = os.path.join(session.data_dir, 'feeddump')
    if not os.path.isfile(dumpfilename):
        sys.exit(
            ("You need to run ""greg check"
             "<feed>"" before using ""greg download""."))
    with open(dumpfilename, mode='rb') as dumpfile:
        dump = pickle.load(dumpfile)
    try:
        feed = Feed(session, dump[0], dump[1])
    except Exception:
        sys.exit((
            "... something went wrong."
            "Are you sure your last ""greg check"" went well?"))
    for number in issues:
        entry = dump[1].entries[eval(number)]
        feed.info = []
        feed.entrylinks = []
        feed.fix_linkdate(entry)
        feed.download_entry(entry)

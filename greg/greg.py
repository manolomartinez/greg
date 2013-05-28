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
import shlex
import subprocess
import sys
import time
import re
from itertools import filterfalse
from urllib.request import urlretrieve
from urllib.parse import urlparse
from urllib.error import URLError

import feedparser

try:  # Stagger is an optional dependency
    import stagger
    from stagger.id3 import *
    staggerexists = True
except ImportError:
    staggerexists = False


config_filename_global = '/etc/greg.conf'


class Session():
    def __init__(self, args):
        self.args = args
        self.config_filename_user = self.retrieve_config_file()
        self.data_dir = self.retrieve_data_directory()
        self.data_filename = os.path.join(self.data_dir, "data")
        self.feeds = configparser.ConfigParser()
        self.feeds.read(self.data_filename)
        self.config = configparser.ConfigParser()
        self.config.read([config_filename_global, self.config_filename_user])

    def list_feeds(self):  # Outputs a list of all feed names
        feeds = configparser.ConfigParser()
        feeds.read(self.data_filename)
        return feeds.sections()

    def retrieve_config_file(self):
        try:
            if self.args["configfile"]:
                return self.args["configfile"]
        except KeyError:
            pass
        return os.path.expanduser('~/.config/greg/greg.conf')

    def retrieve_data_directory(self):  # Retrieves the data directory
        # (looks first into config_filename_global
        # then into config_filename_user. The latest takes preeminence)
        args = self.args
        try:
            if args['datadirectory']:
                ensure_dir(args['datadirectory'])
                return args['datadirectory']
        except KeyError:
            pass
        config = configparser.ConfigParser()
        config.read([config_filename_global, self.config_filename_user])
        section = config.default_section
        data_path = config.get(section, 'Data directory',
                               fallback='~/.local/share/greg')
        data_path_expanded = os.path.expanduser(data_path)
        ensure_dir(data_path_expanded)
        return os.path.expanduser(data_path_expanded)


class Feed():
    def __init__(self, session, feed, podcast):
        self.session = session
        self.args = session.args
        self.config = self.session.config
        self.name = feed
        if not podcast:
            self.podcast = feedparser.parse(session.feeds[feed]["url"])
        else:
            self.podcast = podcast
        self.sync_by_date = self.has_date()
        self.willtag = self.will_tag()
        if self.willtag:
            self.defaulttagdict = self.default_tag_dict()
        self.mime = self.retrieve_mime()
        try:
            self.wentwrong = "URLError" in str(self.podcast["bozo_exception"])
        except KeyError:
            self.wentwrong = False
        self.info = os.path.join(session.data_dir, feed)
        self.entrylinks, self.linkdates = parse_feed_info(self.info)

    def retrieve_config(self, value, default):
        # Retrieves a value (with a certain fallback) from the config files
        # (looks first into config_filename_global
        # then into config_filename_user. The latest takes preeminence)
        # if the command line flag for the value is use,
        # that overrides everything else
        args = self.args
        name = self.name
        try:
            if args[value]:
                return args[value]
        except KeyError:
            pass
        section = name if self.config.has_section(
            name) else self.config.default_section
        answer = self.config.get(section, value, fallback=default)
        return answer

    def default_tag_dict(self):
        defaultoptions = self.config.defaults()
        tags = [[option.replace(
            "tag_", ""), defaultoptions[option]] for option
            in defaultoptions if "tag_" in option]
            # these are the tags to be filled
        return dict(tags)

    def retrieve_download_path(self):
        # Retrieves the download path (looks first into config_filename_global
        # then into the [DEFAULT], then the [feed], section of
        # config_filename_user. The latest takes preeminence)
        section = self.name if self.config.has_section(
            self.name) else self.config.default_section
        download_path = config.get(
            section, 'Download directory', fallback='~/Podcasts')
        subdirectory = config.get(
            section, 'Create subdirectories', fallback='no')
        return [os.path.expanduser(download_path), subdirectory]

    def has_date(self):
        podcast = self.podcast
        session = self.session
        name = self.name
        try:  # If the feed has a date, and we can parse it, we use it.
            test = podcast.feed.published_parsed
            sync_by_date = True
        except AttributeError:
            try:
                test = podcast.feed.updated_parsed
                sync_by_date = True
            except AttributeError:  # Otherwise, we use download links.
                print(
                    "I cannot parse the time information of this feed.\
                    I'll use your current local time instead.",
                    file=sys.stderr, flush=True)
                sync_by_date = False
        if not sync_by_date:
            session.feeds[name]["date_info"] = "not available"
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
        else:
            session.feeds[name]["date_info"] = "available"
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
        return sync_by_date

    def will_tag(self):  # Checks whether the feed should be tagged
        wanttags = self.retrieve_config('Tag', 'no')
        if wanttags == 'yes':
            if staggerexists:
                willtag = True
            else:
                willtag = False
                print("You want me to tag {0}, but you have not installed the\
                      Stagger module. I cannot honour your request.".
                      format(feed), file=sys.stderr, flush=True)
        else:
            willtag = False
        return willtag

    def how_many(self):  # Where to start downloading, and how many.
        if self.linkdates != []:
            currentdate = max(self.linkdates)
            stop = 10 ^ 6
        else:
            currentdate = [1, 1, 1, 0, 0]
            firstsync = self.retrieve_config('firstsync', '1')
            if firstsync == 'all':
                stop = 10 ^ 6
                # I'm guessing no feed in the world
                # will have more than a million entries.
            else:
                stop = int(firstsync)
        return currentdate, stop

    def retrieve_mime(self):  # Checks the mime-type to download
        mime = self.retrieve_config('mime', 'audio')
        mimedict = {"number": mime}
        # the input that parse_for_download expects
        return parse_for_download(mimedict)


class Placeholders():
    def __init__(self, feed, link, filename, title):
        self.feed = feed
        self.link = link
        self.filename = filename
        #self.fullpath = os.path.join(self.directory, self.filename)
        self.title = title
        try:
            self.podcasttitle = feed.podcast.title
        except AttributeError:
            self.podcasttitle = feed.name
        self.name = feed.name
        self.date = tuple(feed.linkdate)

    def date_string(self):
        date_format = self.feed.retrieve_config("date_format", "%Y-%m-%d")
        return time.strftime(date_format, self.date)


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


def ensure_dir(dirname):
    try:
        os.makedirs(dirname)
    except OSError:
        if not os.path.isdir(dirname):
            raise


def check_directory(placeholders):
    # Find out, and create if needed,
    # the directory in which the feed will be downloaded
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
            subdnametemplate, placeholders, "normal")
        placeholders.directory = os.path.join(download_path, subdname)
    ensure_dir(placeholders.directory)
    placeholders.fullpath = os.path.join(
        placeholders.directory, placeholders.filename)
    return placeholders


def parse_for_download(args):
    # Turns an argument such as 4, 6-8, 10 into a list such as [4,6,7,8,10]
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
    # Tags the file at podpath with the information in podcast and entry
    # We first recover the name of the file to be tagged...
    template = placeholders.feed.retrieve_config("file_to_tag", "{filename}")
    filename = substitute_placeholders(template, placeholders, "normal")
    podpath = os.path.join(placeholders.directory, filename)
    # ... and this is it

    # now we create a dictionary of tags and values
    tagdict = placeholders.feed.defaulttagdict  # these are the defaults
    feedoptions = placeholders.feed.config.options(placeholders.name)
    # this monstruous concatenation of classes... surely a bad idea.
    tags = [[option.replace(
        "tag_", ""), placeholders.feed.config[
            placeholders.name][option]] for option
        in feedoptions if "tag_" in option]  # these are the tags to be filled
    if tags == []:
        tagdict = placeholders.feed.defaulttagdict  # these are the defaults
    # Now we combine this list with the default dictionary
    else:
        for tag in tags:
            tagdict[tag[0]] = tag[1]
    for tag in tagdict:
        metadata = substitute_placeholders(
            tagdict[tag], placeholders, "normal")
        stagger.util.set_frames(podpath, {tag: metadata})

def filtercond(placeholders):
    template = placeholders.feed.retrieve_config("filter", "True")
    condition = substitute_placeholders(template, placeholders, "normal")
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
    value = feed.retrieve_config('downloadhandler', 'greg')
    if value == 'greg':
        while os.path.isfile(placeholders.fullpath):
            placeholders.fullpath = placeholders.fullpath + '_'
        urlretrieve(placeholders.link, placeholders.fullpath)
    else:
        instruction = substitute_placeholders(value, placeholders, "safe")
        instructionlist = shlex.split(instruction)
        subprocess.call(instructionlist)


def download_entry(feed, entry):
    downloadlinks = {}
    for enclosure in entry.enclosures:
        # We will download all enclosures of the desired mime-type
        if any([mimetype in enclosure["type"] for mimetype in feed.mime]):
            downloadlinks[urlparse(
                enclosure["href"]).path.split("/")[-1]] = enclosure["href"]
            # preserve original name
    for podname in downloadlinks:
        if podname not in feed.entrylinks:
            try:
                title = entry.title
            except:
                title = podname
            try:
                placeholders = Placeholders(
                    feed, downloadlinks[podname], podname, title)
                placeholders = check_directory(placeholders)
                condition = filtercond(placeholders)
                if condition:
                    print("Downloading {} -- {}".format(title, podname))
                    download_handler(feed, placeholders)
                    if feed.willtag:
                        tag(placeholders)
                    if feed.info:
                        with open(feed.info, 'a') as current:
                            # We write to file this often to ensure that downloaded
                            # entries count as downloaded.
                            current.write(''.join([podname, ' ',
                                                   str(feed.linkdate), '\n']))
                else:
                    print("Skipping {} -- {}".format(title, podname))
            except URLError:
                sys.exit("... something went wrong.\
                         Are you sure you are connected to the internet?")


def parse_feed_info(info):
    entrylinks = []
    linkdates = []
    try:
        with open(info, 'r') as previous:
            for line in previous:
                entrylinks.append(line.split(sep=' ')[0])
                # This is the list of already downloaded entry links
                linkdates.append(eval(line.split(sep=' ', maxsplit=1)[1]))
                # This is the list of already downloaded entry dates
    except FileNotFoundError:
        pass
    return entrylinks, linkdates


def substitute_placeholders(string, placeholders, mode):
    if mode == "safe":
        newst = string.format(link=placeholders.link,
                              filename=placeholders.filename,
                              directory=placeholders.directory,
                              fullpath=placeholders.fullpath,
                              title=placeholders.title,
                              date=placeholders.date_string(),
                              podcasttitle=placeholders.podcasttitle,
                              name=placeholders.name)

    if mode == "normal":
        newst = string.format(link=shlex.quote(placeholders.link),
                              filename=shlex.quote(placeholders.filename),
                              directory=shlex.quote(placeholders.directory),
                              fullpath=shlex.quote(placeholders.fullpath),
                              title=shlex.quote(placeholders.title),
                              date=placeholders.date_string(),
                              podcasttitle=shlex.quote(
                                  placeholders.podcasttitle),
                              name=shlex.quote(placeholders.name))
    return newst

# The following are the functions that correspond to the different commands


def add(args):  # Adds a new feed
    session = Session(args)
    if args["name"] in session.feeds.sections():
        sys.exit("You already have a feed with that name.")
    if args["name"] in ["all", "DEFAULT"]:
        sys.exit(
            "greg uses ""{}"" for a special purpose.\
            Please choose another name for your feed.".format(args["name"]))
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
                print("{} has no date information that I can use.\
                      Using --downloadfrom might not have the\
                      results that you expect.".
                      format(args["name"]), file=sys.stderr, flush=True)
            line = ' '.join(["currentdate", str(value), "\n"])
            # A dummy entry with the right date, in case we need it.
            try:
                # Remove from the feed file all entries
                # after or equal to downloadfrom
                with open(feed_info, 'r') as previous:
                    current = list(filterfalse(
                        lambda line: value < get_date(line), previous))
                    if current == [] and dateinfo:
                        current = [line]
                with open(feed_info, 'w') as currentfile:
                    currentfile.writelines(current)
            except FileNotFoundError:
                # Write the file with a dummy entry with the right date
                with open(feed_info, 'w') as currentfile:
                    currentfile.write(line)


def remove(args):  # Removes a certain feed
    session = Session(args)
    if not(args["name"] in session.feeds):
        sys.exit("You don't have a feed with that name.")
    inputtext = "Are you sure you want to remove the {}\
            feed? (y/N) ".format(args["name"])
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
        print(feed, end=" ")
    print()


def sync(args):
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
            for entry in feed.podcast.entries:
                if feed.sync_by_date:
                    try:
                        feed.linkdate = list(entry.published_parsed)
                    except AttributeError:
                        feed.linkdate = list(entry.updated_parsed)
                else:
                    feed.linkdate = list(time.localtime())
                if feed.linkdate > currentdate and entrycounter < stop:
                    download_entry(feed, entry)
                entrycounter += 1
            print("Done")
        else:
            msg = ''.join(["I cannot sync ", feed,
                           " just now. Are you connected to the internet?"])
            print(msg, file=sys.stderr, flush=True)


def check(args):
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
    try:
        podcast = feedparser.parse(url)
        wentwrong = "urlopen" in str(podcast["bozo_exception"])
    except KeyError:
        wentwrong = False
    if wentwrong:
        sys.exit("I cannot check that podcast now.\
                 You are probably not connected to the internet.")
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
    session = Session(args)
    issues = parse_for_download(args)
    if issues == ['']:
        sys.exit(
            "You need to give a list of issues, of the form ""a, b-c, d...""")
    dumpfilename = os.path.join(session.data_dir, 'feeddump')
    if not(os.path.isfile(dumpfilename)):
        sys.exit(
            "You need to run ""greg check\
            <feed>"" before using ""greg download"".")
    with open(dumpfilename, mode='rb') as dumpfile:
        dump = pickle.load(dumpfile)
    try:
        feed = Feed(session, dump[0], dump[1])
    except Exception:
        sys.exit(
            "... something went wrong.\
            Are you sure your last check went well?")
    for number in issues:
        entry = dump[1].entries[eval(number)]
        feed.info = []
        feed.entrylinks = []
        feed.linkdate = list(time.localtime())
        download_entry(feed, entry)

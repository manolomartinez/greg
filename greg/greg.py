# Copyright (C) 2012  Manolo Martínez <manolo@austrohungaro.com>
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

import os, sys, configparser, pickle, time, re
from itertools import islice, filterfalse
from urllib.request import urlretrieve
from urllib.parse import urlparse 
from urllib.error import URLError

import feedparser

try: # Stagger is an optional dependency
    import stagger
    from stagger.id3 import *
    staggerexists = True
except ImportError:
    staggerexists = False

CONFIG_FILENAME_GLOBAL = '/etc/greg.conf'
CONFIG_FILENAME_USER = os.path.expanduser('~/.config/greg/greg.conf')

# Registering a custom date handler for feedparser

_feedburner_date_pattern = re.compile(
    r'\w+, (\w+) (\d{,2}), (\d{4}) - (\d{,2}):(\d{2})')
 
def FeedburnerDateHandler(aDateString):
    months = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
    # Parse a date sucn as "Sunday, November 25, 2012 - 12:00"
    try: # feedparser is supposed to catch the exception on its own, but it doesn't
        month, day, year, hour, minute = _feedburner_date_pattern.search(aDateString).groups()
        return (int(year), int(months[month]), int(day), int(hour), int(minute), 0, 0, 0, 0)
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

def parse_for_download(args):  # Turns an argument such as 4, 6-8, 10 into a list such as [4,6,7,8,10]
    single_arg="" # in the first bit we put all arguments together and take out any extra spaces
    list_of_feeds=[]
    for arg in args["number"]:
        single_arg = ''.join([single_arg , " " , arg])
    single_arg = single_arg.translate({32:None}) # eliminates spaces
    for group in single_arg.split(sep=","):
        if not("-" in group):
            list_of_feeds.append(group)
        else:
            extremes = group.split(sep="-")
            list_of_feeds = list_of_feeds + [str(x) for x in range (eval(extremes[0]),eval(extremes[1])+1)]
    return list_of_feeds

def retrieve_config(feed, value, default): # Retrieves a value (with a certain fallback) from the config files
    # (looks first into CONFIG_FILENAME_GLOBAL
    # then into CONFIG_FILENAME_USER. The latest takes preeminence)
    config = configparser.ConfigParser()
    config.read([CONFIG_FILENAME_GLOBAL, CONFIG_FILENAME_USER])
    section = feed if config.has_section(feed) else config.default_section
    answer = config.get(section,value, fallback=default)
    return answer

def retrieve_data_directory(): # Retrieves the data directory (looks first into CONFIG_FILENAME_GLOBAL
    # then into CONFIG_FILENAME_USER. The latest takes preeminence)
    config = configparser.ConfigParser()
    config.read([CONFIG_FILENAME_GLOBAL, CONFIG_FILENAME_USER])
    section = config.default_section
    data_path = config.get(section, 'Data directory', fallback='~/.local/share/greg')
    data_path_expanded = os.path.expanduser(data_path)
    ensure_dir(data_path_expanded)
    return os.path.expanduser(data_path_expanded)   
        
def retrieve_download_path(feed): # Retrieves the download path (looks first into CONFIG_FILENAME_GLOBAL
    # then into the [DEFAULT], then the [feed], section of CONFIG_FILENAME_USER. The latest takes preeminence)
    config = configparser.ConfigParser()
    config.read([CONFIG_FILENAME_GLOBAL, CONFIG_FILENAME_USER])
    section = feed if config.has_section(feed) else config.default_section
    download_path = config.get(section, 'Download directory', fallback='~/Podcasts')
    subdirectory = config.get(section, 'Create subdirectories', fallback='no')
    return [os.path.expanduser(download_path), subdirectory]   

def will_tag(feed): # Checks whether the feed should be tagged (looks first into CONFIG_FILENAME_GLOBAL
    # then into the [DEFAULT], then the [feed], section of CONFIG_FILENAME_USER. The latest takes preeminence)
    wanttags = retrieve_config(feed, 'Tag', 'no')
    if wanttags == 'yes':
        if staggerexists:
            willtag = True
        else:
            willtag = False
            print("You want me to tag {0}, but you have not installed the Stagger module. I cannot honour your request.".format(feed), file = sys.stderr, flush=True)
    else:
        willtag = False
    return willtag

def retrieve_mime(feed): # Checks the mime-type to download
    mime = retrieve_config(feed, 'mime', 'audio')
    mimedict = {"number":mime} # the input that parse_for_download expects
    return parse_for_download(mimedict)

def tag(feed, entry, podcast, podpath): # Tags the file at podpath with the information in podcast and entry
    try:
        stagger.util.set_frames(podpath, {"artist":podcast.feed.title})
    except:
        stagger.util.set_frames(podpath, {"artist":feed})
    try:
        stagger.util.set_frames(podpath, {"title":entry.title})
    except:
        stagger.util.set_frames(podpath, {"title":entry.link})
    stagger.util.set_frames(podpath, {"genre":"Podcast"})

def check_directory(feed, podcast): # Find out, and create if needed, the directory in which the feed will be downloaded
    DOWNLOAD_PATH = retrieve_download_path(feed)[0]
    subdirectory = retrieve_download_path(feed)[1]
    if subdirectory == "title":
        try:
            directory = os.path.join(DOWNLOAD_PATH, podcast.feed.title)
        except:
            print("You want me to use the feed title to name the directory in which this podcast is saved, but this feed apparently has no title. I will use the name you gave me for it.", file = sys.stderr, flush = True)
            directory = os.path.join(DOWNLOAD_PATH, feed)
    elif subdirectory == "name":
        directory = os.path.join(DOWNLOAD_PATH, feed)
    else:
        directory = DOWNLOAD_PATH
    ensure_dir(directory)
    return directory

def get_date(line):
    date = eval(line.split(sep=' ', maxsplit = 1)[1])
    return date

def has_date(podcast):
    try: # If the feed has a date, and we can parse it, we use it.
        test = podcast.feed.published_parsed
        sync_by_date = True
    except AttributeError: 
        try:
            test = podcast.feed.updated_parsed
            sync_by_date = True
        except AttributeError: # Otherwise, we use download links.
            print("I cannot parse the time information of this feed. I'll use your current local time instead.", file = sys.stderr, flush = True)
            sync_by_date = False
    return sync_by_date

def transition(feed, feeds): # A function to ease the transition to individual feed files
    if "downloadfrom" in feeds[feed]:
        edit({"downloadfrom":eval(feeds[feed]["downloadfrom"]), "name":feed}) # edit() is usually called from the outside
        DATA_DIR = retrieve_data_directory()
        DATA_FILENAME =  os.path.join(DATA_DIR, "data")
        feeds.remove_option(feed, "downloadfrom")
        with open(DATA_FILENAME, 'w') as configfile:
            feeds.write(configfile)

def parse_feed_info(FEED_INFO):
    entrylinks = []
    linkdates = []
    try:
        with open(FEED_INFO, 'r') as previous:
            for line in previous:
                entrylinks.append(line.split(sep=' ')[0]) # This is the list of already downloaded entry links
                linkdates.append(eval(line.split(sep=' ', maxsplit = 1)[1])) # This is the list of already downloaded entry dates
    except FileNotFoundError:
        pass
    return entrylinks, linkdates

def download_handler(feed, link, filename, directory, fullpath):
    value = retrieve_config(feed, 'downloadhandler', 'greg')
    if value == 'greg':
        while os.path.isfile(fullpath):
            fullpath = fullpath + '_'
        urlretrieve(link, fullpath)
    else:
        instruction = value.format(link = link, filename = filename, directory = directory, fullpath = fullpath)
        os.system(instruction)


# The following are the functions that correspond to the different commands

def add(args): # Adds a new feed
    DATA_FILENAME =  os.path.join(retrieve_data_directory(), "data")
    config = configparser.ConfigParser()
    config.read(DATA_FILENAME)
    if args["name"] in config.sections():
        sys.exit("You already have a feed with that name.")
    if args["name"] in ["all"]:
        sys.exit("greg uses ""{}"" for a special purpose. Choose another name for your feed.".format(args["name"]))
    entry = {}
    for key,value in args.items():
        if value != None and key != "func" and key != "name":
            entry[key] = value
    config[args["name"]] = entry
    with open(DATA_FILENAME, 'w') as configfile:
        config.write(configfile)

def edit(args): # Edits the information associated with a certain feed
    DATA_DIR = retrieve_data_directory()
    DATA_FILENAME =  os.path.join(DATA_DIR, "data")
    FEED_INFO =  os.path.join(DATA_DIR, args["name"])
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    if not(args["name"] in feeds):
        sys.exit("You don't have a feed with that name.")
    for key,value in args.items():
        if value != None and key == "url":
            feeds[args["name"]][key] = str(value)
            with open(DATA_FILENAME, 'w') as configfile:
                feeds.write(configfile)
        if value != None and key == "downloadfrom":
            try:
                dateinfo = (feeds[args["name"]]["date_info"] == "not available")
            except KeyError:
                feeds[args["name"]]["date_info"] = "available" # provisionally!
                with open(DATA_FILENAME, 'w') as configfile:
                    feeds.write(configfile)
                dateinfo = False #provisionally
            if dateinfo:
                print("{} has no date information that I can use. Using --downloadfrom might not have the results that you expect.", file = sys.stderr, flush = True)
            line =' '.join(["currentdate", str(value), "\n"]) # A dummy entry with the right date, in case we need it.
            try:
                # Remove from the feed file all entries after or equal to downloadfrom
                with open(FEED_INFO, 'r') as previous:
                    current = list(filterfalse(lambda line: value < get_date(line), previous))
                    if current == [] and dateinfo:
                        current = [line]
                with open(FEED_INFO, 'w') as currentfile:
                    currentfile.writelines(current)
            except FileNotFoundError:
                # Write the file with a dummy entry with the right date
                with open(FEED_INFO, 'w') as currentfile:
                    currentfile.write(line)

def remove(args): # Removes a certain feed
    DATA_DIR = retrieve_data_directory()
    DATA_FILENAME =  os.path.join(DATA_DIR, "data")
    FEED_INFO =  os.path.join(DATA_DIR, args["name"])
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    if not(args["name"] in feeds):
        sys.exit("You don't have a feed with that name.")
    inputtext = "Are you sure you want to remove the {} feed? (y/N) ".format(args["name"])
    reply = input(inputtext)
    if reply != "y" and reply != "Y": 
        return 0
    else:
        feeds.remove_section(args["name"])
        with open(DATA_FILENAME, 'w') as configfile:
            feeds.write(configfile)
        try:
            os.remove(os.path.join(DATA_DIR, args["name"]))
        except FileNotFoundError:
            pass

def info(args): # Provides information of a number of feeds
    if "all" in args["names"]:
        feeds = list_feeds()
    else:
        feeds = args["names"]
    for feed in feeds:
        pretty_print(feed)

def pretty_print(feed): # Prints the dictionary entry of a feed in a nice way.
    print ()
    DATA_DIR = retrieve_data_directory()
    FEED_INFO =  os.path.join(DATA_DIR, feed)
    DATA_FILENAME =  os.path.join(DATA_DIR, "data")
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    entrylinks, linkdates = parse_feed_info(FEED_INFO)
    print (feed)
    print ("-"*len(feed))
    print (''.join(["    url: " , feeds[feed]["url"]]))
    if linkdates != []:
        print (''.join(["    Next sync will download from: ", time.strftime("%d %b %Y %H:%M:%S", tuple(max(linkdates))),"."]))

def list_for_user(args):
    for feed in list_feeds():
        print (feed, end=" ")
    print ()

def list_feeds(): # Outputs a list of all feed names
    feedslist = []
    DATA_FILENAME =  os.path.join(retrieve_data_directory(), "data")
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    return feeds.sections()

def sync(args):
    DATA_DIR = retrieve_data_directory()
    DATA_FILENAME =  os.path.join(DATA_DIR, "data")
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    if "all" in args["names"]:
        targetfeeds = list_feeds()
    else:
        targetfeeds = []
        for name in args["names"]:
            if name not in feeds:
                print("You don't have a feed called {}.".format(name), file = sys.stderr, flush = True)
            else:
                targetfeeds.append(name)
    for feed in targetfeeds:
        transition(feed, feeds)
        podcast = feedparser.parse(feeds[feed]["url"])
        directory = check_directory(feed, podcast)
        willtag = will_tag(feed)
        mime = retrieve_mime(feed)
        try:
            wentwrong = "URLError" in str(podcast["bozo_exception"])
        except KeyError:
            wentwrong = False
        if not wentwrong:
            try:
                title = podcast.feed.title
            except AttributeError:
                title = feed
            print ("Checking",title, end = "...\n")
            sync_by_date = has_date(podcast)
            if not sync_by_date:
                feeds[feed]["date_info"] = "not available"
                with open(DATA_FILENAME, 'w') as configfile:
                    feeds.write(configfile)
            else:
                feeds[feed]["date_info"] = "available"
                with open(DATA_FILENAME, 'w') as configfile:
                    feeds.write(configfile)
            FEED_INFO = os.path.join(DATA_DIR, feed)
            entrylinks, linkdates = parse_feed_info(FEED_INFO)
            if linkdates != []:
                currentdate = max(linkdates)
                stop = 10^6
            else:
                currentdate = [1,1,1,0,0]
                firstsync = retrieve_config(feed, 'firstsync', '1')
                if firstsync == 'all':
                    stop = 10^6 # I'm guessing no feed in the world will have more than a million entries 
                else:
                    stop = int(firstsync)
            entrycounter = 0
            for entry in podcast.entries:
                if sync_by_date:
                    try:
                        linkdate = list(entry.published_parsed)
                    except AttributeError:
                        linkdate = list(entry.updated_parsed)
                else:
                    linkdate = list(time.localtime())
                downloadlinks = []
                for enclosure in entry.enclosures: 
                    # We will download all enclosures of the desired mime-type
                    if any([mimetype in enclosure["type"] for mimetype in mime]): 
                        downloadlinks.append(urlparse(enclosure["href"]).path.split("/")[-1]) # preserve the original name
                for podname in downloadlinks: 
                    if podname not in entrylinks:
                        if linkdate > currentdate and entrycounter < stop:
                            try:
                                print ("Downloading {} -- {}".format(entry.title, podname))
                            except:
                                print ("Downloading entry -- {}".format(podname))
                            try:
                                podpath = os.path.join(directory, podname)
                                download_handler(feed, enclosure["href"],podname,directory,podpath)
                                if willtag:
                                    tag(feed, entry, podcast, podpath)
                            except URLError:
                                sys.exit ("... something went wrong. Are you sure you are connected to the internet?")
                        with open(FEED_INFO, 'a') as current: # We write to file this often to ensure that downloaded entries count as downloaded.
                            current.write(''.join([podname, ' ', str(linkdate),'\n']))
                entrycounter += 1
            print ("Done")
        else:
            msg = ''.join(["I cannot sync " , feed , " just now. Are you connected to the internet?"])
            print(msg, file = sys.stderr, flush = True)
        
def check(args):
    DATA_DIR = retrieve_data_directory()
    DATA_FILENAME =  os.path.join(DATA_DIR, "data")
    feeds = configparser.ConfigParser()
    feeds.read(DATA_FILENAME)
    if str(args["url"]) != 'None':
        url = args["url"]
        name = "DEFAULT"
    else:
        url = feeds[args["feed"]]["url"]
        name = args["feed"]
    try:
        podcast = feedparser.parse(url)
        wentwrong = "urlopen" in str(podcast["bozo_exception"])
    except KeyError:
        wentwrong = False
    if wentwrong:
        sys.exit("I cannot check that podcast now. You are probably not connected to the internet.")
    for entry in enumerate(podcast.entries):
        listentry=list(entry)
        print (listentry[0], end =": ")
        try:
            print (listentry[1]["title"], end = " (")
        except:
            print (listentry[1]["link"], end = " (")
        try:
            print (listentry[1]["updated"], end =")")
        except:
            print ("", end =")")
        print ()
    dumpfilename = os.path.join(DATA_DIR, 'feeddump')
    with open(dumpfilename, mode='wb') as dumpfile:
        dump = [name, podcast]
        pickle.dump(dump, dumpfile)

def download(args):
    issues = parse_for_download(args)
    DATA_DIRECTORY = retrieve_data_directory()
    dumpfilename = os.path.join(DATA_DIRECTORY, 'feeddump')
    if not(os.path.isfile(dumpfilename)):
        sys.exit("You need to run ""greg check <feed>"" before using ""greg download"".")
    with open(dumpfilename, mode='rb') as dumpfile:
        dump = pickle.load(dumpfile)
        try:
            directory = check_directory(dump[0], dump[1])
        except Exception:
            sys.exit("... something went wrong. Are you sure your last check went well?")
        ensure_dir(directory)
        for number in issues:
            entry = dump[1].entries[eval(number)]
            for enclosure in entry.enclosures:
                if "audio" in enclosure["type"]: # if it's an audio file
                    podname = urlparse(enclosure["href"]).path.split("/")[-1] # preserve the original name
                    try:
                        print ("Downloading {} -- {}".format(entry.title, podname))
                    except:
                       print("Downloading entry -- {}".format(podname))
                    try:
                        podpath = os.path.join(directory, podname)
                        download_handler(dump[0], enclosure["href"],podname,directory,podpath)
                        print("Done")
                    except URLError:
                        sys.exit("... something went wrong. Are you sure you are connected to the internet?")




# Copyright (C) 2012, 2016  Manolo Martínez <manolo@austrohungaro.com>
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
Defines the functions corresponding to each of the subcommands
"""
import os.path
import pickle
import sys
import time

import greg.classes as c
import greg.aux_functions as aux

try:  # lxml is an optional dependency for pretty printing opml export
    from lxml import etree as ET
    lxmlexists = True
except ImportError:
    import xml.etree.ElementTree as ET
    lxmlexists = False

def retrieveglobalconf(args):
    """
    Retrieve the global config path
    """
    print(c.config_filename_global)


def add(args):
    """
    Add a new feed
    """
    session = c.Session(args)
    isduplicate = False
    for feed in session.list_feeds():
        if session.feeds.has_option(feed, "url") and args["url"] == session.feeds.get(feed, "url"):
            print("You are already subscribed to %r as %r." % (args["url"], str(feed)))
            isduplicate = True
        elif args["name"] in feed:
            print("You already have a feed called %r." % args["name"])
            isduplicate = True
        elif args["name"] in ["all", "DEFAULT"]:
            print(
                ("greg uses ""{}"" for a special purpose."
                "Please choose another name for your feed.").format(args["name"]))
            isduplicate = True
    if not isduplicate:
        entry = {}
        for key, value in args.items():
            if value is not None and key != "func" and key != "name" and key != "import":
                entry[key] = value
        session.feeds[args["name"]] = entry
        with open(session.data_filename, 'w') as configfile:
            session.feeds.write(configfile)
        print("Added %r." % args["name"])


def edit(args):  # Edits the information associated with a certain feed
    session = c.Session(args)
    name = args["name"][0]
    feed_info = os.path.join(session.data_dir, name)
    if not(name in session.feeds):
        sys.exit("You don't have a feed with that name.")
    for key, value in args.items():
        if value is not None and key == "url":
            session.feeds[name][key] = str(value[0])
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
            line = ' '.join(["currentdate", str(value[0]), "\n"])
            # A dummy entry with the new downloadfrom date.
            try:
                # Remove from the feed file all entries
                # after or equal to downloadfrom, then append line
                with open(feed_info, 'r') as previous:
                    previouslist = previous.readlines()
                    current = [aline for aline in previouslist if value >
                               aux.get_date(aline)]
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
    session = c.Session(args)
    for name in args["name"]:
        if not name in session.feeds:
            sys.exit("You don't have a feed with that name.")
        inputtext = ("Are you sure you want to remove the {} "
                     "feed? (y/N) ").format(name)
        reply = input(inputtext)
        if reply != "y" and reply != "Y":
            print('Not removed')
        else:
            session.feeds.remove_section(name)
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
            try:
                os.remove(os.path.join(session.data_dir, name))
            except FileNotFoundError:
                pass

def get_feeds(args): # Returns a list of feed names
    session = c.Session(args)
    return session.list_feeds()

def info(args):
    """
    Provide information of a number of feeds
    """
    session = c.Session(args)
    if "all" in args["names"]:
        feeds = get_feeds(args)
    else:
        feeds = args["names"]
    for feed in feeds:
        aux.pretty_print(session, feed)


def list_for_user(args):
    session = c.Session(args)
    for feed in sorted(session.list_feeds()):
        print(feed)
    print()


def sync(args):
    """
    Implement the 'greg sync' command
    """
    import operator
    session = c.Session(args)
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
        feed = c.Feed(session, target, None)
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
    session = c.Session(args)
    if str(args["url"]) != 'None':
        url = args["url"][0]
        name = "DEFAULT"
    else:
        try:
            name = args["feed"][0]
            url = session.feeds[name]["url"]
        except KeyError:
            sys.exit("You don't appear to have a feed with that name.")
    podcast = aux.parse_podcast(str(url))
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
    session = c.Session(args)
    issues = aux.parse_for_download(args)
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
        feed = c.Feed(session, dump[0], dump[1])
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

def opml(args):
    """
    Implement the 'greg opml' command
    """
    if args["import"]:
        opmlfile = args["import"][0]
        try:
            opmltree = ET.parse(opmlfile)
        except ET.ParseError:
            sys.exit("%r does not appear to be a valid opml file." % opmlfile)
        for element in opmltree.iterfind('.//*[@type="rss"]'):
            if element.get('xmlUrl'):
                args["url"] = element.get('xmlUrl')
            elif element.get('url'):
                args["url"] = element.get('url')
            if element.get('title'):
                args["name"] = element.get('title')
            elif element.get('text'):
                args["name"] = element.get('text')
            else:
                print("No title found for this feed, using url as title.")
                args["name"] = args["url"]
            add(args)
    if args["export"]:
        session = c.Session(args)
        filename = args["export"][0]
        toplevel = ET.Element("opml")
        toplevel.set("version", "2.0")
        head = ET.SubElement(toplevel, "head")
        title = ET.SubElement(head, "title")
        title.text = "Podcasts"
        dateCreated = ET.SubElement(head, "dateCreated")
        dateCreated.text = time.strftime("%c %Z")
        body = ET.SubElement(toplevel, "body")
        for feedname in sorted(session.list_feeds()):
            if session.feeds.has_option(feedname, "url"):
                feedurl = session.feeds.get(feedname, "url")
                feedtype = aux.feedparser.parse(feedurl).version
                if "rss" in feedtype: feedtype = "rss"
                elif "atom" in feedtype: feedtype = "atom"
                else: 
                    feedtype = False
                    print("%r is not a valid feed, skipping." % feedname)
                if feedtype:
                    print("Exporting %r..." % (feedname))
                    outline = ET.SubElement(body, "outline")
                    outline.set("text", feedname)
                    outline.set("title", feedname)
                    outline.set("xmlUrl", feedurl)
                    outline.set("type", feedtype)
        opmlfile = open(filename, 'wb')
        opmlfile.write(('<?xml version="1.0" encoding="UTF-8"?>\n' \
                + '<!-- Generated by greg (https://github.com/manolomartinez/greg) on ' \
                + time.strftime("%c %Z") + ' -->\n\n').encode())
        if lxmlexists:
            opmlfile.write(ET.tostring(toplevel, encoding="utf-8", pretty_print=True))
        else:
            opmlfile.write(ET.tostring(toplevel, encoding="utf-8"))
        opmlfile.close()

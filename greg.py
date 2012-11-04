#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time
from urllib.request import urlretrieve

import feedparser

CONFIG_FILENAME = os.path.expanduser('~/.config/greg')
DOWNLOAD_PATH = os.path.expanduser('~/Podcasts')
DATA_FILENAME = os.path.expanduser('~/.local/share/greg/data')


def ensure_dir(dirname):
    """Most of this code is from http://stackoverflow.com/questions/273192/"""
    try:
        os.makedirs(dirname)
    except OSError:
        if not os.path.isdir(dirname):
            raise

def add(args): # Adds a new feed
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        if args.name in feeds:
            print ("You already have a feed with that name.")
            return 0
    with open(DATA_FILENAME, mode='w', encoding='utf-8') as feedsjson:
        entry = {}
        for key,value in vars(args).items():
            if value != None and key != "func" and key != "name":
                entry[key] = value
        feeds[args.name] = entry
        json.dump(feeds, feedsjson)

def edit(args): # Edits the information associated with a certain feed
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        if not(args.name in feeds):
            print ("You don't have a feed with that name.")
            return 0
    with open(DATA_FILENAME, mode='w', encoding='utf-8') as feedsjson:
        for key,value in vars(args).items():
            if value != None and key != "func" and key != "name":
                feeds[args.name][key] = value
        json.dump(feeds, feedsjson)

def info(args): # Provides information of a number of feeds
    if "all" in args.names:
        feeds = list_feeds()
    else:
        feeds = args.names
    for feed in feeds:
        pretty_print(feed)

def pretty_print(feed): # Prints the dictionary entry of a feed in a nice way.
    print ()
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        print (feed)
        print ("-"*len(feed))
        print ("    url: " + feeds[feed]["url"])
        if "downloadfrom" in feeds[feed]:
            if feeds[feed]["downloadfrom"] != None:
                print ("    In the next sync, greg will download podcasts issued later than", feeds[feed]["downloadfrom"], ".")
        if "download" in feeds[feed]:
            if feeds[feed]["download"] != None:
                print ("    In the next sync, greg will download the latest", feeds[feed]["download"], "podcasts.")

def list_feeds(): # Outputs a list of all feed names
    feedslist = []
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        for key in feeds:
            feedslist.append(key)
    return feedslist


def sync(args):
    if "all" in args.names:
        targetfeeds = list_feeds()
    else:
        targetfeeds = args.names
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        for feed in targetfeeds:
            podcast = feedparser.parse(feeds[feed]["url"])
            print ("Checking",podcast.feed.title,"...")
            # 
            # The directory to save files is named after the podcast.
            # 
            directory = os.path.join(DOWNLOAD_PATH, podcast.feed.title)
            ensure_dir(directory)
            # 
            # Download entries later than downloadfrom in the json entry
            #
            if "downloadfrom" in feeds[feed]:
                if feeds[feed]["downloadfrom"] != None:
                    latest = feeds[feed]["downloadfrom"]
                else:
                    latest = datetime.min # If there is no latest downloadfrom date, download all
            for entry in podcast.entries:
                if list(entry.updated_parsed) > latest:
                    print ("Downloading", entry.title)
                    podname = entry.enclosure.split('/')[-1].split('#')[0].split('?')[0]
                    urlretrieve(entry.enclosure, os.path.join(directory, podname))
            # 
            # New fromdate: the date of the latest feed update.
            # 
            feedtime = podcast.updated_parsed
            feeds[feed]["downloadfrom"]=feedtime
            print ("Done")
    with open(DATA_FILENAME, mode='w', encoding='utf-8') as feedsjson:
        json.dump(feeds, feedsjson)


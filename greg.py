#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time
from configparser import SafeConfigParser
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

def info(args):
    for feed in args.names:
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

def sync():
    # 
    # Opening the config file.
    # 
    config = SafeConfigParser()
    with open(CONFIG_FILENAME) as configfile:
        config.readfp(configfile)
    # 
    # We go through each section (i.e., feed) in the config file.
    # 
    for section in config.sections():
        # 
        # Fetch feed.
        # 
        podcast = feedparser.parse(config.get(section, 'url'))
        print ("Checking ",podcast.feed.title,"...")
        # 
        # The directory to save files is named after the podcast.
        # 
        directory = os.path.join(DOWNLOAD_PATH, podcast.feed.title)
        ensure_dir(directory)
        # 
        # Download entries later than fromdate in the config file.
# 
        latest = DateTime.strptime(
            config.get(section, 'fromdate'), '%Y-%m-%d %H:%M:%S'
        )
        for entry in podcast.entries:
            if DateTime(*entry.updated_parsed[:6]) > latest:
                print ("Downloading ", entry.title)
                podname = entry.link.split('/')[-1].split('#')[0].split('?')[0]
                urlretrieve(entry.link, os.path.join(directory, podname))
        # 
        # New fromdate: the date of the latest feed update.
        # 
        feedtime = DateTime(*podcast.updated_parsed[:6])
        config.set(section, 'fromdate', str(feedtime))
        with open(CONFIG_FILENAME, 'w') as configfile:
            config.write(configfile)
        print ("Done")


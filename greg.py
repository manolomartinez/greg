#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, pickle, time
from urllib.request import urlretrieve
from urllib.parse import urlparse 

import feedparser

CONFIG_FILENAME = os.path.expanduser('~/.config/greg')
DOWNLOAD_PATH = os.path.expanduser('~/Podcasts')
DATA_FILENAME = os.path.expanduser('~/.local/share/greg/data')
DATA_DIRECTORY = os.path.expanduser('~/.local/share/greg')

def ensure_dir(dirname):
    """Most of this code is from http://stackoverflow.com/questions/273192/"""
    try:
        os.makedirs(dirname)
    except OSError:
        if not os.path.isdir(dirname):
            raise

def parse_for_download(args):
    single_arg="" # in the first bit we put all arguments together and take out any
    list_of_feeds=[]
    for arg in args.number:
        single_arg = single_arg + " " + arg
    single_arg = single_arg.translate({32:None}) # eliminates spaces
    for group in single_arg.split(sep=","):
        if not("-" in group):
            list_of_feeds.append(group)
        else:
            extremes = group.split(sep="-")
            list_of_feeds = list_of_feeds + [str(x) for x in range (eval(extremes[0]),eval(extremes[1])+1)]
    return list_of_feeds

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
                print ("    Next sync will download from:", time.strftime("%d %b %Y %H:%M:%S", tuple(feeds[feed]["downloadfrom"]))+".")
        if "download" in feeds[feed]:
            if feeds[feed]["download"] != None:
                print ("    Next sync will download:", feeds[feed]["download"], "podcasts.")

def list_for_user(args):
    for feed in list_feeds():
        print (feed, end=" ")
    print ()

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
                    latest = [1,1,1,0,0] # If there is no latest downloadfrom date, download all
            else:
                latest = [1,1,1,0,0] # If there is no latest downloadfrom date, download all
            entrytimes = [latest] # Here we will put the times of each entry, to choose the max for "latest"
            for entry in podcast.entries:
                if list(entry.updated_parsed) > latest:
                    entrytimes.append(list(entry.updated_parsed))
                    print ("Downloading", entry.title)
                    for enclosure in entry.enclosures:
                        if "audio" in enclosure["type"]: # if it's an audio file
                            podname = urlparse(enclosure["href"]).path.split("/")[-1] # preserve the original name
                            urlretrieve(enclosure["href"], os.path.join(directory, podname))
            # 
            # New fromdate: the date of the latest feed update.
            # 
            feeds[feed]["downloadfrom"]=max(entrytimes)
            print ("Done")
    with open(DATA_FILENAME, mode='w', encoding='utf-8') as feedsjson:
        json.dump(feeds, feedsjson)

def check(args):
    with open(DATA_FILENAME, mode='r', encoding='utf-8') as feedsjson:
        feeds = json.load(feedsjson)
        podcast = feedparser.parse(feeds[args.name]["url"])
        for entry in enumerate(podcast.entries):
            listentry=list(entry)
            print (listentry[0], end =": ")
            print (listentry[1]["title"], end = " (")
            print (listentry[1]["updated"], end =")")
            print ()
    dumpfilename = os.path.join(DATA_DIRECTORY, 'feeddump')
    with open(dumpfilename, mode='wb') as dumpfile:
        pickle.dump(podcast, dumpfile)

def download(args):
    issues = parse_for_download(args)
    dumpfilename = os.path.join(DATA_DIRECTORY, 'feeddump')
    if not(os.path.isfile(dumpfilename)):
        print("You need to run ""greg check <feed>"" before using ""greg download"".")
        return 0
    with open(dumpfilename, mode='rb') as dumpfile:
        podcast = pickle.load(dumpfile)
        directory = os.path.join(DOWNLOAD_PATH, podcast.feed.title)
        ensure_dir(directory)
        for number in issues:
            entry = podcast.entries[eval(number)]
            print ("Downloading", entry.title)
            for enclosure in entry.enclosures:
                if "audio" in enclosure["type"]: # if it's an audio file
                    podname = urlparse(enclosure["href"]).path.split("/")[-1] # preserve the original name
                    urlretrieve(enclosure["href"], os.path.join(directory, podname))
    print("Done")




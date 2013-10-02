# Copyright (C) 2013  Pierre Marijon <pierre@marion.fr>
#
# This file is part of Greg.
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

import os
import sys
import configparser
from datetime import datetime
from time import sleep
import daemonic

from greg.greg import *

class Daemon():
    def __init__(self, args, time=0, user=None, log="/var/log/greg/", pid='/var/run/greg/greg.pid'):
        self.daemon_user = user
        self.pidfile_path = pid
        self.log_dir = log
        self.sleep_time = time 
        self.session = Session(args)
        self.feeds_time = configparser.ConfigParser()
        self.feeds_time_path = os.path.join(self.session.data_dir, "feed_time")
        self.feeds_time.read(self.feeds_time_path)
        self.date_format_write = "%Y-%m-%d %H:%M:%S%z"
        self.date_format_podcast = "%a, %d %b %Y %H:%M:%S %z"

    def start(self):
        out = open(os.path.join(self.log_dir, "message.log"), "a")
        err = open(os.path.join(self.log_dir, "error.log"), "a")
        d = daemonic.daemon(pidfile=self.pidfile_path, stdout=out, stderr=err, user=self.daemon_user)

        with d:
            while True :
                self.__daemon_work()
                sleep(self.sleep_time)

    def stop(self):
        d = daemonic.daemon(pidfile=self.pidfile_path)
        d.stop()

    def __daemon_work(self):
        print("Check podcast "+datetime.now().strftime(self.date_format_podcast)+".")
        # Set data and conf file after change user
        self.session.config_filename_user = self.session.retrieve_config_file()
        self.session.data_dir = self.session.retrieve_data_directory()
        self.session.data_filename = os.path.join(self.session.data_dir, "data")
        self.session.feeds.read(self.session.data_filename)
        self.session.config.read([config_filename_global, self.session.config_filename_user])
        self.feeds_time_path = os.path.join(self.session.data_dir, "feed_time")
        self.feeds_time.read(self.feeds_time_path)

        # For each feed check if update
        for feed_name in self.session.list_feeds():
            print("Check "+feed_name+" feed")

            # Find date of last podcast in remote and local
            podcast = create_podcast(self.session.feeds[feed_name]["url"])

            remote_date_str = re.sub("(.*\s\+\d\d):(\d\d)$", r"\1\2", podcast.entries[0]["published"])
            remote_date = datetime.strptime(remote_date_str, self.date_format_podcast)

            # Test if is the first check of this feed
            if feed_name not in self.feeds_time.sections():
                 self.__download_podcast(feed_name, podcast, remote_date)

            local_date_str = re.sub("(.*\+\d\d):(\d\d)$", r"\1\2", self.feeds_time[feed_name]["date"])
            local_date = datetime.strptime(local_date_str, self.date_format_write)

            # If remote_date up local_date why need download the last podcast
            if remote_date > local_date:
                self.__download_podcast(feed_name, podcast)
            else:
                print(feed_name+" podcast is uptodate.")

    def __download_podcast(self, feed_name, podcast, remote_date):
        # Download podcast
        load_feed = Feed(self.session, feed_name, podcast)
        load_feed.info = []
        load_feed.entrylinks = []
        load_feed.linkdate = list(time.localtime())
        download_entry(load_feed, podcast.entries[0])

        # Set time value in local storage
        entry = {}
        entry["date"] = remote_date
        self.feeds_time[feed_name] = entry
        with open(self.feeds_time_path, 'w') as configfile:
            self.feeds_time.write(configfile)

def main(args) :
    # Create daemon object
    if args["command"] == "start":
        if not(args["time"]):
            sys.exit("You dont set the time betowen tow check.")
        elif not(args["user"]):
            sys.exit("You dont set the user of worker processe.")
        else:
            daemon = Daemon(args, time=args["time"], user=args["user"], log=args["log_dir"], pid=args["pid_file"])
            daemon.start()
    elif args["command"] == "stop":
            daemon = Daemon(args, log=args["log_dir"], pid=args["pid_file"])
            daemon.stop()
    else:
        sys.exit("You need specifie start or stop.")

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
from pwd import getpwnam  
from time import sleep
import daemonic

from greg.greg import *

class Daemon():
    def __init__(self, args, time=0, user=None):
        self.daemon_user = user
        self.pidfile_path = '/var/run/greg/greg.pid'
        self.sleep_time = time 
        self.session = Session(args)
        self.feeds_time = configparser.ConfigParser()
        self.feeds_time_path = os.path.join(self.session.data_dir, "feed_time")
        self.feeds_time.read(self.feeds_time_path)
        self.date_format = "%a, %d %b %Y %H:%M:%S %z"

    def start(self):
        out = open("/var/log/greg/message.log", "a")
        err = open("/var/log/greg/error.log", "a")
        d = daemonic.daemon(pidfile=self.pidfile_path, stdout=out, stderr=err, user=self.daemon_user)
        
        with d:
            print(os.getuid())
            while True :
                self.__daemon_work()
                sleep(self.sleep_time)
        
    def stop(self):
        d = daemonic.daemon(pidfile=self.pidfile_path)
        d.stop()

    def __daemon_work(self):
        print("Check podcast caca"+datetime.now().strftime(self.date_format)+".")
        self.session.config_filename_user = self.session.retrieve_config_file()
        self.session.data_dir = self.session.retrieve_data_directory()
        self.session.data_filename =  os.path.join(self.session.data_dir, "data")
        print(self.session.list_feeds())
        for feed_name in self.session.list_feeds():
            podcast = create_podcast(self.session.feeds[feed_name]["url"])
        
            remote_date = datetime.strptime(podcast.entries[0]["published"], self.date_format)
            local_date = datetime.strptime(self.feeds_time[feed_name]["date"], self.date_format)
            print("Up to date "+feed_time+". "+(remote_date>local_date))
            if remote_date > local_date:
                load_feed = Feed(self.session, feed_name, podcast)
                load_feed.linkdate = list(time.localtime())
                download_entry(load_feed, podcast.entries[0])

                entry = {}
                entry["date"] = remote_date

                self.feeds_time[feed_name] = entry
                with open(self.feeds_time_path, 'w') as configfile:
                    self.feeds_time.write(configfile)
            else:
                print(feed_name+" podcast is uptodate.")

def main(args) :
    # Create daemon object
    if args["start"]:
        if not(args["t"]):
            sys.exit("You dont set the time betowen tow check.")
        else:
            daemon = Daemon(args, time=int(args["t"][0]), user=args["u"])
            daemon.start()
    elif args["stop"]:
            daemon = Daemon(args)
            daemon.stop()
    else:
        sys.exit("You need specifie start or stop.")
   

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

# Just for devel
import os
import sys

from time import sleep
import daemonic

import greg

class Daemon():
    def __init__(self, time):
        self.pidfile_path = os.path.dirname(__file__)+'.pid'
        self.sleep_time = time 
        
    def start(self):
        stout = open(os.path.dirname(__file__)+".log", "a")
        err = open(os.path.dirname(__file__)+".error", "a")
        d = daemonic.daemon(pidfile=self.pidfile_path, stdout=stout, stderr=err)
        with d:
            while True :
                sleep(self.sleep_time)

    def stop(self):
        d = daemonic.daemon(pidfile=self.pidfile_path)
        d.stop()

def main(args) :
    # Create daemon object
    if args["start"]:
        if not(args["t"]):
            sys.exit("You dont set the time betowen tow check.")
        else:
            daemon = Daemon(int(args["t"][0]))
            daemon.start()
    elif args["stop"]:
            daemon = Daemon(0)
            daemon.stop()
    else:
        sys.exit("You need specifie start or stop.")
   

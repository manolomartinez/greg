# Copyright (C) 2012 -- 2016  Manolo Martínez <manolo@austrohungaro.com>
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
This module defines the following classes:

* Session: takes into account flags passed by the command line instruction,
reads config files and data directory

* Feed: Sanitizes and organizes a particular feed and makes it available for
the subcommands

* Placeholders: Calculates and stores the values of placeholders
"""
import configparser
import os.path
import sys
import time
from pkg_resources import resource_filename
from urllib.parse import urlparse
from urllib.error import URLError

import greg.aux_functions as aux

config_filename_global = resource_filename(__name__, 'data/greg.conf')


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

    def list_feeds(self):
        """
        Output a list of all feed names
        """
        feeds = configparser.ConfigParser()
        feeds.read(self.data_filename)
        return feeds.sections()

    def retrieve_config_file(self):
        """
        Retrieve config file
        """
        try:
            if self.args["configfile"]:
                return self.args["configfile"]
        except KeyError:
            pass
        return os.path.expanduser('~/.config/greg/greg.conf')

    def retrieve_data_directory(self):
        """
        Retrieve the data directory
        Look first into config_filename_global
        then into config_filename_user. The latter takes preeminence.
        """
        args = self.args
        try:
            if args['datadirectory']:
                aux.ensure_dir(args['datadirectory'])
                return args['datadirectory']
        except KeyError:
            pass
        config = configparser.ConfigParser()
        config.read([config_filename_global, self.config_filename_user])
        section = config.default_section
        data_path = config.get(section, 'Data directory',
                               fallback='~/.local/share/greg')
        data_path_expanded = os.path.expanduser(data_path)
        aux.ensure_dir(data_path_expanded)
        return os.path.expanduser(data_path_expanded)


class Feed():
    """
    Calculate information about the current feed
    """
    def __init__(self, session, feed, podcast):
        self.session = session
        self.args = session.args
        self.config = self.session.config
        self.name = feed
        if not podcast:
            self.podcast = aux.parse_podcast(session.feeds[feed]["url"])
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
        self.entrylinks, self.linkdates = aux.parse_feed_info(self.info)

    def retrieve_config(self, value, default):
        """
        Retrieves a value (with a certain fallback) from the config files
        (looks first into config_filename_global then into
        config_filename_user. The latest takes preeminence) if the command line
        flag for the value is used, that overrides everything else
        """
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
        """
        Retrieves the download path (looks first into config_filename_global
        then into the [DEFAULT], then the [feed], section of
        config_filename_user. The latest takes preeminence)
        """
        section = self.name if self.config.has_section(
            self.name) else self.config.default_section
        download_path = self.config.get(
            section, 'Download directory', fallback='~/Podcasts')
        subdirectory = self.config.get(
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
            except AttributeError:
                try:
                    test = podcast.entries[0].published_parsed
                    sync_by_date = True
                except (AttributeError, IndexError):
                    # Otherwise, we use download links.
                    print(("I cannot parse the time information of this feed."
                           "I'll use your current local time instead."),
                          file=sys.stderr, flush=True)
                    sync_by_date = False
        if not sync_by_date:
            session.feeds[name]["date_info"] = "not available"
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
        else:
            try:
                if session.feeds[name]["date_info"] == "not available":
                    print(("Either this feed has changed, or greg has "
                           "improved, but we can now parse its time "
                           "information. This is good, but it also means that "
                           "(just this time) it's possible that you have "
                           "missed some entries. You might do a 'greg check "
                           "-f {}' to make sure that you're not missing out "
                           "on anything.").format(name))
            except KeyError:
                pass
            session.feeds[name]["date_info"] = "available"
            with open(session.data_filename, 'w') as configfile:
                session.feeds.write(configfile)
        return sync_by_date

    def will_tag(self):
        """
        Check whether the feed should be tagged
        """
        wanttags = self.retrieve_config('Tag', 'no')
        if wanttags == 'yes':
            if aux.staggerexists:
                willtag = True
            else:
                willtag = False
                print(("You want me to tag {0}, but you have not installed "
                       "the Stagger module. I cannot honour your request.").
                      format(self.name), file=sys.stderr, flush=True)
        else:
            willtag = False
        return willtag

    def how_many(self):
        """
        Ascertain where to start downloading, and how many entries.
        """
        if self.linkdates != []:
            # What follows is a quick sanity check: if the entry date is in the
            # future, this is probably a mistake, and we just count the entry
            # date as right now.
            if max(self.linkdates) <= list(time.localtime()):
                currentdate = max(self.linkdates)
            else:
                currentdate = list(time.localtime())
                print(("This entry has its date set in the future. "
                       "I will use your current local time as its date "
                       "instead."),
                      file=sys.stderr, flush=True)
            stop = sys.maxsize
        else:
            currentdate = [1, 1, 1, 0, 0]
            firstsync = self.retrieve_config('firstsync', '1')
            if firstsync == 'all':
                stop = sys.maxsize
            else:
                stop = int(firstsync)
        return currentdate, stop

    def fix_linkdate(self, entry):
        """
        Give a date for the entry, depending on feed.sync_by_date
        Save it as feed.linkdate
        """
        if self.sync_by_date:
            try:
                entry.linkdate = list(entry.published_parsed)
                self.linkdate = list(entry.published_parsed)
            except (AttributeError, TypeError):
                try:
                    entry.linkdate = list(entry.updated_parsed)
                    self.linkdate = list(entry.updated_parsed)
                except (AttributeError, TypeError):
                    print(("This entry doesn't seem to have a parseable date. "
                           "I will use your local time instead."),
                          file=sys.stderr, flush=True)
                    entry.linkdate = list(time.localtime())
                    self.linkdate = list(time.localtime())
        else:
            entry.linkdate = list(time.localtime())

    def retrieve_mime(self):
        """
        Check the mime-type to download
        """
        mime = self.retrieve_config('mime', 'audio')
        mimedict = {"number": mime}
        # the input that parse_for_download expects
        return aux.parse_for_download(mimedict)

    def download_entry(self, entry):
        """
        Find entry link and download entry
        """
        downloadlinks = {}
        downloaded = False
        ignoreenclosures = self.retrieve_config('ignoreenclosures', 'no')
        notype = self.retrieve_config('notype', 'no')
        if ignoreenclosures == 'no':
            for enclosure in entry.enclosures:
                if notype == 'yes':
                    downloadlinks[urlparse(enclosure["href"]).path.split(
                        "/")[-1]] = enclosure["href"]
                    # preserve original name
                else:
                    try:
                        # We will download all enclosures of the desired
                        # mime-type
                        if any([mimetype in enclosure["type"] for mimetype in
                                self.mime]):
                            downloadlinks[urlparse(
                                enclosure["href"]).path.split(
                                    "/")[-1]] = enclosure["href"]
                            # preserve original name
                    except KeyError:
                        print("This podcast carries no information about "
                              "enclosure types. Try using the notype "
                              "option in your greg.conf", file=sys.stderr,
                              flush=True)
        else:
            downloadlinks[urlparse(entry.link).query.split(
                "/")[-1]] = entry.link
        for podname in downloadlinks:
            if (podname, entry.linkdate) not in zip(self.entrylinks,
                                                    self.linkdates):
                try:
                    title = entry.title
                except:
                    title = podname
                try:
                    sanitizedsummary = aux.html_to_text(entry.summary)
                    if sanitizedsummary == "":
                        sanitizedsummary = "No summary available"
                except:
                    sanitizedsummary = "No summary available"
                try:
                    placeholders = Placeholders(
                        self, entry, downloadlinks[podname], podname, title,
                        sanitizedsummary)
                    placeholders = aux.check_directory(placeholders)
                    condition = aux.filtercond(placeholders)
                    if condition:
                        print("Downloading {} -- {}".format(title, podname))
                        aux.download_handler(self, placeholders)
                        if self.willtag:
                            aux.tag(placeholders)
                        downloaded = True
                    else:
                        print("Skipping {} -- {}".format(title, podname))
                        downloaded = False
                    if self.info:
                        with open(self.info, 'a') as current:
                            # We write to file this often to ensure that
                            # downloaded entries count as downloaded.
                            current.write(''.join([podname, ' ',
                                          str(entry.linkdate), '\n']))
                except URLError:
                    sys.exit(("... something went wrong. "
                             "Are you connected to the internet?"))
        return downloaded


class Placeholders:
    def __init__(self, feed, entry, link, filename, title, summary):
        self.feed = feed
        self.link = link
        self.filename = filename
        # self.fullpath = os.path.join(self.directory, self.filename)
        self.title = title.replace("\"", "'")
        self.filename_title = aux.sanitize(title)
        try:
            self.podcasttitle = feed.podcast.title
        except AttributeError:
            self.podcasttitle = feed.name
        try:
            self.sanitizedsubtitle = aux.html_to_text(
                feed.podcast.feed.subtitle)
            if self.sanitizedsubtitle == "":
                self.sanitizedsubtitle = "No description"
        except AttributeError:
            self.sanitizedsubtitle = "No description"
        self.entrysummary = summary
        self.filename_podcasttitle = aux.sanitize(self.podcasttitle)
        self.name = feed.name
        self.date = tuple(entry.linkdate)

    def date_string(self):
        date_format = self.feed.retrieve_config("date_format", "%Y-%m-%d")
        return time.strftime(date_format, self.date)

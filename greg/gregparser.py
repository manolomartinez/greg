# Copyright (C) 2012, 2013  Manolo Martínez <manolo@austrohungaro.com>
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

import argparse, time, sys
from urllib.parse import urlparse

import greg.greg

try:
    import argcomplete
    argcompleteexists = True
except ImportError:
    argcompleteexists = False

# defining the from_date type
def from_date(string):
    try:
        fd =  list(time.strptime(string, "%Y-%m-%d"))
    except Exception:
        msg = "the date should be in the form YYYY-MM-DD"
        raise argparse.ArgumentTypeError(msg)
    return fd

# defining the url type
def url(string):
    testurl = urlparse(string)
    if not testurl.netloc:
        msg = "%r does not appear to be an url (be sure to use the full url, including the ""http(s)"" bit)" % string
        raise argparse.ArgumentTypeError(msg)
    return string

# get list of feed names and pass to global var
def set_FeedChoices(value):
    global feednames
    feednames=greg.greg.get_feeds(value)

# send list of subscribed feeds to argcomplete
def customCompleter(prefix, parsed_args, **kwargs):
    if not parsed_args.datadirectory and not parsed_args.configfile:
        set_FeedChoices({}) #if datadirectory or configfile are not specified, get greg to use default
    return feednames

# set possible choices to list of feed names for appropriate data dir or configfile
class customActionSetFeedChoices(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if "datadirectory" in self.dest:
            set_FeedChoices({"datadirectory" : values})
            setattr(namespace, self.dest, values)
        elif "configfile" in self.dest:
            set_FeedChoices({"configfile" : values})
            setattr(namespace, self.dest, values)
        else:
            if values == self.default:
                setattr(namespace, self.dest, values)
            else:
                try:
                    self.choices = feednames
                except NameError:
                    set_FeedChoices(vars(namespace))
                    self.choices = feednames
                for value in values:
                    if value not in self.choices:
                        msg = "%r is not a valid feed" % value
                        raise argparse.ArgumentError(self, msg)
                setattr(namespace, self.dest, values)

#Create the top-level parser
parser = argparse.ArgumentParser()
parser.add_argument('--configfile', '-cf',
                    help='specifies the config file that greg should use', action=customActionSetFeedChoices, metavar='CONFIGFILE')
parser.add_argument('--datadirectory', '-dtd',
                    help='specifies the directory where greg keeps its data', action=customActionSetFeedChoices, metavar='DATADIRECTORY')

subparsers = parser.add_subparsers()

# create the parser for the "add" command
parser_add = subparsers.add_parser('add', help='adds a new feed')
parser_add.add_argument('name', help='the name of the new feed')
parser_add.add_argument('url', type = url, help='the url of the new feed')
parser_add.add_argument('--downloadfrom', '-d', type=from_date,
    help='the date from which files should be downloaded (YYYY-MM-DD)')
parser_add.set_defaults(func=greg.greg.add)

# create the parser for the "edit" command
parser_edit = subparsers.add_parser('edit', help='edits a feed')
parser_edit.add_argument('name', action=customActionSetFeedChoices, help='the name of the feed to be edited', nargs=1, metavar='FEEDNAME').completer = customCompleter
group = parser_edit.add_mutually_exclusive_group(required = True)
group.add_argument('--url', '-u', type = url, help='the new url of the feed', nargs=1)
group.add_argument('--downloadfrom', '-d', 
        type=from_date, help='the date from which files should be downloaded (YYYY-MM-DD)', nargs=1)
parser_edit.set_defaults(func=greg.greg.edit)

# create the parser for the "info" command
parser_info = subparsers.add_parser('info', help='provides information about a feed')
parser_info.add_argument('names', action=customActionSetFeedChoices, help='the name(s) of the feed(s) you want to know about', nargs='*', default=['all'], metavar='FEEDNAME').completer = customCompleter
parser_info.set_defaults(func=greg.greg.info)

# create the parser for the "list" command
parser_list = subparsers.add_parser('list', help='lists all feeds')
parser_list.set_defaults(func=greg.greg.list_for_user)

# create the parser for the "sync" command
parser_sync = subparsers.add_parser('sync', help='syncs feed(s)')
parser_sync.add_argument('names', help='the name(s) of the feed(s) you want to sync', action=customActionSetFeedChoices, nargs='*', default=['all'], metavar='FEEDNAME').completer = customCompleter
parser_sync.add_argument('--downloadhandler', '-dh', help='whatever you want greg to do with the enclosure')
parser_sync.add_argument('--downloaddirectory', '-dd', help='the directory to which you want to save your downloads')
parser_sync.add_argument('--firstsync', '-fs', help='the number of files to download (if this is the first sync)')
parser_sync.set_defaults(func=greg.greg.sync)

# create the parser for the "check" command
parser_check = subparsers.add_parser('check', help='checks feed')
check_group = parser_check.add_mutually_exclusive_group(required=True)
check_group.add_argument('--url', '-u', type = url, help='the url that you want to check', nargs=1)
check_group.add_argument('--feed', '-f', help='the feed that you want to check', action=customActionSetFeedChoices, nargs=1, metavar='FEEDNAME').completer = customCompleter
parser_check.set_defaults(func=greg.greg.check)

# create the parser for the "download" command
parser_download = subparsers.add_parser('download', help='downloads particular issues of a feed')
parser_download.add_argument('number', help='the issue numbers you want to download', nargs="*")
parser_download.add_argument('--mime', help='(part of) the mime type of the enclosure to download')
parser_download.add_argument('--downloadhandler', '-dh', help='whatever you want greg to do with the enclosure')
parser_download.add_argument('--downloaddirectory', '-dd', help='the directory to which you want to save your downloads')
parser_download.set_defaults(func=greg.greg.download)

# create the parser for the "remove" command
parser_remove = subparsers.add_parser('remove', help='removes feed(s)')
parser_remove.add_argument('name', help='the name of the feed(s) you want to remove', action=customActionSetFeedChoices, nargs='+', metavar='FEEDNAME').completer = customCompleter
parser_remove.set_defaults(func=greg.greg.remove)

# create the parser for the 'opml' command
parser_opml = subparsers.add_parser('opml', help='import/export an opml feed list')
opml_group = parser_opml.add_mutually_exclusive_group(required=True)
opml_group.add_argument('--import', '-i', help='import an opml feed', nargs=1, metavar='FILENAME')
opml_group.add_argument('--export', '-e', help='export an opml feed', nargs=1, metavar='FILENAME')
parser_opml.set_defaults(func=greg.greg.opml)

# create the parser for the 'retrieveglobalconf' command
parser_rgc = subparsers.add_parser('retrieveglobalconf', aliases=['rgc'],
                                   help='retrieves the path to the global config file')
parser_rgc.set_defaults(func=greg.greg.retrieveglobalconf)

def main():
    """
    Parse the args and call whatever function was selected
    """
    if argcompleteexists:
        argcomplete.safe_actions = argcomplete.safe_actions + (customActionSetFeedChoices,)
        argcomplete.autocomplete(parser)
    args = parser.parse_args()
    try:
        function = args.func
    except AttributeError:
        parser.print_usage()
        parser.exit(1)
    function(vars(args))

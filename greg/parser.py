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

import argparse
import time
from urllib.parse import urlparse

import greg.commands as commands


# defining the from_date type
def from_date(string):
    if string == "now":
        return list(time.localtime())
    else:
        try:
            fd = list(time.strptime(string, "%Y-%m-%d"))
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

# create the top-level parser
parser = argparse.ArgumentParser()
parser.add_argument('--configfile', '-cf',
                    help='specifies the config file that greg should use')
parser.add_argument('--datadirectory', '-dtd',
                    help='specifies the directory where greg keeps its data')
subparsers = parser.add_subparsers()

# create the parser for the "add" command
parser_add = subparsers.add_parser('add', help='adds a new feed')
parser_add.add_argument('name', help='the name of the new feed')
parser_add.add_argument('url', type=url, help='the url of the new feed')
parser_add.add_argument('--downloadfrom', '-d', type=from_date, help='the date\
                        from which files should be downloaded (YYYY-MM-DD)')
parser_add.set_defaults(func=commands.add)

# create the parser for the "edit" command
parser_edit = subparsers.add_parser('edit', help='edits a feed')
parser_edit.add_argument('name', help='the name of the feed to be edited')
group = parser_edit.add_mutually_exclusive_group(required=True)
group.add_argument('--url', '-u', type=url, help='the new url of the feed')
group.add_argument('--downloadfrom', '-d', type=from_date, help='the date from\
                   which files should be downloaded (YYYY-MM-DD)')
parser_edit.set_defaults(func=commands.edit)

# create the parser for the "info" command
parser_info = subparsers.add_parser('info', help='provides information \
                                    about a feed')
parser_info.add_argument('names', help='the name(s) of the feed(s) you want to\
                         know about', nargs='*', default='all')
parser_info.set_defaults(func=commands.info)

# create the parser for the "list" command
parser_info = subparsers.add_parser('list', help='lists all feeds')
parser_info.set_defaults(func=commands.list_for_user)

# create the parser for the "sync" command
parser_sync = subparsers.add_parser('sync', help='syncs feed(s)')
parser_sync.add_argument('names', help='the name(s) of the feed(s) you want to\
                         sync', nargs='*', default='all')
parser_sync.add_argument('--downloadhandler', '-dh', help='whatever you want\
                         greg to do with the enclosure')
parser_sync.add_argument('--downloaddirectory', '-dd', help='the directory to\
                         which you want to save your downloads')
parser_sync.add_argument('--firstsync', '-fs', help='the number of files to\
                         download (if this is the first sync)')
parser_sync.set_defaults(func=commands.sync)

# create the parser for the "check" command
parser_check = subparsers.add_parser('check', help='checks feed(s)')
group = parser_check.add_mutually_exclusive_group(required=True)
group.add_argument('--url', '-u', type=url, help='the url that you want to\
                   check')
group.add_argument('--feed', '-f', help='the feed that you want to check')
parser_check.set_defaults(func=commands.check)

# create the parser for the "download" command
parser_download = subparsers.add_parser('download', help='downloads particular\
                                        issues of a feed')
parser_download.add_argument('number', help='the issue numbers you want to\
                             download', nargs="*")
parser_download.add_argument('--mime', help='(part of) the mime type of the\
                             enclosure to download')
parser_download.add_argument('--downloadhandler', '-dh', help='whatever you\
                             want greg to do with the enclosure')
parser_download.add_argument('--downloaddirectory', '-dd', help='the directory\
                             to which you want to save your downloads')
parser_download.set_defaults(func=commands.download)

# create the parser for the "remove" command
parser_remove = subparsers.add_parser('remove', help='removes feed(s)')
parser_remove.add_argument('name', help='the name of the feed you want to\
                           remove')
parser_remove.set_defaults(func=commands.remove)

# create the parser for the 'retrieveglobalconf' command
parser_rgc = subparsers.add_parser('retrieveglobalconf', aliases=['rgc'],
                                   help='retrieves the path to the global\
                                   config file')
parser_rgc.set_defaults(func=commands.retrieveglobalconf)


def main():
    """
    Parse the args and call whatever function was selected
    """
    args = parser.parse_args()
    try:
        function = args.func
    except AttributeError:
        parser.print_usage()
        parser.exit(1)
    function(vars(args))

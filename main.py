#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, time, sys

import greg

# defining the from_date type
def from_date(string):
    fd =  time.strptime(string, "%d/%m/%y")
    print (fd)
    return fd

# create the top-level parser
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

# create the parser for the "add" command
parser_add = subparsers.add_parser('add', help='adds a new feed')
parser_add.add_argument('name', help='the name of the new feed')
parser_add.add_argument('url', help='the url of the new feed')
parser_add.add_argument('--downloadfrom', type=from_date, help='the date from which files should be downloaded [%Y-%m-%d]')
parser_add.set_defaults(func=greg.add)

# create the parser for the "edit" command
parser_edit = subparsers.add_parser('edit', help='edits a new feed')
parser_edit.add_argument('name', help='the name of the feed to be edited')
parser_edit.add_argument('--url', help='the new url for the feed')
parser_edit.add_argument('--downloadfrom', type=from_date, help='the date from which files should be downloaded [%Y-%m-%d]')
parser_edit.set_defaults(func=greg.edit)

# create the parser for the "info" command
parser_info = subparsers.add_parser('info', help='provides information about a feed')
parser_info.add_argument('names', help='the name(s) of the feed(s) you want to know about', nargs='*', default='all')
parser_info.set_defaults(func=greg.info)

# create the parser for the "list" command
parser_info = subparsers.add_parser('list', help='lists all feeds')
parser_info.set_defaults(func=greg.list_for_user)

# create the parser for the "sync" command
parser_sync = subparsers.add_parser('sync', help='syncs feed(s)')
parser_sync.add_argument('names', help='the name(s) of the feed(s) you want to sync', nargs='*', default='all')
parser_sync.set_defaults(func=greg.sync)

# create the parser for the "check" command
parser_check = subparsers.add_parser('check', help='checks feed(s)')
parser_check.add_argument('name', help='the name of the feed you want to check')
parser_check.set_defaults(func=greg.check)

# create the parser for the "download" command
parser_download = subparsers.add_parser('download', help='downloads particular issues of a podcast')
parser_download.add_argument('number', help='the issue numbers you want to download', nargs="*")
parser_download.set_defaults(func=greg.download)

# create the parser for the "tag" command
#parser_tag = subparsers.add_parser('tag', help='tags feed(s)')
#parser_tag.add_argument('name', help='the name of the feed you want to tag')
#parser_tag.set_defaults(func=greg.tag)

# create the parser for the "untag" command
#parser_untag = subparsers.add_parser('untag', help='untags feed(s)')
#parser_untag.add_argument('name', help='the name of the feed you want to untag')
#parser_untag.set_defaults(func=greg.untag)

# create the parser for the "pfd" command
parser_pfd = subparsers.add_parser('pfd', help='pfds feed(s)')
parser_pfd.add_argument('number', help='the name of the feed you want to pfd', nargs="*")
parser_pfd.set_defaults(func=greg.parse_for_download)

# parse the args and call whatever function was selected
args = parser.parse_args(sys.argv[1:])
args.func(args)

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
dateornumber = parser_add.add_mutually_exclusive_group()
dateornumber.add_argument('--downloadfrom', type=from_date, help='the date from which files should be downloaded [%Y-%m-%d]')
dateornumber.add_argument('--download', help='the number of files to be downloaded')
parser_add.set_defaults(func=greg.add)

# create the parser for the "edit" command
parser_edit = subparsers.add_parser('edit', help='edits a new feed')
parser_edit.add_argument('name', help='the name of the feed to be edited')
parser_edit.add_argument('--url', help='the new url for the feed')
dateornumber = parser_edit.add_mutually_exclusive_group()
dateornumber.add_argument('--downloadfrom', type=from_date, help='the date from which files should be downloaded [%Y-%m-%d]')
dateornumber.add_argument('--download', help='the number of files to be downloaded')
parser_edit.set_defaults(func=greg.edit)

# create the parser for the "info" command
parser_info = subparsers.add_parser('info', help='provides information about a feed')
parser_info.add_argument('names', help='the name(s) of the feed(s) you want to know about', nargs='*', default='all')
parser_info.set_defaults(func=greg.info)

# create the parser for the "list" command
parser_info = subparsers.add_parser('list', help='lists all feeds')
parser_info.set_defaults(func=greg.list_feeds)

# create the parser for the "sync" command
parser_sync = subparsers.add_parser('sync', help='syncs feed(s)')
parser_sync.add_argument('names', help='the name(s) of the feed(s) you want to sync', nargs='*', default='all')
parser_sync.set_defaults(func=greg.sync)

# parse the args and call whatever function was selected
args = parser.parse_args(sys.argv[1:])
args.func(args)

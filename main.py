#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, datetime, sys

import greg

# create the top-level parser
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

# create the parser for the "add" command
parser_add = subparsers.add_parser('add', help='adds a new feed')
parser_add.add_argument('name', help='the name of the new feed')
parser_add.add_argument('url', help='the url of the new feed')
dateornumber = parser_add.add_mutually_exclusive_group()
dateornumber.add_argument('--date', type = datetime.date, help='the date from which files should be downloaded [%Y-%m-%d]')
dateornumber.add_argument('--number', help='the number of files to be downloaded')
parser_add.set_defaults(func=greg.add)

# create the parser for the "edit" command
parser_edit = subparsers.add_parser('edit', help='edits a new feed')
parser_edit.add_argument('name', help='the name of the new feed')
dateornumber = parser_edit.add_mutually_exclusive_group()
dateornumber.add_argument('--date', type = datetime.date, help='the date from which files should be downloaded [%Y-%m-%d]')
dateornumber.add_argument('--number', help='the number of files to be downloaded')
parser_edit.set_defaults(func=greg.add)


# parse the args and call whatever function was selected
print(sys.argv)
args = parser.parse_args(sys.argv[1:])
print (args)
args.func(args)

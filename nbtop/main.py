#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
nbtop - resource monitor for IPython Notebook servers

source: https://github.com/iiSeymour/nbtop
author: @iiSeymour
license: MIT Copyright (c) 2015 Chris Seymour
"""

import os
import sys
import math
import curses
import argparse
import warnings
from time import sleep
from getpass import getpass
from curses import color_pair, wrapper
from os.path import splitext, basename

import requests
from psutil import process_iter
from six.moves.urllib.parse import quote
from simplejson.scanner import JSONDecodeError
from requests.exceptions import SSLError, ConnectionError, InvalidSchema

from nbtop.version import __version__


def notebook_process(process):
    """
    Is the process an IPython notebook process
    """
    if 'python' in process.name().lower():
        for arg in process.cmdline():
            if arg.endswith('.json') and '/kernel-' in arg:
                return True
    return False


def kernel(process):
    """
    Get the kernel id from a process
    """
    for arg in process.cmdline():
        if arg.endswith('.json') and '/kernel-' in arg:
            return splitext(basename(arg).replace('kernel-', ''))[0]


def human_readable_size(bytes):
    """
    Converts a size in bytes to a string containing a
    human-readable size in KB/MB/GB etc.
    """
    exp = int(math.log(bytes) / math.log(1024))
    units = "kMGTPE"
    pre = units[exp-1]
    return "%.1f %sB" % (bytes / (1024**exp), pre)


def process_stats_perc(proc):
    """
    Get process statistics for the percentage memory option
    """
    return proc.cpu_percent(), proc.memory_percent(), proc.create_time()


def process_stats_abs(proc):
    """
    Get process statistics for the absolute memory option
    """
    rss = proc.memory_info()[0]
    mem_usage = human_readable_size(rss)

    return proc.cpu_percent(), mem_usage, proc.create_time()


def process_state(args):
    """
    Get IPython notebook process information
    """
    procs = filter(notebook_process, process_iter())

    if args.abs:
        # Display memory usage in abs values
        process_stats_function = process_stats_abs
    else:
        # Display memory usage in %
        process_stats_function = process_stats_perc

    return {kernel(proc): process_stats_function(proc) for proc in procs}


def session_state(url, verify=True, session=None):
    """
    Query IPython notebook server for session information
    """
    path = 'api/sessions'
    try:
        if session is not None:
            response = session.get(os.path.join(url, path), verify=verify)
        else:
            response = requests.get(os.path.join(url, path), verify=verify)
    except SSLError:
        sys.stderr.write('certificate verification failed\n')
        sys.exit(1)
    except ConnectionError:
        sys.stderr.write('connection to %s failed!\n' % url)
        sys.exit(1)
    except InvalidSchema as e:
        sys.stderr.write('%s\n' % e)
        sys.exit(1)
    if response.status_code == 200:
        try:
            return response.json()
        except JSONDecodeError:
            pass
    return dict()


def notebook_name(notebook, args):
    """
    Get full notebook name with path
    """
    name = notebook['notebook']['path']
    try:
        name = os.path.join(name, notebook['notebook']['name'])
    except KeyError:
        pass
    if args.links:
        name = os.path.join(args.url, 'notebooks', quote(name))
    elif not args.extension:
        name = splitext(name)[0]
    return name


def shutdown_notebook(url, kernel, verify=True):
    """
    Shutdown an IPython notebook
    """
    response = requests.delete('%s/api/kernels/%s' % (url, kernel), verify=verify)
    return response.status_code


def simple_cli(args):
    while True:

        load = process_state(args)
        state = session_state(args.url, verify=args.insecure, session=args.session)

        os.system('clear')
        print('{:40}{:6}{:10}{}'.format('Kernel', 'CPU %', 'MEM %', 'Notebook'))

        for notebook in state:
            kernel = notebook['kernel']['id']
            name = notebook_name(notebook, args)

            cpu = str(round(load.get(kernel, (-99, -99))[0], 1))

            if args.abs:
                mem = load.get(kernel, ('-99.0', '-99.0'))[1]
            else:
                mem = str(round(load.get(kernel, (-99, -99))[1], 1))

            print('{0:40}{1:6}{2:7}   {3:}'.format(kernel, cpu, mem, name))

        sleep(args.rate)


def curses_wraps(fn):
    return lambda *args: wrapper(fn, *args)


@curses_wraps
def curses_cli(stdscr, args):

    stdscr.keypad(1)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_MAGENTA, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    curses.init_pair(7, curses.COLOR_RED, -1)

    KERN_COL = 1
    CPU__COL = 40
    MEM__COL = 48
    NAME_COL = 57

    max_h, max_w = stdscr.getmaxyx()

    offset = 3
    header = curses.newwin(offset, max_w)

    footer = curses.newwin(1, max_w, max_h - 1, 0)

    footer.addstr(0, 0, " s:", color_pair(3))
    footer.addstr(0, 3, "[shutdown notebook]")
    footer.addstr(0, max_w - 9, "q:", color_pair(3))
    footer.addstr(0, max_w - 7, "[quit]")
    footer.refresh()

    load = process_state(args)
    state = session_state(args.url, verify=args.insecure, session=args.session)

    running_notebooks = len(state)

    win = curses.newpad(running_notebooks + offset, max_w)
    win.nodelay(1)
    win.keypad(1)

    pad_offset = 0
    current_line = 1

    bottom = min(running_notebooks, max_h - offset - 1)

    while True:

        header.clear()
        header.addstr(0, 0, "NBTOP".center(max_w),  color_pair(5) | curses.A_STANDOUT)
        header.addstr(1, 0, args.url.center(max_w), color_pair(5) | curses.A_STANDOUT)
        header.addstr(2, KERN_COL, "Kernel", color_pair(3))
        header.addstr(2, CPU__COL, "CPU %",  color_pair(3))

        if args.abs:
            header.addstr(2, MEM__COL, "MEM",  color_pair(3))
        else:
            header.addstr(2, MEM__COL, "MEM %",  color_pair(3))

        header.addstr(2, NAME_COL, "Name",   color_pair(3))
        header.refresh()

        win.clear()

        load = process_state(args)
        state = session_state(args.url, verify=args.insecure, session=args.session)
        running_notebooks = len(state)

        kernels = [None, ]  # Pad for natural indexing

        for i, notebook in enumerate(state):

            kern = notebook['kernel']['id']
            name = notebook_name(notebook, args)
            cpu = str(round(load.get(kern, (-99, -99))[0], 1))

            if args.abs:
                mem = load.get(kern, ('-99.0', '-99.0'))[1]
            else:
                mem = str(round(load.get(kern, (-99, -99))[1], 1))

            kernels.append(kern)

            win.addstr(offset + i, KERN_COL, kern, color_pair(1))
            win.addstr(offset + i, CPU__COL, cpu,  color_pair(1))
            win.addstr(offset + i, MEM__COL, mem,  color_pair(1))
            win.addstr(offset + i, NAME_COL, name, color_pair(1))

        cmd = win.getch()

        if cmd == curses.KEY_DOWN and current_line < running_notebooks:
            current_line += 1
            if current_line > bottom and running_notebooks - bottom > pad_offset:
                pad_offset += 1
        elif cmd == curses.KEY_UP and current_line > 1:
            current_line -= 1
            if current_line - pad_offset == 0:
                pad_offset -= 1

        if running_notebooks > 0:
            win.chgat(current_line + offset - 1, 0, curses.A_REVERSE)
            win.refresh(offset + pad_offset, 0, offset, 0, max_h - 2, max_w)
        else:
            sleep(args.rate)

        if cmd in [ord('q'), ord('Q')]:
            sys.exit()
        if cmd in [ord('s'), ord('S')]:
            shutdown_notebook(args.url, kernels[current_line], verify=args.insecure)
            if current_line == running_notebooks or current_line == bottom:
                current_line -= 1


def main():

    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser()

    parser.add_argument('--debug', action="store_true", default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument("-r", "--rate", type=int, default=1,
                        help=argparse.SUPPRESS)
    parser.add_argument("-e", "--extension", action="store_false", default=True,
                        help="strip notebook extensions")
    parser.add_argument("-k", "--insecure", action="store_false", default=True,
                        help="no verification of SSL certificates")
    parser.add_argument("-a", "--abs", action="store_true", default=False,
                        help="show memory usage in absolute values (KB, MB, GB)")
    parser.add_argument("-l", "--links", action="store_true", default=False,
                        help="display full notebook URLs")
    parser.add_argument("-p", "--passwd", action="store_true", default=False,
                        help="prompt for notebook server password")
    parser.add_argument("--shutdown-all", action="store_true", default=False,
                        help="shutdown all notebooks on the server")
    parser.add_argument("-u", "--url", required=True,
                        help="IPython notebook server url")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    args = parser.parse_args()

    args.session = None

    if args.passwd:
        password = getpass("password for %s: " % args.url)

        login_url = os.path.join(args.url, 'login')
        args.session = requests.Session()
        resp = args.session.get(login_url)
        params = {
            '_xsrf': resp.cookies['_xsrf'],
            'password': password
        }

        response = args.session.post(login_url, verify=args.insecure, data=params)

        if response.url == login_url:
            sys.stderr.write("invalid password!\n")
            exit(1)

    state = session_state(args.url, verify=args.insecure, session=args.session)

    if args.shutdown_all:
        if len(state) == 0:
            sys.stderr.write("no notebook founds at %s\n" % args.url)
            exit(1)
        for notebook in state:
            sys.stdout.write("shutting down notebook: %-45s" % notebook_name(notebook, args))
            status = shutdown_notebook(args.url, notebook['kernel']['id'], verify=args.insecure)
            sys.stdout.write(" [%d]\n" % status)
        exit()

    try:
        if args.debug:
            simple_cli(args)
        else:
            curses_cli(args)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

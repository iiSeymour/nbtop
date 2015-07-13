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
import curses
import requests
import argparse
import warnings
from time import sleep
#from urllib import quote
from psutil import process_iter
from curses import color_pair, wrapper

from os.path import splitext, basename
from simplejson.scanner import JSONDecodeError
from six.moves.urllib.parse import quote
from requests.exceptions import SSLError, ConnectionError


def notebook_process(process):
    """
    Is the process an IPython notebook process
    """
    if process.name() == 'python':
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


def process_stats(proc):
    return proc.cpu_percent(), proc.memory_percent(), proc.create_time()


def process_state():
    """
    Get IPython notebook process information
    """
    procs = filter(notebook_process, process_iter())
    return {kernel(proc): process_stats(proc) for proc in procs}


def server_version(url, verify=True):
    """
    Get the IPython notebook server version
    """
    path = '/api'
    try:
        response = requests.get(url + path, verify=verify)
    except SSLError:
        sys.stderr.write('certificate verify failed\n')
        sys.exit(1)
    if response.status_code == 200:
        return 3
    else:
        return 2


def session_state(url, verify=True):
    """
    Query IPython notebook server for session information
    """
    path = '/api/sessions'
    try:
        response = requests.get(url + path, verify=verify)
    except SSLError:
        sys.stderr.write('certificate verification failed\n')
        sys.exit(1)
    except ConnectionError:
        sys.stderr.write('connection to %s failed!\n' % url)
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
    version = server_version(args.url, args.insecure)
    name = notebook['notebook']['path']
    if version == 2:
        name = os.path.join(name, notebook['notebook']['name'])
    if args.links:
        name = os.path.join(args.url, 'notebooks', quote(name))
    elif not args.extension:
        name = splitext(name)[0]
    return name


def shutdown_notebook(url, kernel, verify=True):
    """
    Shutdown an IPython notebook
    """
    requests.delete('%s/api/kernels/%s' % (url, kernel), verify=verify)


def simple_cli(args):
    while True:

        load = process_state()
        state = session_state(args.url, verify=args.insecure)

        os.system('clear')
        print('{:40}{:6}{:8}{}'.format('Kernel', 'CPU %', 'MEM %', 'Notebook'))

        for notebook in state:
            kernel = notebook['kernel']['id']
            name = notebook_name(notebook, args)
            print('{0:40}{1[0]:5.1f}{1[1]:6.1f}   {2:}'.format(kernel, load[kernel], name))

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

    load = process_state()
    state = session_state(args.url, verify=args.insecure)

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
        header.addstr(2, MEM__COL, "MEM %",  color_pair(3))
        header.addstr(2, NAME_COL, "Name",   color_pair(3))
        header.refresh()

        win.clear()

        load = process_state()
        state = session_state(args.url, verify=args.insecure)
        running_notebooks = len(state)

        kernels = [None, ]  # Pad for natural indexing

        for i, notebook in enumerate(state):

            kern = notebook['kernel']['id']
            name = notebook_name(notebook, args)
            cpu = str(round(load.get(kern, (-99, -99))[0], 1))
            cpu = cpu if float(cpu) < 100 else '100'
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
    parser.add_argument("-l", "--links", action="store_true", default=False,
                        help="display full notebook URLs")
    parser.add_argument("--shutdown-all", action="store_true", default=False,
                        help="shutdown all notebooks on the server")
    parser.add_argument("-u", "--url", required=True,
                        help="IPython notebook server url")

    args = parser.parse_args()
    state = session_state(args.url, verify=args.insecure)

    if args.shutdown_all:
        for notebook in state:
            shutdown_notebook(args.url, notebook['kernel']['id'], verify=args.insecure)
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

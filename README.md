nbtop
=====

IPython Notebook server monitor inspired by `htop`.

![screenshot](https://raw.githubusercontent.com/iiSeymour/nbtop/master/screenshot.png)

usage
=====

```bash
$ nbtop --help
usage: nbtop [-h] [-e] [-k] [-a] [-l] [-p] [--shutdown-all] -u URL [-v]

optional arguments:
  -h, --help         show this help message and exit
  -e, --extension    strip notebook extensions
  -k, --insecure     no verification of SSL certificates
  -a, --abs          show memory usage in absolute values (KB, MB, GB)
  -l, --links        display full notebook URLs
  -p, --passwd       prompt for notebook server password
  --shutdown-all     shutdown all notebooks on the server
  -u URL, --url URL  IPython notebook server url
  -v, --version      show program's version number and exit
```

installation
============

From pip:

    $ sudo pip install nbtop

From github:

    $ git clone https://github.com/iiSeymour/nbtop
    $ cd nbtop
    $ sudo python setup.py install

notes
=====

`nbtop` uses the kernel ids of running notebooks (queried from `/api/sessions`)
and matches them to running processes on the server. If `nbtop` is pointed at a
remote notebook server the memory and cpu percentage will be displayed as -99.

license
=======

MIT Copyright (c) 2015 - 2017 Chris Seymour

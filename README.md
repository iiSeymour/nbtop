nbtop
=====

IPython Notebook server monitor inspired by `htop`.

usage
=====

```bash
$ nbtop --help
usage: nbtop.py [-h] [-e] [-k] [-l] -u URL

optional arguments:
  -h, --help         show this help message and exit
  -e, --extension    strip notebook extensions
  -k, --insecure     no verification of SSL certificates
  -l, --links        display full notebook URLs
  -u URL, --url URL  IPython notebook server url
```

installation
============

From pip:

    $ pip install nbtop --user

From github:

    $ git clone https://github.com/iiSeymour/nbtop
    $ cd nbtop
    $ python setup.py install --user

notes
=====

`nbtop` uses the kernel ids of running notebooks (queried from `/api/sessions`)
and matches them to running processes on the server. If `nbtop` is pointed at a
remote notebook server the memory and cpu percentage will be displayed as -99.

license
=======

MIT Copyright (c) 2015 Chris Seymour

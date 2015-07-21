#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from nbtop.version import __version__

NAME = "nbtop"
DESCRIPTION = "resource monitor for IPython Notebook servers"
AUTHOR = "Chris Seymour"
AUTHOR_EMAIL = "chris.j.seymour@hotmail.com"
AUTHOR_TWITTER = "@iiSeymour"
URL = "https://github.com/iiSeymour/nbtop"

setup(
    name=NAME,
    version=__version__,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="MIT",
    url=URL,
    packages=['nbtop'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'nbtop=nbtop.main:main',
        ]
    },
    install_requires=[
        'requests>=2.7.0',
        'psutil>=2.2.1',
        'simplejson>=3.3.1',
        'six>=1.9.0'
    ]
)

#!/usr/bin/env python

import setuptools

setuptools.setup(
    name = 'aiopynoon',
    version = '0.0.1',
    license = 'MIT',
    description = 'Async Python library for Noon Home',
    author = 'Alistair Galbraith',
    author_email = 'github@alistairs.net',
    url = 'http://github.com/alistairg/aiopynoon',
    include_package_data=True,
	packages=setuptools.find_packages(),
    install_requires=['aiohttp'],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]

)
#!/usr/bin/env python
"""Installs SquareMap using distutils

Run:
	python setup.py install
to install the package from the source archive.
"""
import os
try:
    from setuptools import setup
except ImportError, err:
    from distutils.core import setup

version = [
    (line.split('=')[1]).strip().strip('"').strip("'")
    for line in open(os.path.join('squaremap','__init__.py'))
    if line.startswith( '__version__' )
][0]

if __name__ == "__main__":
	extraArguments = {
		'classifiers': [
			"""License :: OSI Approved :: BSD License""",
			"""Programming Language :: Python""",
			"""Topic :: Software Development :: Libraries :: Python Modules""",
			"""Intended Audience :: Developers""",
		],
		'keywords': 'wxPython,squaremap',
		'long_description' : """Hierarchic visualization control for wxPython 

Hierarchic data visualization control intended for use with 
structures where "parents" hold collections of weighted children.

Can be used for viewing sizes of directories on file-systems,
running-time of functions in profiling, or time spent on tasks 
in a time-tracking application.""",
		'platforms': ['Any'],
	}
	### Now the actual set up call
	setup (
		name = "SquareMap",
		version = version,
		url = "https://launchpad.net/squaremap",
		description = "Hierarchic data-visualisation control for wxPython",
		author = "Mike C. Fletcher",
		author_email = "mcfletch@vrplumber.com",
		license = "BSD",
		package_dir = {
			'squaremap':'squaremap',
		},
		packages = [
			'squaremap',
		],
		options = {
			'sdist':{'force_manifest':1,'formats':['gztar','zip'],},
		},
		zip_safe=False,
		**extraArguments
	)


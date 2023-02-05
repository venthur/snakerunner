# Changelog

## [3.0.0] - yyyy-mm-dd

* Renamed properly to Snakerunner
* Removed complicated guess-homedirectory logic and replaced it with
  pathlib.Path.home()
* Removed macshim.py
* Removed coldshot support


## Modifications since the Fork

* Python3 compatibility
* Updated to current wxpython version
* Merged `squaremap` library into the project
* Removed support for Meliae memory profiling
* Modernized setup.py
* Replaced SafeConfigParser with ConfigParser
* Replaced logger.warn with logger.warning

## [2.1.0] - 2023-02-05

* wxPython 4.2.0 compatibility
* Fixed deprecation warning
* Fixed top-level code environment
* Modernized `setup.py`: updated and fixed installation meta
* Modernized `version` control: rename `version.py` -> `vertion.txt`
* Added `requirements.txt`
* Added `.flake8` and fixed the code 
* Added `.editorconfig`
* Updated application resource

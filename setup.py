import os
from setuptools import setup, find_packages

version = [
    (line.split('=')[1]).strip().strip('"').strip("'")
    for line in open(os.path.join('runsnakerun', '__init__.py'))
    if line.startswith('__version__')
][0]

longdesc = """GUI Viewer for Python profiling runs
Provides explorability and overall visualization of the call tree
and package/module structures."""

setup(
    name='RunSnakeRun',
    version=version,
    author="Mike C. Fletcher",
    author_email="mcfletch@vrplumber.com",
    description="GUI Viewer for Python profiling runs",
    long_description=longdesc,
    keywords='profile,gui,wxPython,squaremap',
    url="https://github.com/venthur/snakerunner",
    packages=find_packages(exclude=['tests', "venv"]),
    install_requires=[
        'wxpython',
    ],
    extras_requires={"coldshot": ["coldshot"],  # Coldshot is a custom profiler that doesn't seem to exist anymore.
                     "windows": ["pywin32"]},
    license="BSD",
    zip_safe=False,
    entry_points={
        'gui_scripts': ['runsnake=runsnakerun.runsnake:main', ],
    },
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ],
    include_package_data=True,
    package_data={
        'runsnakerun': [
            'resources/*.png',
        ],
    },
)

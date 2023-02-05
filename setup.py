from setuptools import setup, find_packages
from os.path import abspath, dirname, join

_root = dirname(abspath(__file__))
_version = open(join(_root, 'snakerunner', 'version.txt'), 'r').read()
_long_description = open(join(_root, 'README.md'), 'r').read()
_install_requires = open(join(_root, 'requirements.txt'), 'r').readlines()

setup(
    name='snakerunner',
    version=_version,
    author="Bastian Venthur",
    author_email="venthur@debian.org",
    description="GUI Viewer for Python profiling runs",
    long_description=_long_description,
    keywords='profile,gui,wxPython,squaremap',
    url="https://github.com/venthur/snakerunner",
    packages=find_packages(exclude=['tests', "venv"]),
    install_requires=_install_requires,
    license="BSD",
    zip_safe=False,
    entry_points={
        'gui_scripts': ['runsnake=snakerunner.snakerunner:main',
                        'snakerunner=snakerunner.snakerunner:main'],
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

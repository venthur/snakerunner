from setuptools import setup, find_packages

meta = {}
exec(open('./snakerunner/version.py').read(), meta)
meta['long_description'] = open('./README.md').read()

setup(
    name='snakerunner',
    version=meta['__version__'],
    author="Bastian Venthur",
    author_email="venthur@debian.org",
    description="GUI Viewer for Python profiling runs",
    long_description=meta['long_description'],
    keywords='profile,gui,wxPython,squaremap',
    url="https://github.com/venthur/snakerunner",
    packages=find_packages(exclude=['tests', "venv"]),
    install_requires=[
        'wxpython',
    ],
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

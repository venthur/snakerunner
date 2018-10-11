#! /usr/bin/env python
"""Creates hotshot and cProfile sample files"""
import time
import cProfile
import hotshot
from subpackage.timewaster import r


def x():
    print('x')
    y()
    z()
    from . import big_import  # noqa
    a()
    r()


def y():
    print('y')
    for i in range(2500):
        int(i) ** i
    time.sleep(0.25)
    z()


def z():
    print('z')
    time.sleep(0.1)
    a()


def a(count=5):
    print('a', count)
    if count:
        time.sleep(0.05)
        return a(count - 1)


if __name__ == "__main__":
    command = '''x()'''
    profiler = hotshot.Profile(
        "hotshot.profile", lineevents=True, linetimings=True
    )
    profiler.runctx(command, globals(), locals())
    print(dir(profiler))
    profiler.close()
    print('hotshot line events', profiler.lineevents)

    profiler = cProfile.Profile(subcalls=True)
    profiler.runctx(command, globals(), locals())
    stats = profiler.getstats()
    profiler.dump_stats('cprofile.profile')

    try:
        import line_profiler
    except ImportError as err:
        pass
    else:
        profiler = line_profiler.LineProfiler()
#        profiler.add_function( x )
        for func in (a, x, y, z):
            profiler.add_function(func)
        profiler.runctx(command, globals(), locals())
        profiler.dump_stats('line_profiler.profile')

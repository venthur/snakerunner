"""Module to load cProfile/profile records as a tree of records"""
import pstats
import os
import logging
from gettext import gettext as _

log = logging.getLogger(__name__)

TREE_CALLS, TREE_FILES = 0, 1


class PStatsLoader(object):
    """Load profiler statistics from PStats (cProfile) files"""

    def __init__(self, *filenames):
        self.filename = filenames
        self.rows = {}
        self.roots = {}
        self.location_rows = {}
        self.stats = pstats.Stats(*filenames)
        self.tree = self.load(self.stats.stats)
        self.location_tree = self.load_location()

    ROOTS = ['functions', 'location']

    def get_root(self, key):
        """Retrieve a given declared root by root-type-key"""
        if key not in self.roots:
            function = getattr(self, 'load_%s' % (key,))()
            self.roots[key] = function
        return self.roots[key]

    def get_rows(self, key):
        """Get the set of rows for the type-key"""
        if key not in self.roots:
            self.get_root(key)
        if key == 'location':
            return self.location_rows
        else:
            return self.rows

    def get_adapter(self, key):
        from snakerunner import pstatsadapter
        if key == 'functions':
            return pstatsadapter.PStatsAdapter()
        elif key == 'location':
            return pstatsadapter.DirectoryViewAdapter()
        else:
            raise KeyError("""Unknown root type %s""" % (key, ))

    def load(self, stats):
        """Build a squaremap-compatible model from a pstats class"""
        rows = self.rows
        for func, raw in stats.items():
            try:
                rows[func] = row = PStatRow(func, raw)
            except ValueError:
                log.info('Null row: %s', func)
        for row in rows.values():
            row.weave(rows)
        return self.find_root(rows)

    def load_functions(self):
        """Load function records from the pstats file"""
        return self.load()

    def find_root(self, rows):
        """Attempt to find/create a reasonable root node from list/set of rows

        rows -- key: PStatRow mapping

        TODO: still need more robustness here, particularly in the case of
        threaded programs.  Should be tracing back each row to root, breaking
        cycles by sorting on cumulative time, and then collecting the traced
        roots (or, if they are all on the same root, use that).
        """
        maxes = sorted(list(rows.values()), key=lambda x: x.cumulative)
        if not maxes:
            raise RuntimeError("""Null results!""")
        root = maxes[-1]
        roots = [root]
        for key, value in rows.items():
            if not value.parents:
                log.debug('Found node root: %s', value)
                if value not in roots:
                    roots.append(value)
        if len(roots) > 1:
            root = PStatGroup(
                directory='*',
                filename='*',
                name=_("<profiling run>"),
                children=roots,
            )
            root.finalize()
            self.rows[root.key] = root
        self.roots['functions'] = root
        return root

    def load_location(self):
        """Load the location root record (loading regular records if necessary)"""
        if not self.rows:
            self.load()
        return self._load_location()

    def _load_location(self):
        """Build a squaremap-compatible model for location-based hierarchy"""
        directories = {}
        files = {}
        root = PStatLocation('/', 'PYTHONPATH')
        self.location_rows = self.rows.copy()
        for child in self.rows.values():
            current = directories.get(child.directory)
            directory, filename = child.directory, child.filename
            if current is None:
                if directory == '':
                    current = root
                else:
                    current = PStatLocation(directory, '')
                    self.location_rows[current.key] = current
                directories[directory] = current
            if filename == '~':
                filename = '<built-in>'
            file_current = files.get((directory, filename))
            if file_current is None:
                file_current = PStatLocation(directory, filename)
                self.location_rows[file_current.key] = file_current
                files[(directory, filename)] = file_current
                current.children.append(file_current)
            file_current.children.append(child)
        # now link the directories...
        for key, value in directories.items():
            if value is root:
                continue
            found = False
            while key:
                new_key, rest = os.path.split(key)
                if new_key == key:
                    break
                key = new_key
                parent = directories.get(key)
                if parent:
                    if value is not parent:
                        parent.children.append(value)
                        found = True
                        break
            if not found:
                root.children.append(value)
        # lastly, finalize all of the directory records...
        root.finalize()
        return root


class BaseStat(object):
    def recursive_distinct(self, already_done=None, attribute='children'):
        if already_done is None:
            already_done = {}
        for child in getattr(self, attribute, ()):
            if child not in already_done:
                already_done[child] = True
                yield child
                for descendent in child.recursive_distinct(already_done=already_done, attribute=attribute):
                    yield descendent

    def descendants(self):
        return list(self.recursive_distinct(attribute='children'))

    def ancestors(self):
        return list(self.recursive_distinct(attribute='parents'))


class PStatRow(BaseStat):
    """Simulates a HotShot profiler record using PStats module"""

    def __init__(self, key, raw):
        self.children = []
        self.parents = []
        file, line, func = self.key = key
        try:
            dirname, basename = os.path.dirname(file), os.path.basename(file)
        except ValueError:
            dirname = ''
            basename = file
        nc, cc, tt, ct, callers = raw
        if nc == cc == tt == ct == 0:
            raise ValueError('Null stats row')
        (
            self.calls, self.recursive, self.local, self.localPer,
            self.cumulative, self.cumulativePer, self.directory,
            self.filename, self.name, self.lineno
        ) = (
            nc,
            cc,
            tt,
            tt/(cc or 0.00000000000001),
            ct,
            ct/(nc or 0.00000000000001),
            dirname,
            basename,
            func,
            line,
        )
        self.callers = callers

    def __repr__(self):
        return 'PStatRow( %r,%r,%r,%r, %s )' % (self.directory, self.filename, self.lineno, self.name, len(self.children))

    def add_child(self, child):
        self.children.append(child)

    def weave(self, rows):
        for caller, data in self.callers.items():
            # data is (cc,nc,tt,ct)
            parent = rows.get(caller)
            if parent:
                self.parents.append(parent)
                parent.children.append(self)

    def child_cumulative_time(self, child):
        total = self.cumulative
        if total:
            try:
                (cc, nc, tt, ct) = child.callers[self.key]
            except TypeError:
                ct = child.callers[self.key]
            return float(ct)/total
        return 0


class PStatGroup(BaseStat):
    """A node/record that holds a group of children but isn't a raw-record based group"""
    # if LOCAL_ONLY then only take the raw-record's local values, not cumulative values
    LOCAL_ONLY = False

    def __init__(self, directory='', filename='', name='', children=None, local_children=None, tree=TREE_CALLS):
        self.directory = directory
        self.filename = filename
        self.name = ''
        self.key = (directory, filename, name)
        self.children = children or []
        self.parents = []
        self.local_children = local_children or []
        self.tree = tree

    def __repr__(self):
        return '%s( %r,%r,%s )' % (self.__class__.__name__, self.directory, self.filename, self.name)

    def finalize(self, already_done=None):
        """Finalize our values (recursively) taken from our children"""
        if already_done is None:
            already_done = {}
        if self in already_done:
            return True
        already_done[self] = True
        self.filter_children()
        children = self.children
        for child in children:
            if hasattr(child, 'finalize'):
                child.finalize(already_done)
            child.parents.append(self)
        self.calculate_totals(self.children, self.local_children)

    def filter_children(self):
        """Filter our children into regular and local children sets (if appropriate)"""

    def calculate_totals(self, children, local_children=None):
        """Calculate our cumulative totals from children and/or local children"""
        for field, local_field in (('recursive', 'calls'), ('cumulative', 'local')):
            values = []
            for child in children:
                if isinstance(child, PStatGroup) or not self.LOCAL_ONLY:
                    values.append(getattr(child, field, 0))
                elif isinstance(child, PStatRow) and self.LOCAL_ONLY:
                    values.append(getattr(child, local_field, 0))
            value = sum(values)
            setattr(self, field, value)
        if self.recursive:
            self.cumulativePer = self.cumulative/float(self.recursive)
        else:
            self.recursive = 0
        if local_children:
            for field in ('local', 'calls'):
                value = sum([getattr(child, field, 0) for child in children])
                setattr(self, field, value)
            if self.calls:
                self.localPer = self.local / self.calls
        else:
            self.local = 0
            self.calls = 0
            self.localPer = 0


class PStatLocation(PStatGroup):
    """A row that represents a hierarchic structure other than call-patterns

    This is used to create a file-based hierarchy for the views

    Children with the name <module> are our "empty" space,
    our totals are otherwise just the sum of our children.
    """
    LOCAL_ONLY = True

    def __init__(self, directory, filename, tree=TREE_FILES):
        super(PStatLocation, self).__init__(directory=directory,
                                            filename=filename, name='package', tree=tree)

    def filter_children(self):
        """Filter our children into regular and local children sets"""
        real_children = []
        for child in self.children:
            if child.name == '<module>':
                self.local_children.append(child)
            else:
                real_children.append(child)
        self.children = real_children


if __name__ == "__main__":
    import sys
    p = PStatsLoader(sys.argv[1])
    assert p.tree
    print(p.tree)

"""Manages scanning of data files.

Files containing the same variables and having the same filenames are
regrouped into a same Filegroup.
"""

import logging

import os
import re
from types import MethodType

import data_loader.coord_scan as dlcs
from data_loader.accessor import Accessor


log = logging.getLogger(__name__)


class FilegroupScan():
    """An ensemble of files.

    Files which share the same variables, and filename structure.
    Class manages the scanning part of filegroups.

    Parameters
    ----------
    root: str
        Root data directory containing all files.
    contains: List[str]
        Variables contained in this filegroup.
    db: DataBase or subclass
        Parent database.
    coords: List[ List[Coord, shared: bool] ]
        Parent coordinates objects, and a bool indicating if the coordinate
        is shared accross files.
    vi: VariablesInfo
        Global VariablesInfo instance.

    Attributes
    ----------
    root: str
        Root data directory containing all files.
    contains: List[str]
        Variables contained in this filegroup.
    db: DataBase or subclass
        Parent database.
    cs: Dict[name: str, CoordScan or subclass]
        Dictionnary of scanning coordinates,
        each dynamically inheriting from its
        parent Coord.
    pregex: str
        Pre-regex.
    regex: str
        Regex.
    segments: List[str]
        Fragments of filename used for reconstruction,
        pair indices are replaced with matches.
    vi: VariablesInfo
        Global VariablesInfo instance.
    scan_attr: bool
        If the variables attributes have to be scanned.
    """

    def __init__(self, root, contains, db, coords, vi):
        self.root = root
        self.contains = contains
        self.db = db

        self.found_file = False
        self.n_matcher = 0
        self.segments = []

        self.regex = ""
        self.pregex = ""

        self.vi = vi
        self.scan_attr = False

        self.make_coord_scan(coords)

        self.acs = Accessor()

    def __str__(self):
        s = [self.__class__.__name__]
        s.append("Contains: %s" % ', '.join(self.contains))

        s.append("Root Directory: %s" % self.root)
        s.append("Pre-regex: %s" % self.pregex)
        s.append("Regex: %s" % self.regex)
        s.append('')

        s.append("Coordinates for scan:")
        for name, cs in self.iter_scan().items():
            s1 = ["\t%s " % name]
            s1.append(["(in)", "(shared)"][cs.shared])
            if cs.scanned:
                s1.append(" found %d values, kept %d" % (len(cs.values), cs.size))
            s.append(''.join(s1))
        return '\n'.join(s)

    def make_coord_scan(self, coords):
        """Add CoordScan objects.

        Each CoordScan is dynamically rebased
        from its parent Coord.
        """
        self.cs = {}
        for coord, shared in coords:
            cs = dlcs.get_coordscan(self, coord, shared)
            self.cs.update({coord.name: cs})

    def iter_shared(self, shared=None):
        """Iter through CoordScan objects.

        Parameters
        ----------
        shared: bool, optional
            To iterate only shared coordinates (shared=True),
            or only in coordinates (shared=False).
            If left to None, iter all coordinates.
        """
        cs = {}
        for name, c in self.cs.items():
            add = False
            if shared is None:
                add = True
            else:
                add = (c.shared == shared)

            if add:
                cs[name] = c

        return cs

    def iter_scan(self, scan=None):
        """Iter through CoordScan objects.

        Parameters
        ----------
        scan: bool, optional
            To iterate only scannable coordinates (scan=True),
            or only not scannable coordinates (scan=False).
            If left to None, iter all coordinates.
        """
        cs = {}
        for name, c in self.cs.items():
            add = False
            if scan is None:
                add = True
            elif scan == "scannable":
                add = len(c.scan) > 0
            else:
                add = scan in c.scan

            if add:
                cs[name] = c

        return cs

    def add_scan_regex(self, pregex, replacements):
        """Specify the pre-regex.

        Create a proper regex from the pre-regex.
        Find the matchers: replace them by the appropriate regex,
        store segments for easy replacement by the matches later.

        Parameters
        ----------
        pregex: str
            Pre-regex.
        replacements: Dict
            Dictionnary of matchers to be replaced by a constant.
            The keys must match a matcher in the pre-regex.

        Example
        -------
        >>> pregex = "%(prefix)_%(time:value)"
        ... replacements = {"prefix": "SST"}
        """
        pregex = pregex.strip()

        for k, z in replacements.items():
            pregex = pregex.replace("%({:s})".format(k), z)

        m = self.scan_pregex(pregex)

        # Separations between segments
        idx = 0
        regex = pregex
        for idx, match in enumerate(m):
            matcher = dlcs.Matcher(match, idx)
            self.cs[matcher.coord].add_matcher(matcher)
            regex = regex.replace(match.group(), '(' + matcher.rgx + ')')

        self.n_matcher = idx + 1
        self.regex = regex
        self.pregex = pregex

    def scan_pregex(self, pregex):
        """Scan pregex for matchers."""
        regex = r"%\(([a-zA-Z]*):([a-zA-Z]*)(?P<cus>:custom=)?((?(cus)[^:]+:))(:?dummy)?\)"
        m = re.finditer(regex, pregex)
        return m

    def find_segments(self, m):
        """Find segments in filename.

        Store result.

        Parameters
        ----------
        m: re.match
            Match of the pre-regex to find matchers.
            Output of FilegroupScan.scan_pregex()
        """
        sep = [0]
        n = len(m.groups())
        for i in range(n):
            sep.append(m.start(i+1))
            sep.append(m.end(i+1))

        s = m.string
        self.segments = [s[i:j]
                         for i, j in zip(sep, sep[1:]+[None])]

    def open_file(self, filename, mode='r', log_lvl='info'):
        """Open a file.

        Parameters
        ----------
        filename: str
            File to open.
        mode: str
            Mode for opening (read only, replace, append, ...)
        log_lvl: {'debug', 'info', 'warning'}
            Level to log the opening at.
        """
        raise NotImplementedError

    def close_file(self, file):
        """Close file.

        Parameters
        ----------
        file:
            File object.
        """
        raise NotImplementedError

    def is_to_open(self):
        """Return if the current file has to be opened."""
        to_open = False
        for cs in self.iter_scan("scannable").values():
            to_open = to_open or cs.is_to_open()
        to_open = to_open or self.scan_attr
        return to_open

    def scan_file(self, filename: str):
        """Scan a single filename.

        Match filename against regex.
        If first match, retrieve segments.
        If needed, open file.
        If not already, scan attributes.
        Scan per coordinate.
        Close file.
        """
        m = re.match(self.regex, filename)

        filename = os.path.join(self.root, filename)

        # Discard completely non matching files
        if m is None:
            return

        self.found_file = True

        if len(self.segments) == 0:
            self.find_segments(m)

        file = None
        if self.is_to_open():
            file = self.open_file(filename, mode='r', log_lvl='debug')

        try:
            if self.scan_attr:
                infos = self.scan_attributes(file, self.contains) #pylint: disable=not-callable
                for var, info in infos.items():
                    log.debug("Found for '%s' attributes %s", var, list(info.keys()))
                    self.vi.add_attrs_per_variable(var, info)
                self.scan_attr = False

            for cs in self.iter_scan("scannable").values():
                cs.scan_file(m, file)
        except:
            self.close_file(file)
            raise
        else:
            if file is not None:
                self.close_file(file)

    def find_files(self):
        """Find files to scan in root directory.

        Uses os.walk.
        Sort files alphabetically

        Raises
        ------
        RuntimeError:
            If no files are found.
        """
        # Using a generator should fast things up even though
        # less readable
        files = [os.path.relpath(os.path.join(root, file), self.root)
                 for root, _, files in os.walk(self.root)
                 for file in files]
        files.sort()

        if len(files) == 0:
            raise RuntimeError("No files were found in %s" % self.root)

        log.debug("Found %s files in %s", len(files), self.root)

        return files

    def scan_files(self):
        """Scan files.

        Raises
        ------
        NameError
            If no file were found.
        ValueError
            If no values were detected.
        """
        files = self.find_files()
        for file in files:
            self.scan_file(file)

        if not self.found_file:
            raise NameError("No file matching the regex found ({0}, regex={1})".format(
                self.contains, self.regex))

        for cs in self.iter_scan("scannable").values():
            if len(cs.values) == 0:
                raise ValueError("No values detected ({0}, {1})".format(
                    cs.name, self.contains))
            cs.sort_values()
            cs.update_values(cs.values)

    def set_scan_attributes_func(self, func):
        """Set function for scanning variables attributes.

        Parameters
        ----------
        func: Callable[[file, variables: List[str]], [Dict]]
            Function that recovers variables attributes in file.
            See FilegroupScan.scan_attributes for a better description
            of the function interface.
        """
        self.scan_attr = True
        self.scan_attributes = MethodType(func, self)

    def scan_attributes(self, file, variables): #pylint: disable=method-hidden
        """Scan attributes in file for specified variables.

        Parameters
        ----------
        file:
            Object to access file.
            The file is already opened by FilegroupScan.open_file().
        variables: List[str]
            Variables to look for attributes.

        Returns
        -------
        attributes: Dict[attribute: str, Dict[variable: str, value: Any]]
            Attributes found: {'attribute name': {'variable name': Any}}
        """
        raise NotImplementedError("scan_attribute was not set for (%s)" % self.contains)

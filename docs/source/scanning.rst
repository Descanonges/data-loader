
.. currentmodule:: tomate

Scanning
========

At its creation, the database object looks into the available files on disk in a
process called scanning.
It looks inside the files and at their filenames to find how the data is
arranged.
It can find the values of the coordinates, and their placement in the files, as
well as other metadata.
The scanning is done independently in each filegroup.


Scanning Coordinates
--------------------

This section title means we are scanning coordinates, and have coordinates for
scanning: :class:`CoordScan<filegroup.coord_scan.CoordScan>` objects, often
abbrievated CS.
Each CoordScan has a parent :class:`Coord<coordinates.coord.Coord>` object.
The CS is dynamically subclassed from the parent Coord class at runtime.
So the user can use any subclass of coordinate he defined and the corresponding
CoordScan will have access to its methods and attributes.


Generalites
^^^^^^^^^^^

They are two types of dimension (and thus of CS).

* Some dimensions are found entirely in each file: they are 'in',
* others can be scattered accross different files: they are 'shared'.

In-coordinates are also assumed to be arranged in the same way for all files
(same values, same indexing).
For example, in a dataset of the sea surface temperature with an image per date
per file, the latitude and longitude will be 'in' and the temperature 'shared'.
There could also be more than one date per file, for instance one file for each
month with daily images.

.. note::

   keep in mind that all coordinates are independent.

The CS must find various **elements**: the coordinates values, the index in the
file for each value, and if the CS is shared, the file that contains this value.
For each variable, the dimensions it depends upon must also be retrieved.
All those elements are indexed on the coordinate values, so when we ask for the
i\ :sup:`th` value of a coordinate, we take the i\ :sup:`th` file, and the i\
:sup:`th` in-file index to know where to look in that file.
The fact that everything is indexed on coordinates values, means that
coordinates scanned from files will always have values in growing order.

Some dimensions might not be represented inside the file, for instance in the
first example above the files might not contain a time dimension.
In that case, the in-file index should be `None`. This is then handled
appropriately by the filegroup loading methods.

Filenames are stored in full. Rather, the matches from the pre-regex
corresponding to that coordinate are kept for each coordinate value.
This avoid storing an excessive number of long filenames, especially if there
are multiple shared coordinates.
With the matches from all the shared coordinates, we can reconstruct the
filename, by replacing the matchers in the pre-regex.


Setting up scanning coordinates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The user has to indicate for each filegroup the scanning coordinates, and some
information about them. This is done with a series of
:class:`CoordScanSpec<filegroup.spec.CoordScanSpec>` objects, accessible from
the constructor as `Constructor.CSS`.
The information to enter to a CSS are:

- the **parent** coordinate object or name,
- if it is **shared** (`True` or `'shared'`) or in (`False` or `'in'`),
- and the **name** with which the dimension can be found in file.

The last two argument are optional and default to 'in' and to the same name as
the parent coordinate.

Following the same example as above::

    coord_fg = [cstr.CSS('lat', name='latitude'),
                cstr.CSS('lon', name='longitude'),
                cstr.CSS('time', 'shared')]
    cstr.add_filegroup(FilegroupNetCDF, coord_fg)

Note the order in which the scanning coordinates are specified dictates the
order in which they will be scanned.

To do this automatically: see below.


Scanning coordinates objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default the user create :class:`Coord<coordinates.coord.Coord>` objects,
and specify CoordScan objects for each filegroups.
This allows for a lot of flexibility in the choice the Coord subclass,
coordinate name, etc. But this can become cumbersome when a lot of dimensions
are present in the file.

It is possible to scan for coordinates object automatically. In order to do
this, the user has to call the function :func:`Constructor.scan_dimensions
<constructor.Constructor.scan_coordinates_objects>`, and supply a function that
will do the scanning (ex: :func:`scan_library.nc.scan_coordinates_objects`).
At this point, the current filegroup will try to find the first file of this
filegroup and will look into it. This means that the filegroups files must be
setup (either by having a regex set, or by using
:func:`Constructor.set_file_override<constructor.Constructor.set_file_override>`).

Found coordinates objects will be added to the filegroup and constructor (if
they are not already present). Note this will only add 'in' coordinates,
shared coordinates should be indicated as usual.


Variables Coordinates
^^^^^^^^^^^^^^^^^^^^^

Variables are treated as coordinates when scanning, with some specificities.

First, the user does not need to create a
:class:`Variables<coordinates.variables.Variables>` object, it is automatically
added by the constructor.
The variable dimension can also be omitted when adding a filegroup to the
constructor, it will automatically be added, 'in' by default.

The variables values still need to be set, either by scanning them like any
other coordinate, or setting it manully using
:func:`constructor.Constructor.set_variables_elements`.
This function takes as argument
:class:`VariablesSpec<filegroup.spec.VariableSpec>`, accessible from the
constructor as `Constructor.VS`.

Example::

    cstr.set_variables_elements(cstr.VS('SST', 'sea_surface_temperature',
                                        ['time', 'lat', 'lon']))



Units conversion
^^^^^^^^^^^^^^^^

The coordinates values found by scanning might not have the desired units.
One can rely one the
:func:`Coord.change_units_other<coordinates.coord.Coord.change_units>` default
function or use a custom function instead by using
:func:`Constructor.set_coords_units_conversion
<constructor.Constructor.set_coords_units_conversion>`.

This conversion will only happen if the 'units' attribute on the CoordScan
and its parent Coord are defined and different.
By default the CoordScan object will inherit the units of its parent Coord, but
this might not reflect the units inside the files!
You can set the CoordScan units by scanning attributes, or by accessing it::

  cstr.current_fg.cs['time'].units = '...'

The conversion will happen once all files were scanned.


.. currentmodule:: tomate.constructor

Multiple filegroups
-------------------

Where's the fun in having only one filegroup ? The 'fun' part is that with
multiple filegroups, a choice has to be made in what coordinates points should
be kept.

When all filegroups have finished scanning, the database object will compile
values found for each coordinate. This will dictate the range of the 'available'
scope.
By default, only coordinates points common to all filegroups are taken. The
variables dimension is an exception to this.
If in some filegroup a coordinate must be sliced, a warning will be emitted.

Duplicate coordinates points (variables and coordinates values are identical in
two different filegroups) are not supported.
To avoid those, one can select parts of the CS to take in each filegroup,
either by index or value (see :func:`Constructor.set_coord_selection`
and :func:`Constructor.set_coord_selection_by_value`).

By setting the flag :attr:`Constructor.allow_advanced` to `True`, one unlocks
some even funnier possibilities.
This allows to retain all found values, not only values common accross
filegroups.
Duplicates are still not supported.
This renders possible some nice features, like having a variable split accross
two filegroups. For instance multiple filegroups containing different spatial or
temporal ranges of a same variable.

But with great power comes great responsabilites. Advanced compiling can lead to
unforeseen circumstances.
It allows to have multiple coordinates grid at the same time, which could be
unwanted. It also allows non-convex data grids: a variable could be available at
a location where others are not for instance. By loading all variables at this
location, parts of the data array would be allocated but left untouched, without
warnings being emitted.
To use with some caution.

.. currentmodule:: tomate.coordinates.coord

Float comparison
^^^^^^^^^^^^^^^^

Having multiple filegroups add the need to compare coordinates values accross
filegroups. This implies float comparison. Some of it is done using
:func:`Coord.get_index_exact`, which uses a the :attr:`Coord.float_comparison`
threshold, by default 1e-9. It can be changed manually for each CoordScan
object.

When aggregating values from all filegroups, we need to remove duplicates. For
that comparison, the maximum of all :attr:`Coord.float_comparison` for that
dimension is used. The value used is logged as debug.

.. currentmodule:: tomate


Finding coordinates elements
----------------------------

Coordinate elements (ie values, in-file indices, variables dimensions) can be
obtained by :ref:`setting them manually<Setting elements manually>`, or by using
user-defined functions to :ref:`scan a filename<Scanning filename>` or to
:ref:`scan inside a file<Scanning in file>`.

To use functions the user must add a series of scanning functions or
:class:`'scanners'<filegroup.scanner.ScannerCS>`.
A scanner is a wrapper around a function that adds some features described
below.
You can set any number of functions that will be executed in the order you added
them to the filegroup.
Each can extract any combination of elements.
One can specify / override which elements are returned by a function / scanner,
and eventually restrain what elements are kept from thoses returned.

For each file, the coordinates values scanned so far are passed as argument to
each function. And previously scanned elements can be found in the CoordScan
object itself, that is passed as well.
So, for instance with monthly files, one could first find the year and month in
the filename, and the day of the month in the file. It would combine both to
create the whole date.

In-coordinates scan only one file, the first one found.
Shared coordinates scan all the files available.


Scanning in file
^^^^^^^^^^^^^^^^

A scanning function is added by
:func:`Constructor.add_scan_in_file<constructor.Constructor.add_scan_in_file>`.
The function should receive a CoordScan object, a file object, and values
scanned so far.

The file object is a handle for whatever file format is needed. It is returned
by the Filegroup
:func:`open_file<filegroup.filegroup_scan.FilegroupScan.open_file>` method.
All exception handling (and closing the file appropriately) is done by Tomate.

One should look into :func:`filegroup.scanner.scan_in_file_default` for a better
description of the function signature.
:mod:`tomate.scan_library` contains some examples.


Scanning filename
^^^^^^^^^^^^^^^^^

The filename can also be scanned, as sometimes it is the sole source of
information for a coordinate.
This is done via a pre-regex, a regular expression with added features that
specifies how the filename is constructed.

One cannot just use a regular expression when having shared dimensions, as it
will be replaced by its match as found in the first file and then considered
constant.
For example, if we have daily files 'sst_2003-01-01.nc' with the date changing
for each file. We could use the regex `sst_.*\.nc`, which would match correctly
all files, but the program would then consider that *all* filenames are
'sst_2003-01-01.nc'

Instead, we must specify what part of the filename varies, and along which
dimension / coordinate.
To this end, we use :class:`matchers<filegroup.matcher.Matcher>`. This is a part
of the pre-regex, enclosed in parenthesis and preceded by a `%`. It specifies
the coordinate name an element.
The element dictate the regex that will be used for that matcher, and how it
will eventually be treated by the filename scanning function.

Various elements are already coded. Elements for dates and times follow
`strftime <https://linux.die.net/man/3/strftime>`__ format specifications.
For instance the element 'Y' designate a year. It will be replaced by a regex
searching for 4 digits and :class:`scan_library.general.get_date_from_matches`
will use this to create a date.


+--------------+--------------+-------------------+
| Element name | Regex        |                   |
+--------------+--------------+-------------------+
| idx          | \\d*         | Index             |
+--------------+--------------+-------------------+
| text         | [a-zA-Z]*    | Letters           |
+--------------+--------------+-------------------+
| char         | \\S*         | Character         |
+--------------+--------------+-------------------+
| x            | %Y%m%d       | Date (YYYYMMDD)   |
+--------------+--------------+-------------------+
| X            | %H%M%S       | Time (HHMMSS)     |
+--------------+--------------+-------------------+
| Y            | \\d\\d\\d\\d | Year (YYYY)       |
+--------------+--------------+-------------------+
| m            | \\d\\d       | Month (MM)        |
+--------------+--------------+-------------------+
| d            | \\d\\d       | Day of month (DD) |
+--------------+--------------+-------------------+
| j            | \\d\\d\\d    | Day of year (DDD) |
+--------------+--------------+-------------------+
| B            | [a-zA-Z]*    | Month name        |
+--------------+--------------+-------------------+
| H            | \\d\\d       | Hour 24 (HH)      |
+--------------+--------------+-------------------+
| M            | \\d\\d       | Minute (MM)       |
+--------------+--------------+-------------------+
| S            | \\d\\d       | Seconds (SS)      |
+--------------+--------------+-------------------+


Single letters preceded by a percentage in the matcher regex will recursively be
replaced by the corresponding regex.
So `%X` will be replaced by `%H%M%S`. This still counts as a single matcher and
its element name will not be changed.
A percentage character can be escaped by another percentage (`%%`)

All the use cases are not covered, and one might want to use a specific regex in
place of the matcher::

  sst_%(time:Y:custom=\d\d:)-%(time:m)-%(time:d)

.. warning::

   The custom regex must be terminated with a colon `:`.

The filename can comport varying part which are not detrimental to the
extraction of coordinate values. They still have to be specified, but one can
append the 'dummy' keyword to the matcher to make clear that this information is
to be discarded. This is usefull for instance when dealing with filenames that
specify the averaging boundaries::

  sst_%(time:Y)-%(time:Y:dummy)
  sst_%(time:Y)-%(time:Y:custom=\d\d\d\d:dummy)

More use cases are presented in the :doc:`tutorial` and `/examples
<https://github.com/Descanonge/tomate/blob/master/examples>`__.

Each scanned filename is matched again the regex constructed from the pre-regex.
The matches are temporarily stored in the matchers of the corresponding
coordinates.
Again, the CoordScan calls a user-defined function set with
:func:`Constructor.add_scan_filename<constructor.Constructor.add_scan_filename>`.
The function receives a Coordscan instance, and values previously scanned from
the same file.

One should look into :func:`filegroup.scanner.scan_filename_default` for a
better description of the function signature. :mod:`tomate.scan_library`
contains some examples.

It is possible to avoid the scanning of files by using :func:`Constructor.set_file_override<constructor.Constructor.set_file_override>`.
It allows to set a single filename, in which case the regex can be left empty,
or a list of filenames, in which case a regex still has to be setup (it just
avoids the process of exploring the whole file tree from the filegroup root).

.. warning::

   Tomate will recursively explore the filegroup root directory and store
   the names of **all** the files in it, up to a depth of 3 directories.
   This limit can be changed by tweaking `FilegroupScan.MAX_DEPTH_SCAN`.

.. currentmodule:: tomate.constructor

Setting elements manually
^^^^^^^^^^^^^^^^^^^^^^^^^

This whole process can be overlooked or completed by setting manually various
coordinates elements.
For shared coordinates the scanning of values is recommended though as setting
file matches manually is cumbersome and prone to errors.

Elements can be set very simply using :func:`Constructor.set_elements_manually`.
This is incompatible with any scanning function.

Both scanning function and elements set manually are compatible with setting
constant elements with :func:`Constructor.set_elements_constant`. This simply
set one or more element to the same value for all coordinates values.
Setting an element constant will override any results scanned, and conversely
adding a scanning function for an element previously set constant will remove
that constant.


Attributes scanning
-------------------

Other metadata can also be retrieved.
General attributes of the filegroup can be scanned by using
:func:`Constructor.add_scan_general_attributes`,
and variables specific attributes can be retrieved with
:func:`Constructor.add_scan_variables_attributes`.
In both cases, found information will be added to the
:ref:`Variables Info`.

Coordinate specific metadata can be found by using
:func:`Constructor.add_scan_coords_attributes`.
These attributes will be sent to `CoordScan.set_attr`, and thus should only
affect the scanning coordinate (and VI).
The user should manually propagates this information to its parent coordinates.

General attributes are the first thing to be scanned, then comes coordinates
attributes and values.
This is done to be able to use this information for the scanning (see
:ref:`Units conversion` for instance).
Variable specific information is scanned last. It is assumed metadata for each
variable is stored with its data (so possibly in different files for different
variables).
After the scanning, a load command is ensued to find in which files each
variable lies. The user function is then used. See
:func:`FilegroupLoad.scan_variables_attributes
<tomate.filegroup.filegroup_load.FilegroupLoad.scan_variables_attributes>`.

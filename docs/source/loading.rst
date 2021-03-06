
.. currentmodule:: tomate.filegroup


Loading
=======

The filegroup manages the loading of data. It receives from the database
object the parts of each dimensions to load.
The filegroup ellaborates a list of 'loading commands', which contain the file
to open, the parts of the data to take from that file (the in-file keys),
and where to put them in the data array in memory (the memory keys).
The filegroup then execute each command.

All this process relies heavily on keys and keyrings as defined in
:ref:`Keys and keyrings`.


Creation of loading commands
++++++++++++++++++++++++++++

Note that, hopefully, you should not have to temper with the construction of the
commands. This is mostly intended for developpers and if the need to debug
or change this process should arise.

.. note::

   The explainations in this section are not stellar, and not quite up to date.
   They still give the gist of what is happening if you are curious.
   If you want to change or fix this process, well may the gods of python
   be with you, and do not rely too much on what is explained here.

Loading starts in the DataBase object, where the user specify parts of each
dimension to load.
This is transmitted to each filegroup, in the form of a keyring containing
indices of the available scope.
The filegroup converts this into its own scope. It keeps part of demanded data
that it contains and find the appropriate memory keyring (that is still in
available scope).

We then need to retrieve the files to load, thus by working with the shared
coordinates. In the process we also retrieve the in-file index for shared
coordinates.

At this point, we have a list of commands, each containing one key for shared
coordinates.
The memory keys for the shared coordinate each have been split.
The in-file key should be an integer or None.
Commands for the same file are merged together.
We now possibly have multiple integers keys in the same file,
as this would be the case for files containing multiple steps for a shared
coordinate.
Rather than loading one step by one step, the keys are merged together when
possible. Two keys differing by only one coordinate are merged, and lists are
transformed into slices.
For instance::

    key 1: time=0, depth=0
    key 2: time=2, depth=0
    key 3: time=4, depth=0

would be transformed into::

    key 1: time=[0, 2, 4], depth=0

and then::

    key 1: time=slice(0, 5, 2), depth=0

Of course, the in-file keys are modified along with the memory keys.

Once the shared coordinates are taken care of, the in-file and memory keys
for in coordinates are constructed, and added to all the commands.
Lists of length one are transformed in integers.
The keys are finally ordered as specified in the data base.


Executing the command
+++++++++++++++++++++

The construction of the loading commands is completely remote from the file
format. The only function to depend on the file format is
:func:`load_cmd<filegroup_load.FilegroupLoad.load_cmd>`.
Thus, to add a file format, one has to mainly rewrite this function, as
well as two functions that open and close a file.

The function takes a single command and a file object in argument.
The file object is created by
:func:`open_file<filegroup_scan.FilegroupScan.open_file>`.
For each key in the command, the function should take a 'chunk' of data
corresponding to the in-file keyring, reorder it so that it matches the
dimensions order of the memory keyring, and finally place it in a subpart of the
database data array using the memory keyring.

For more information on subclassing for a new file format: :ref:`File formats`
For a working example: :mod:`tomate.filegroup.filegroup_netcdf`

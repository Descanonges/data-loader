"""NetCDF files support."""

# This file is part of the 'data-loader' project
# (http://github.com/Descanonges/data-loader)
# and subject to the MIT License as defined in file 'LICENSE',
# in the root of this project. © 2020 Clément HAËCK


import logging
import os
from typing import List

try:
    import netCDF4 as nc
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True

import numpy as np

from data_loader.custom_types import File
from data_loader.keys.keyring import Keyring
from data_loader.filegroup.filegroup_load import FilegroupLoad
from data_loader.filegroup.command import separate_variables, Command


log = logging.getLogger(__name__)


class FilegroupNetCDF(FilegroupLoad):
    """Filegroup class for NetCDF files."""

    def __init__(self, *args, **kwargs):
        if not _has_netcdf:
            raise ImportError("netCDF4 package necessary to use FilegroupNetCDF.")
        super().__init__(*args, **kwargs)

    def open_file(self, filename: str,
                  mode: str = 'r', log_lvl: str = 'info') -> nc.Dataset:
        file = nc.Dataset(filename, mode)
        log_lvl = getattr(logging, log_lvl.upper())
        log.log(log_lvl, "Opening %s", filename)
        return file

    def close_file(self, file: File):
        file.close()

    def get_commands(self, keyring: Keyring, memory: Keyring) -> List[Command]:
        commands = super().get_commands(keyring, memory)
        commands = separate_variables(commands)
        return commands

    def load_cmd(self, file: File, cmd: Command):
        for krg_inf, krg_mem in cmd:
            for ncname in krg_inf['var']:
                log.info("Looking at variable %s", ncname)

                chunk = self._load_slice_single_var(file, krg_inf, ncname)

                log.info("Placing it in %s",
                         krg_mem.print())
                self.acs.place(krg_mem, self.db.data, chunk)

    def _load_slice_single_var(self, file: nc.Dataset,
                               keyring: Keyring, ncname: str) -> np.ndarray:
        """Load data for a single variable.

        :param file: File object.
        :param keyring: Keys to load from file.
        :param ncname: Name of the variable in file.
        """
        order_file = self._get_order_in_file(file, ncname)
        order = self._get_order(order_file)
        int_krg = self._get_internal_keyring(order, keyring)

        log.info("Taking keys %s", int_krg.print())
        chunk = self.acs.take(int_krg, file[ncname])

        chunk = self.reorder_chunk(chunk, keyring, int_krg)
        return chunk

    @staticmethod
    def _get_order_in_file(file: nc.Dataset, ncname: str) -> List[str]:
        """Get order from netcdf file, reorder keys.

        :param file: File object.
        :param ncname: Name of the variable in file.

        :returns: Coordinate names in order.
        """
        order = list(file[ncname].dimensions)
        return order

    def write(self, filename: str, wd: str, keyring: Keyring):
        """Write data to disk."""
        if wd is None:
            wd = self.root

        file = os.path.join(wd, filename)

        with self.open_file(file, mode='w', log_lvl='INFO') as dt:
            for name, coord in self.db.loaded.coords.items():
                key = keyring[name].copy()
                key.set_shape_coord(coord)
                if key.shape != 0:
                    dt.createDimension(name, key.shape)
                    dt.createVariable(name, 'f', [name])
                    dt[name][:] = coord[key.value]
                    log.info("Laying %s values, extent %s", name,
                             coord.get_extent_str(key.no_int()))

                    dt[name].setncattr('fullname', coord.fullname)
                    dt[name].setncattr('units', coord.units)

            for info in self.db.vi.infos:
                if not info.startswith('_'):
                    dt.setncattr(info, self.db.vi.get_info(info))

            for var in keyring['var']:
                cs = self.cs['var']
                name = cs.in_idx[cs.idx(var)]
                t = self.vi.get_attr_safe('nctype', var, 'f')
                dimensions = keyring.get_non_zeros()
                dimensions.remove('var')
                dt.createVariable(name, t, dimensions)
                dt[name][:] = self.db.view(keyring=keyring, var=var)

                for attr in self.db.vi.attrs:
                    if not attr.startswith('_'):
                        dt[name].setncattr(attr, self.db.vi.get_attr(attr, var))

    def write_variable(self, file: nc.Dataset, cmd: Command,
                       var: str, inf_name: str):
        """Add variable to file."""

        for krg_inf, krg_mem in cmd:
            if inf_name not in file.variables:

                t = self.vi.get_attr_safe('nctype', var, 'f')
                file.createVariable(inf_name, t, self.db.coords_name)

                for attr in self.db.vi.attrs:
                    # TODO: no attributes for all variables.
                    if not attr.startswith('_'):
                        value = self.db.vi.get_attr(attr, var)
                        if value is not None:
                            file[inf_name].setncattr(attr, value)

            ncvar = file[var]

            order = self._get_order_in_file(file, var)
            chunk = self.db.acs.take(krg_mem, self.db.data)
            chunk = self.reorder_chunk(chunk, krg_inf, order)


            if not krg_inf.is_shape_equivalent(ncvar.shape):
                raise ValueError("Mismatch between selected data "
                                 "and keyring shape (array: %s, keyring: %s)"
                                 % (ncvar.shape, krg_inf.shape))
            ncvar[:] = chunk

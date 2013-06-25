"""Pydap handler for NetCDF3/4 files."""

import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate

import numpy as np
from pkg_resources import get_distribution

try:
    from netCDF4 import Dataset as netcdf_file
    attrs = lambda var: {k: getattr(var, k) for k in var.ncattrs()}
except ImportError:
    from pupynere import netcdf_file
    attrs = lambda var: var._attributes

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError


class NetCDFHandler(BaseHandler):

    __version__ = get_distribution("pydap.handlers.netcdf").version
    extensions = re.compile(r"^.*\.(nc|cdf)$", re.IGNORECASE)

    def __init__(self, filepath):
        BaseHandler.__init__(self)

        try:
            self.fp = netcdf_file(filepath)
        except Exception, exc:
            message = 'Unable to open file %s: %s' % (filepath, exc)
            raise OpenFileError(message)

        self.additional_headers.append(
            ('Last-modified', (
                formatdate(
                    time.mktime(
                        time.localtime(os.stat(filepath)[ST_MTIME]))))))

        # shortcuts
        vars = self.fp.variables
        dims = self.fp.dimensions

        # build dataset
        name = os.path.split(filepath)[1]
        self.dataset = DatasetType(
            name, attributes=dict(NC_GLOBAL=attrs(self.fp)))
        for dim in dims:
            if dims[dim] is None:
                self.dataset.attributes['DODS_EXTRA'] = {
                    'Unlimited_Dimension': dim,
                }
                break

        # add grids
        grids = [var for var in vars if var not in dims]
        for grid in grids:
            self.dataset[grid] = GridType(grid, attrs(vars[grid]))
            # add array
            self.dataset[grid][grid] = BaseType(
                grid, NetcdfData(vars[grid]), vars[grid].dimensions,
                attrs(vars[grid]))
            # add maps
            for dim in vars[grid].dimensions:
                self.dataset[grid][dim] = BaseType(
                    dim, vars[dim][:], None, attrs(vars[dim]))

        # add dims
        for dim in dims:
            self.dataset[dim] = BaseType(
                dim, vars[dim][:], None, attrs(vars[dim]))

    def close(self):
        self.fp.close()


class NetcdfData(object):
    """
    A wrapper for Netcdf variables, making them behave more like Numpy arrays.

    """
    def __init__(self, var):
        self.var = var
        self.dtype = np.dtype(self.var.dtype.char)
        self.shape = var.shape

    # Comparisons are passed to the data.
    def __eq__(self, other):
        return self.var[:] == other

    def __ne__(self, other):
        return self.var[:] != other

    def __ge__(self, other):
        return self.var[:] >= other

    def __le__(self, other):
        return self.var[:] <= other

    def __gt__(self, other):
        return self.var[:] > other

    def __lt__(self, other):
        return self.var[:] < other

    # Implement the sequence and iter protocols.
    def __getitem__(self, index):
        return self.var[index]

    def __len__(self):
        return self.shape[0]

    def __iter__(self):
        return iter(self.var[:])


if __name__ == "__main__":
    import sys
    from werkzeug.serving import run_simple

    application = NetCDFHandler(sys.argv[1])
    run_simple('localhost', 8001, application, use_reloader=True)

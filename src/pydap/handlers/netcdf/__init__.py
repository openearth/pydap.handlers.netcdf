"""Pydap handler for NetCDF3/4 files."""

import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate

import numpy as np
from pkg_resources import get_distribution

# available NetCDF modules
NETCDF4 = 0
PUPYNERE = 1

try:
    from netCDF4 import Dataset as netcdf_file
    attrs = lambda var: {k: getattr(var, k) for k in var.ncattrs()}
    NETCDF_MODULE = NETCDF4
except ImportError:
    from pupynere import netcdf_file
    attrs = lambda var: var._attributes
    NETCDF_MODULE = PUPYNERE

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError


class NetCDFHandler(BaseHandler):

    """A simple handler for NetCDF files."""

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

        # turn off automatic scaling
        if NETCDF_MODULE == NETCDF4:
            for var in vars.values():
                var.set_auto_maskandscale(False)

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
                grid, vars[grid], vars[grid].dimensions, attrs(vars[grid]))
            # add maps
            for dim in vars[grid].dimensions:
                self.dataset[grid][dim] = BaseType(
                    dim, vars[dim][:], None, attrs(vars[dim]))

        # add dims
        for dim in dims:
            self.dataset[dim] = BaseType(
                dim, vars[dim][:], None, attrs(vars[dim]))

    def close(self):
        """Close the NetCDF file."""
        self.fp.close()


if __name__ == "__main__":
    import sys
    from werkzeug.serving import run_simple

    application = NetCDFHandler(sys.argv[1])
    run_simple('localhost', 8001, application, use_reloader=True)

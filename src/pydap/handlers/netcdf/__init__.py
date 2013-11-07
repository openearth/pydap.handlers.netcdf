"""Pydap handler for NetCDF3/4 files."""

import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate

import numpy as np
from pkg_resources import get_distribution

# available NetCDF modules
NETCDF4 = "netCDF4"
PUPYNERE = "pupynere"

try:
    from netCDF4 import Dataset as netcdf_file
    NETCDF_MODULE = NETCDF4

    def attrs(var):
        """Use the netCDF4 API to load all attributes."""
        if hasattr(var, "ncattrs"):
            return {k: getattr(var, k) for k in var.ncattrs()}
        else:
            return {}

except ImportError:
    from pupynere import netcdf_file
    NETCDF_MODULE = PUPYNERE
    
    def attrs(var):
        """Pupynere stores attributes in a special attribute."""
        return getattr(var, "_attributes", {})

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
        vars = dict(self.fp.variables)
        dims = dict(self.fp.dimensions)

        # turn off automatic scaling
        if NETCDF_MODULE == NETCDF4:
            for var in vars.values():
                var.set_auto_maskandscale(False)

        # add missing dimensions
        for dim in dims:
            if dim not in vars:
                if NETCDF_MODULE == NETCDF4:
                    length = len(dims[dim])
                else:
                    length = dims[dim]
                vars[dim] = np.arange(length)

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

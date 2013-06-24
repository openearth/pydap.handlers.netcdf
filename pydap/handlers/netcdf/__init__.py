import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate
import urllib

import numpy

from arrayterator import Arrayterator

from pydap.model import *
from pydap.lib import quote
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError

try:
    from nio import open_file as nc
    extensions = re.compile(
            r"^.*\.(nc|cdf|netcdf|grb|grib|grb1|grib1|grb2|grib2|hd|hdf|he2|he4|hdfeos|ccm)$",
            re.IGNORECASE)
    var_attrs = lambda var: var.__dict__.copy()
    get_value = lambda var: var.get_value()
    get_typecode = lambda var: var.typecode()
except ImportError:
    try:
        from netCDF4 import Dataset as nc
        extensions = re.compile(
                r"^.*\.(nc|nc4|cdf|netcdf)$",
                re.IGNORECASE)
        var_attrs = lambda var: dict( (a, getattr(var, a))
                for a in var.ncattrs() )
        get_value = lambda var: var.getValue()
        get_typecode = lambda var: var.dtype.char
    except ImportError:
        try:
            from Scientific.IO.NetCDF import NetCDFFile as nc
            extensions = re.compile(
                    r"^.*\.(nc|cdf|netcdf)$",
                    re.IGNORECASE)
            var_attrs = lambda var: var.__dict__.copy()
            get_value = lambda var: var.getValue()
            get_typecode = lambda var: var.typecode()
        except ImportError:
            try:
                from pynetcdf import NetCDFFile as nc
                extensions = re.compile(
                        r"^.*\.(nc|cdf|netcdf)$",
                        re.IGNORECASE)
                var_attrs = lambda var: var.__dict__.copy()
                get_value = lambda var: var.getValue()
                get_typecode = lambda var: var.typecode()
            except ImportError:
                from pupynere import NetCDFFile as nc
                extensions = re.compile(
                        r"^.*\.(nc|cdf|netcdf)$",
                        re.IGNORECASE)
                var_attrs = lambda var: var._attributes.copy()
                get_value = lambda var: var.getValue()
                get_typecode = lambda var: var.typecode()


class Handler(BaseHandler):

    extensions = extensions

    def __init__(self, filepath):
        self.filepath = filepath

    def parse_constraints(self, environ):
        buf_size = int(environ.get('pydap.handlers.netcdf.buf_size', 10000))

        try:
            fp = nc(self.filepath)
        except:
            message = 'Unable to open file %s.' % self.filepath
            raise OpenFileError(message)

        last_modified = formatdate( time.mktime( time.localtime( os.stat(self.filepath)[ST_MTIME] ) ) )
        environ['pydap.headers'].append( ('Last-modified', last_modified) )

        dataset = DatasetType(name=os.path.split(self.filepath)[1],
                attributes={'NC_GLOBAL': var_attrs(fp)})
        for dim in fp.dimensions:
            if fp.dimensions[dim] is None:
                dataset.attributes['DODS_EXTRA'] = {'Unlimited_Dimension': dim}
                break

        fields, queries = environ['pydap.ce']
        fields = fields or [[(quote(name), ())] for name in fp.variables]
        for var in fields:
            target = dataset
            while var:
                name, slice_ = var.pop(0)
                ncname = urllib.unquote(name)
                if (ncname in fp.dimensions or
                        not fp.variables[ncname].dimensions or
                        target is not dataset):
                    target[name] = get_var(ncname, fp, slice_, buf_size)
                elif var:
                    attrs = var_attrs(fp.variables[ncname])
                    target.setdefault(name, StructureType(name=name, attributes=attrs))
                    target = target[name]
                else:  # return grid
                    attrs = var_attrs(fp.variables[ncname])
                    grid = target[name] = GridType(name=name, attributes=attrs)
                    grid[name] = get_var(ncname, fp, slice_, buf_size)
                    slice_ = list(slice_) + [slice(None)] * (len(grid.array.shape) - len(slice_))
                    for dim, dimslice in zip(fp.variables[ncname].dimensions, slice_):
                        axis = get_var(dim, fp, dimslice, buf_size)
                        grid[axis.name] = axis

        dataset._set_id()
        dataset.close = fp.close
        return dataset


def get_var(name, fp, slice_, buf_size=10000):
    if name in fp.variables:
        var = fp.variables[name]
        if hasattr(var, 'set_auto_maskandscale'):
            var.set_auto_maskandscale(False)
        if var.shape: 
            data = Arrayterator(var, buf_size)[slice_]
        else:
            data = numpy.array(get_value(var))
        typecode = get_typecode(var)
        dims = tuple(quote(dim) for dim in var.dimensions)
        attrs = var_attrs(var)
    else:
        for var in fp.variables:
            var = fp.variables[var]
            if name in var.dimensions:
                size = var.shape[
                        list(var.dimensions).index(name)]
                break
        data = numpy.arange(size)[slice_]
        typecode = data.dtype.char
        dims, attrs = (quote(name),), {}

    # handle char vars
    if typecode == 'S1':
        typecode = 'S'
        data = numpy.array([''.join(row) for row in numpy.asarray(data)])
        dims = dims[:-1]

    return BaseType(name=name, data=data, shape=data.shape,
            type=typecode, dimensions=dims,
            attributes=attrs)


if __name__ == '__main__':
    import sys
    from paste.httpserver import serve

    application = Handler(sys.argv[1])
    serve(application, port=8001)

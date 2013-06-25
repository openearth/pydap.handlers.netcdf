from setuptools import setup, find_packages
import sys, os


version = '0.7'

install_requires = [
    # List your project dependencies here.
    # For more details, see:
    # http://packages.python.org/distribute/setuptools.html#declaring-dependencies
    "Numpy",
    "pupynere",
]


setup(name='pydap.handlers.netcdf',
    version=version,
    description="Netcdf handler for Pydap",
    long_description="""
This handler allows Pydap to serve data from NetCDF files. By default           
`pupynere <http://code.dealmeida.net/pupynere>`_ is installed as a dependency,    
providing support for NetCDF 3 files. If you also want to server NetCDF 4 files 
you'll need to install the `netCDF4-python <https://code.google.com/p/netcdf4-python/>`_
library.
""",
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='netcdf opendap dods dap science meteorology oceanography',
    author='Roberto De Almeida',
    author_email='roberto@dealmeida.net',
    url='https://github.com/robertodealmeida/pydap.handlers.netcdf',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    namespace_packages = ['pydap', 'pydap.handlers'],
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points="""
        [pydap.handler]
        netcdf = pydap.handlers.netcdf:NetCDFHandler
    """,
)

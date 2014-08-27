#!/usr/bin/env python

# import modules
import os, datetime
from os.path import isfile
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy import zeros, double, resize

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "data/CenW.DT!", type = "string",
                  help = "CenW DT! file to parse", metavar = "FILE")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.psims.nc", type = "string",
                  help = "Output pSIMS file", metavar = "FILE")
parser.add_option("-s", "--num_scenarios", dest = "num_scenarios", default = 1, type = "int",
                  help = "Number of scenarios to process")
parser.add_option("-y", "--num_years", dest = "num_years", default = 1, type = "int",
                  help = "Number of years in input file")
parser.add_option("-v", "--variables", dest = "variables", default = "", type = "string",
                  help = "String of comma-separated list (with no spaces) of variables to process")
parser.add_option("-u", "--units", dest = "units", default = "", type = "string",
                  help = "Comma-separated list (with no spaces) of units for the variables")
parser.add_option("-d", "--delta", dest = "delta", default = 1, type = "float",
                  help = "Distance between each grid cell in arcminutes")
parser.add_option("-r", "--ref_year", dest = "ref_year", default = 1958, type = "int",
                  help = "Reference year from which to record times")                          
parser.add_option("--latidx", dest = "latidx", default = 1, type = "string",
                  help = "Latitude coordinate")
parser.add_option("--lonidx", dest = "lonidx", default = 1, type = "string",
                  help = "Longitude coordinate")
options, args = parser.parse_args()

file_exists = isfile(options.inputfile)
if file_exists:
    data = open(options.inputfile).readlines()

# get variables
nscens = options.num_scenarios
nyears = options.num_years
variables = options.variables.replace(':', ' ').split(',')
units = options.units.split(',')
latidx = int(options.latidx)
lonidx = int(options.lonidx)
delta = options.delta / 60. # convert from arcminutes to degrees

header1 = data[0][: -2]
header2 = data[2][: -2]

ncolwidth = 8
ncols = (len(header1) - ncolwidth) / (ncolwidth + 1) + 1

allvariables = [0] * ncols
allunits = [0] * ncols
idx = 0
for i in range(ncols):
    allvariables[i] = header1[idx : idx + ncolwidth].strip()
    allunits[i] = header2[idx : idx + ncolwidth].strip()
    idx += ncolwidth + 1

nv = len(variables)
variableidx = [0] * nv
for i in range(nv):
    v = variables[i]
    if not v in allvariables:
        raise Exception('Variable %s not in summary file' % v)
    else:
        variableidx[i] = allvariables.index(v)

ndata = len(data) - 4
alldata = zeros((ndata, nv))
for i in range(ndata):
    datasplit = data[i + 4].split()
    alldata[i] = [double(datasplit[idx]) for idx in variableidx]

lat = 90. - delta * (latidx - 0.5)
lon = -180. + delta * (lonidx - 0.5)
ref_date = datetime.datetime(options.ref_year, 1, 1)

if ndata % (nyears * nscens):
    raise Exception('Invalid data length')

sizeblock = nyears * nscens
nplantings = ndata / sizeblock
nnewscens = nplantings * nscens

vardata = zeros((nv, nyears, nnewscens))
idx1 = idx2 = 0
for i in range(nplantings):
    for v in range(nv):
        data = alldata[idx1 : idx1 + sizeblock, v]
        vardata[v, :, idx2 : idx2 + nscens] = resize(data, (nscens, nyears)).T
    idx1 += sizeblock
    idx2 += nscens

dirname = os.path.dirname(options.outputfile)
if dirname and not os.path.exists(dirname):
    raise Exception('Directory to output file does not exist')
rootgrp = nc(options.outputfile, 'w', format = 'NETCDF3_CLASSIC')

rootgrp.createDimension('longitude', 1)
lonvar = rootgrp.createVariable('longitude', 'f8', ('longitude',))
lonvar[:] = lon
lonvar.units = 'degrees_east'
lonvar.long_name = 'longitude'
rootgrp.createDimension('latitude', 1)
latvar = rootgrp.createVariable('latitude', 'f8', ('latitude',))
latvar[:] = lat
latvar.units = 'degrees_north'
latvar.long_name = 'latitude'

rootgrp.createDimension('time', nyears)
timevar = rootgrp.createVariable('time', 'i4', ('time',))
timevar[:] = range(0, nyears)
timevar.units = 'years since {:s}'.format(str(ref_date))

rootgrp.createDimension('scenario', nnewscens)
scenariovar = rootgrp.createVariable('scenario', 'i4', 'scenario')
scenariovar[:] = range(1, nnewscens + 1)
scenariovar.units = 'no'
scenariovar.long_name = '%d plantings x %d scenarios' % (nplantings, nscens)

for i in range(nv):
    var = rootgrp.createVariable(variables[i].replace(' ', '_'), 'f4', ('time', 'scenario', 'latitude', 'longitude',))
    var[:] = vardata[i]
    var.units = units[i]

rootgrp.close()
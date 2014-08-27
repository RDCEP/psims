#!/usr/bin/env python

from re import findall
from shutil import copyfile
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import masked_array, resize
from numpy import where, zeros, ones, unique, floor, newaxis

parser = OptionParser()
parser.add_option("-i", "--inputfile", dest = "inputfile", default = "", type = "string", 
                  help = "Input aggregation file", metavar = "FILE")
parser.add_option("-y", "--yldfile", dest = "yldfile", default = "yield_targets_census.nc4", type = "string", 
                  help = "Yield targets file", metavar = "FILE")
parser.add_option("-v", "--variable", dest = "variable", default = "HWAM", type = "string", 
                  help = "Variable to aggregate")
parser.add_option("-o", "--outputfile", dest = "outputfile", default = "", type = "string", 
                  help = "Output aggregation file", metavar = "FILE")
options, args = parser.parse_args()

inputfile  = options.inputfile
yldfile    = options.yldfile
variable   = options.variable
outputfile = options.outputfile

copyfile(inputfile, outputfile) # make copy

with nc(outputfile) as f:
    counties = f.variables['county_index'][:]
    otime    = f.variables['time'][:]
    tunits   = f.variables['time'].units
    var      = f.variables[variable + '_county'][:] # scen, time, county, irr
    varunits = f.variables[variable + '_county'].units
    nscen    = f.variables['scen'].size
    nirr     = f.variables['irr'].size
otime += int(findall(r'\d+', tunits)[0]) - 1 # growing seasons since to years
ncounties, ntime = len(counties), len(otime)

with nc(options.yldfile) as f:
    ytime = f.variables['time'][:]
    tunits = f.variables['time'].units
    harvested_area = f.variables['harvested_area'][:] # time, county, irr
ytime += int(findall(r'\d+', tunits)[0]) # years since to years

states  = floor(counties / 1000.)
ustates = unique(states)
nstates = len(ustates)

tidx1, tidx2 = where(ytime == otime[0])[0][0], where(ytime == otime[-1])[0][0] + 1

harvested_area = resize(harvested_area[tidx1 : tidx2], (nscen, ntime, ncounties, nirr))

# aggregate to country level
var_country = (var * harvested_area).sum(axis = 2) / harvested_area.sum(axis = 2)
var_country = var_country[newaxis, ...].transpose((1, 2, 0, 3))

# aggregate to state level
sh = (nscen, ntime, nstates, nirr)
var_state = masked_array(zeros(sh), mask = ones(sh))
for i in range(nstates):
    is_state = states == ustates[i]
    var_state_i = var[:, :, is_state, :]
    hva_state_i = harvested_area[:, :, is_state, :]
    var_state[:, :, i, :] = (var_state_i * hva_state_i).sum(axis = 2) / hva_state_i.sum(axis = 2)

# append to file
with nc(outputfile, 'a') as f:
    countryvar = f.createVariable(variable + '_country_2', 'f4', ('scen', 'time', 'country_index', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    countryvar[:] = var_country
    countryvar.units = varunits
    countryvar.long_name = 'average country %s' % variable

    statevar = f.createVariable(variable + '_state_2', 'f4', ('scen', 'time', 'state_index', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    statevar[:] = var_state
    statevar.units = varunits
    statevar.long_name = 'average state %s' % variable
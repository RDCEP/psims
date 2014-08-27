#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import modules
import re, abc
from os import sep
from itertools import product
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import masked_array, isMaskedArray
from numpy import where, zeros, arange, polyfit, sqrt

class Detrender(object):
    @abc.abstractmethod
    def detrend(self, y): return
    def polytrend(self, y, order):
        ly = len(y)
        x = arange(1, 1 + ly)
        if isMaskedArray(y):
            mask = y.mask
            line = masked_array(zeros(ly), mask = mask)
            if not mask.all():
                x2 = x[~mask]
                y2 = y[~mask]
                if len(x2) < order + 1: # fewer points than order of polynomial
                    line[~mask] = y2
                else:
                    coef = polyfit(x2, y2, order)
                    for i in range(order + 1):
                        line[~mask] += coef[i] * x2 ** (order - i)
        else:
            coef = polyfit(x, y, order)
            line = zeros(ly)
            for i in range(order + 1):
                line += coef[i] * x ** (order - i)
        return line
class PolyDetrender(Detrender):
    def __init__(self, order): self.order = order
    def detrend(self, y):
        line = self.polytrend(y, self.order)
        dy = y - line
        return dy, line

def bc(sim, obs):
    simdt, simtr = PolyDetrender(2).detrend(sim)
    obsdt, _     = PolyDetrender(2).detrend(obs)
    simvar = simdt.var()
    fac = sqrt(obsdt.var() / simvar) if simvar else 1.
    return simtr + fac * simdt

# parse inputs
parser = OptionParser()
parser.add_option("-a", "--aggfile", dest = "aggfile", default = "out.agg.final.nc4", type = "string", 
                  help = "Aggregated file", metavar = "FILE")
parser.add_option("-y", "--yieldfile", dest = "yieldfile", default = "yield_targets.nc4", type = "string", 
                  help = "Yield targets file", metavar = "FILE")
parser.add_option("-c", "--countyidx", dest = "countyidx", default = "0", type = "string", 
                  help = "Comma-separated list of county indices")
parser.add_option("-o", dest = "outputdir", default = ".", type = "string", 
                  help = "Directory to save output")
options, args = parser.parse_args()

aggfile   = options.aggfile
yieldfile = options.yieldfile
countyidx = options.countyidx
outputdir = options.outputdir

countyidx = [int(c) for c in countyidx.split(',')]

with nc(aggfile) as f:
    simt = f.variables['time'][:]
    tunits = f.variables['time'].units
    simt += int(re.findall(r'\d+', tunits)[0]) - 1
    counties = f.variables['county_index'][countyidx]
    irr = f.variables['irr'].long_name
    simy = f.variables['HWAM_county'][:, :, countyidx, :] # time, scen, county, irr

with nc(yieldfile) as f:
    objt = f.variables['time'][:]
    tunits = f.variables['time'].units
    objt += int(re.findall(r'\d+', tunits)[0])
    obsy = f.variables['yield'][:, countyidx, :] # time, county, irr

# sample to simulation time
tidx1, tidx2 = where(objt == simt[0])[0][0], where(objt == simt[-1])[0][0] + 1
obsy = obsy[tidx1 : tidx2]

ntime, nscens, ncounties, nirr = simy.shape

# perform bias correction
simy_bc = simy.copy()
cnt = 0
for s, c, i in product(range(0, nscens), range(ncounties), range(nirr)):
    if cnt % 1000 == 0:
        print cnt
    simyc = simy[:, s, c, i]
    obsyc = obsy[:, c, i]
    for t in range(4, len(simy)): # start at time = 5
        simy_bc[t, s, c, i] = bc(simyc[: t + 1], obsyc[: t + 1])[-1]
    cnt += 1

# write to file
outfile = outputdir + sep + 'out.biascorr.' + str(countyidx[0]).zfill(4) + '.nc4' # zeropad
with nc(outfile, 'w') as f:
    f.createDimension('county_index', None) # make UNLIMITED
    countyvar = f.createVariable('county_index', 'i4', 'county_index')
    countyvar[:] = counties
    countyvar.units = ''
    countyvar.long_name = 'County index'

    f.createDimension('irr', nirr)
    irrvar = f.createVariable('irr', 'i4', 'irr')
    irrvar[:] = range(1, 1 + nirr)
    irrvar.units = 'mapping'
    irrvar.long_name = irr

    f.createDimension('time', ntime)
    timevar = f.createVariable('time', 'i4', 'time')
    timevar[:] = simt - simt[0] + 1
    timevar.units = 'growing seasons since %d-01-01 00:00:00' % simt[0] 
    timevar.long_name = 'time'

    f.createDimension('scen', nscens)
    scenvar = f.createVariable('scen', 'i4', 'scen')
    scenvar[:] = range(1, 1 + nscens)
    scenvar.units = 'no'
    scenvar.long_name = 'scenarios'

    simvar = f.createVariable('HWAM_county', 'f4', ('time', 'scen', 'county_index', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    simvar[:] = simy_bc
    simvar.units = 'kg/ha'
    simvar.long_name = 'average bias-corrected county HWAM'
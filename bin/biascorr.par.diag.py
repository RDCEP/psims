#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import modules
import re, abc
from os import sep
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

    counties  = f.variables['county'][countyidx]
    countries = f.variables['country'][:]
    states    = f.variables['state'][:]

    irr = f.variables['irr'].long_name

    simy_county  = f.variables['sim_yield'][:, countyidx, :] # time, county, irr
    simy_country = f.variables['sim_yield_country'][:]       # time, country, irr
    simy_state   = f.variables['sim_yield_state'][:]         # time, state, irr

with nc(yieldfile) as f:
    objt = f.variables['time'][:]
    tunits = f.variables['time'].units
    objt += int(re.findall(r'\d+', tunits)[0])

    obsy_county  = f.variables['yield'][:, countyidx, :] # time, county, irr
    obsy_country = f.variables['yield_country'][:]       # time, country, irr
    obsy_state   = f.variables['yield_state'][:]         # time, state, irr

# sample to simulation time
tidx1, tidx2 = where(objt == simt[0])[0][0], where(objt == simt[-1])[0][0] + 1
obsy_county  = obsy_county[tidx1  : tidx2]
obsy_country = obsy_country[tidx1 : tidx2] 
obsy_state   = obsy_state[tidx1   : tidx2]

ntime, ncounties, nirr = simy_county.shape
ncountries, nstates = simy_country.shape[1], simy_state.shape[1]

# perform bias correction
simy_county_bc  = simy_county.copy()
simy_country_bc = simy_country.copy()
simy_state_bc   = simy_state.copy()
for i in range(nirr):
    for c in range(ncounties): # counties
        simyc = simy_county[:, c, i]
        obsyc = obsy_county[:, c, i]
        for t in range(4, ntime): # start at time = 5
            simy_county_bc[t, c, i] = bc(simyc[: t + 1], obsyc[: t + 1])[-1]
    for c in range(ncountries): # countries
        simyc = simy_country[:, c, i]
        obsyc = obsy_country[:, c, i]
        for t in range(4, ntime):
            simy_country_bc[t, c, i] = bc(simyc[: t + 1], obsyc[: t + 1])[-1]
    for s in range(nstates): # states
        simys = simy_state[:, s, i]
        obsys = obsy_state[:, s, i]
        for t in range(4, ntime):
            simy_state_bc[t, s, i] = bc(simys[: t + 1], obsys[: t + 1])[-1]

# write to file
outfile = outputdir + sep + 'out.biascorr.' + str(countyidx[0]).zfill(4) + '.nc4' # zeropad
with nc(outfile, 'w') as f:
    f.createDimension('county', None) # make UNLIMITED
    countyvar = f.createVariable('county', 'i4', 'county')
    countyvar[:] = counties
    countyvar.units = ''
    countyvar.long_name = 'County index'

    f.createDimension('country', ncountries)
    countryvar = f.createVariable('country', 'i4', 'country')
    countryvar[:] = countries
    countryvar.units = ''
    countryvar.long_name = 'Country index'

    f.createDimension('state', nstates)
    statevar = f.createVariable('state', 'i4', 'state')
    statevar[:] = states
    statevar.units = ''
    statevar.long_name = 'State index'

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

    simcountyvar = f.createVariable('sim_yield', 'f4', ('time', 'county', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    simcountyvar[:] = simy_county_bc
    simcountyvar.units = 'kg/ha'
    simcountyvar.long_name = 'average bias-corrected county simulated yield'

    simcountryvar = f.createVariable('sim_yield_country', 'f4', ('time', 'country', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    simcountryvar[:] = simy_country_bc
    simcountryvar.units = 'kg/ha'
    simcountryvar.long_name = 'average bias-corrected country simulated yield'

    simstatevar = f.createVariable('sim_yield_state', 'f4', ('time', 'state', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    simstatevar[:] = simy_state_bc
    simstatevar.units = 'kg/ha'
    simstatevar.long_name = 'average bias-corrected state simulated yield'
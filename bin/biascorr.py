#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import modules
import re, abc
from itertools import product
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy import where, zeros, arange, polyfit
from numpy.ma import masked_array, isMaskedArray

import warnings
warnings.filterwarnings('error')

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
    return simtr + simdt * obsdt.var() / simdt.var()

# parse inputs
parser = OptionParser()
parser.add_option("-a", "--aggfile", dest = "aggfile", default = "out.agg.final.nc4", type = "string", 
                  help = "Aggregated file", metavar = "FILE")
parser.add_option("-y", "--yieldfile", dest = "yieldfile", default = "yield_targets.nc4", type = "string", 
                  help = "Yield targets file", metavar = "FILE")
options, args = parser.parse_args()

with nc(options.aggfile) as f:
    simt = f.variables['time'][:]
    tunits = f.variables['time'].units
    simt += int(re.findall(r'\d+', tunits)[0]) - 1
    simy_county = f.variables['HWAM_county'][:] # time, scen, county, irr
    simy_state  = f.variables['HWAM_state'][:]  # time, scen, state, irr

with nc(options.yieldfile) as f:
    objt = f.variables['time'][:]
    tunits = f.variables['time'].units
    objt += int(re.findall(r'\d+', tunits)[0])
    obsy_county = f.variables['yield'][:]       # time, county, irr
    obsy_state  = f.variables['yield_state'][:] # time, state, irr

# sample to simulation time
tidx1, tidx2 = where(objt == simt[0])[0][0], where(objt == simt[-1])[0][0] + 1
obsy_county = obsy_county[tidx1 : tidx2]
obsy_state  = obsy_state[tidx1  : tidx2]

_, nscens, ncounties, nirr = simy_county.shape
_, _, nstates, _           = simy_state.shape

# county bias correction
simy_county_bc = simy_county.copy()
for s, c, i in product(range(0, nscens), range(ncounties), range(nirr)):
    simy = simy_county[:, s, c, i]
    obsy = obsy_county[:, c, i]
    for t in range(4, len(simy)): # start at time = 5
        simy_county_bc[t, s, c, i] = bc(simy[: t + 1], obsy[: t + 1])[-1]

# state bias correction
simy_state_bc = simy_state.copy()
for s, st, i in product(range(0, nscens), range(nstates), range(nirr)):
    simy = simy_state[:, s, st, i]
    obsy = obsy_state[:, st, i]
    for t in range(5, len(simy)): # start at time = 5
        simy_state_bc[t, s, st, i] = bc(simy[: t + 1], obsy[: t + 1])[-1]

# write to file
with nc(options.aggfile, 'a') as f:
    sim_county_var = f.variables['HWAM_county']
    sim_county_var[:] = simy_county_bc
    sim_state_var = f.variables['HWAM_state']
    sim_state_var[:] = simy_state_bc
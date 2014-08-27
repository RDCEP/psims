#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import modules
import re
from os import sep
from itertools import product
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import resize, masked_where, masked_array
from numpy import where, zeros, ones, array, argsort, sqrt

def selyears(years, t1, t2, skipyears = None):
    trange = range(t1, t2 + 1)
    if not skipyears is None:
        for y in skipyears:
            if y in trange and t1 != t2:
                trange.remove(y)
    yearidx = [0] * len(trange)
    for i in range(len(yearidx)):
        yearidx[i] = where(years == trange[i])[0][0]
    return yearidx

# parse inputs
parser = OptionParser()
parser.add_option("-a", "--aggfile", dest = "aggfile", default = "out.agg.final.nc4", type = "string", 
                  help = "Aggregated file", metavar = "FILE")
parser.add_option("-r", "--cropfile", dest = "cropfile", default = "crop_progress.nc4", type = "string", 
                  help = "Crop progress file", metavar = "FILE")
parser.add_option("-y", "--yieldfile", dest = "yieldfile", default = "yield_targets.nc4", type = "string", 
                  help = "Yield targets file", metavar = "FILE")
parser.add_option("-c", "--countyidx", dest = "countyidx", default = "0", type = "string", 
                  help = "Comma-separated list of county indices")
parser.add_option("-i", "--irridx", dest = "irridx", default = "0", type = "string", 
                  help = "Comma-separated list of irrigation indices")
parser.add_option("--t1", dest = "time1", default = "1981", type = "string", 
                  help = "Comma-separated list of start years")
parser.add_option("--t2", dest = "time2", default = "2012", type = "string", 
                  help = "Comma-separated list of end years")
parser.add_option("-d", dest = "outputdir", default = ".", type = "string", 
                  help = "Directory to save output")
parser.add_option("-s", "--skipyears", dest = "skipyears", default = None, type = "string", 
                  help = "Comma-separated list of years to disregard in optimization (optional)")
parser.add_option("-o", "--order", dest = "order", default = 1, type = "int", 
                  help = "Order of optimization (1 = lowest RMSE, etc.) (optional)")                  
parser.add_option("--shift", action = "store_true", dest = "shift", default = False,
                  help = "Whether to shift simulated data by observed mean (optional)")
parser.add_option("--twts", action = "store_true", dest = "twts", default = False,
                  help = "Whether to apply time weights to objective (optional)")
parser.add_option("--rwts", action = "store_true", dest = "rwts", default = False,
                  help = "Whether to apply RMSE weights to objective (optional)")
options, args = parser.parse_args()

wts = array([2.13840161e-06, 3.77888961e-06, 6.67787970e-06, \
             1.18008153e-05, 2.08537290e-05, 3.68512668e-05, \
             6.51202095e-05, 1.15072020e-04, 2.03332615e-04, \
             3.59265034e-04, 6.34703532e-04, 1.12107623e-03, \
             1.97941765e-03, 3.49264219e-03, 6.15556105e-03, \
             1.08267286e-02, 1.89749490e-02, 3.30506416e-02, \
             5.69614773e-02, 9.64454678e-02, 1.58692948e-01, \
             2.50000000e-01, 3.70694379e-01, 5.10032188e-01, \
             6.47828414e-01, 7.64746467e-01, 8.51732417e-01, \
             9.10326415e-01, 9.47200057e-01, 9.69420642e-01, \
             9.82462946e-01, 9.90000000e-01])

aggfile   = options.aggfile
cropfile  = options.cropfile
yieldfile = options.yieldfile
countyidx = options.countyidx
irridx    = options.irridx
time1     = options.time1
time2     = options.time2
outputdir = options.outputdir
skipyears = options.skipyears
order     = options.order
shift     = options.shift
twts      = options.twts
rwts      = options.rwts

countyidx = [int(c) for c in countyidx.split(',')]
irridx    = [int(i) for i in irridx.split(',')]
time1     = [int(t) for t in time1.split(',')]
time2     = [int(t) for t in time2.split(',')]

if not skipyears is None:
    skipyears = [int(y) for y in skipyears.split(',')]

with nc(aggfile) as f: # load simulated data
    simt = f.variables['time'][:]
    tunits = f.variables['time'].units
    simt += int(re.findall(r'\d+', tunits)[0]) - 1 # growing seasons since to years

    counties = f.variables['county_index'][countyidx]
    irr = array(f.variables['irr'].long_name.split(', '))[irridx]

    simy = f.variables['HWAM_county'][:, :, countyidx, :] # simulated yield

with nc(yieldfile) as f: # load objective data
    objt = f.variables['time'][:]
    tunits = f.variables['time'].units
    objt += int(re.findall(r'\d+', tunits)[0]) # years since to years

    obsy = f.variables['yield'][:, countyidx, :] # observed yield

ntime1, ntime2, ntime, ncounties, nirr, nparams = len(time1), len(time2), len(simt), len(counties), len(irridx), simy.shape[1]

sh1 = (ncounties, ntime1, ntime2, nirr)
sopt = masked_array(zeros(sh1), mask = ones(sh1))
rmse = masked_array(zeros(sh1), mask = ones(sh1))
bcor = masked_array(zeros(sh1), mask = ones(sh1))

sh2 = (ncounties, ntime1, ntime2, ntime, nirr)
syld = masked_array(zeros(sh2), mask = ones(sh2))

for c in range(len(countyidx)): # iterate over counties
    for t1, t2 in product(time1, time2): # iterate over time windows
        if t2 >= t1:
            nt = t2 - t1 + 1

            tidx1, tidx2 = time1.index(t1), time2.index(t2)

            simtidx = selyears(simt, t1, t2, skipyears)
            objtidx = selyears(objt, t1, t2, skipyears)

            for i in range(len(irridx)): # iterate over irrigation settings
                simy_slice = simy[simtidx, :, c, irridx[i]].T
                obsy_slice = obsy[objtidx, c, irridx[i]]

                simy_slice = masked_where(simy_slice == 0., simy_slice) / 1000. # convert to masked arrays
                obsy_slice = masked_where(obsy_slice == 0., obsy_slice) / 1000.

                if simy_slice.mask.sum() != simy_slice.size and obsy_slice.mask.sum() != obsy_slice.size:
                    obsy_slice = resize(obsy_slice, (nparams, nt))

                    if shift: # shift ensemble data by observations
                        delta = simy_slice.mean(axis = 0) - obsy_slice.mean(axis = 0)
                        simy_slice -= delta

                    sqerr = (simy_slice - obsy_slice) ** 2 # squared error

                    weights = ones((nparams, nt))
                    if twts: # time weights
                        weights *= resize(wts[-nt :], (nparams, nt))
                    if rwts: # RMSE weights
                        minrmse = sqrt(sqerr.min(axis = 0))
                        minrmse[minrmse < 10.] = 10.
                        weights *= resize(sqrt(10. / minrmse), (nparams, nt))

                    obj = (sqerr * weights).sum(axis = 1) / nt # objective function

                    pidx = argsort(obj)[order - 1] # optimize
                    sopt[c, tidx1, tidx2, i] = pidx + 1

                    rmse[c, tidx1, tidx2, i] = 1000. * sqrt(sqerr[pidx].sum() / nt) # report RMSE

                    syld[c, tidx1, tidx2, :, i] = simy[:, pidx, c, irridx[i]] # report corresponding simulated yield

outfile = outputdir + sep + 'optimal_scenarios_' + str(countyidx[0]).zfill(4) + '.nc4' # zeropad
with nc(outfile, 'w') as f: # write netCDF4
    f.createDimension('time1', ntime1)
    time1var = f.createVariable('time1', 'i4', 'time1')
    time1var[:] = time1
    time1var.units = 'year'
    time1var.long_name = 'start year'

    f.createDimension('time2', ntime2)
    time2var = f.createVariable('time2', 'i4', 'time2')
    time2var[:] = time2
    time2var.units = 'year'
    time2var.long_name = 'end year'

    f.createDimension('county', None) # make UNLIMITED
    countyvar = f.createVariable('county', 'i4', 'county')
    countyvar[:] = counties
    countyvar.units = ''
    countyvar.long_name = 'county index'

    f.createDimension('irr', nirr)
    irrvar = f.createVariable('irr', 'i4', 'irr')
    irrvar[:] = range(1, 1 + nirr)
    irrvar.units = 'mapping'
    irrvar.long_name = ', '.join(irr)

    f.createDimension('time', ntime)
    timevar = f.createVariable('time', 'i4', 'time')
    timevar[:] = simt - simt[0] + 1
    timevar.units = 'growing seasons since %d-01-01 00:00:00' % simt[0] 
    timevar.long_name = 'time'

    scenvar = f.createVariable('scenopt', 'f4', ('county', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    scenvar[:] = sopt
    scenvar.units = ''
    scenvar.long_name = 'optimal scenario'

    rmsevar = f.createVariable('rmse', 'f4', ('county', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    rmsevar[:] = rmse
    rmsevar.units = 'kg/ha'
    rmsevar.long_name = 'optimal RMSE'

    syldvar = f.createVariable('sim_yield', 'f4', ('county', 'time1', 'time2', 'time', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
    syldvar[:] = syld
    syldvar.units = 'kg/ha'
    syldvar.long_name = 'simulated yield'
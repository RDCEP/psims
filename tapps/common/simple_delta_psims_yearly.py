#!/usr/bin/env python

# add paths
import os, sys
for p in os.environ['PATH'].split(':'):
    sys.path.append(p)

# import modules
from calendar import isleap
from datetime import datetime
from netCDF4 import Dataset as nc
from optparse import OptionParser
from pSIMSloader import DailyData, MonthlyData
from numpy import zeros, append, concatenate, arange, reshape

def normalize(vec): return (vec - vec.mean(axis = 0)) / vec.std(axis = 0)

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string", 
                  help = "Input pSIMS file", metavar = "FILE")
parser.add_option("-g", "--gcmfile", dest = "gcmfile", default = "ACCESS1-0.nc4", type = "string",
                  help = "GCM netCDF file", metavar = "FILE")
parser.add_option("-y", "--endyear", dest = "endyear", default = "2050", type = "int",
                  help = "End year of simulation")
parser.add_option("-v", "--variables", dest = "variables", default = "pr,tasmax,tasmin", type = "string",
                  help = "Comma-separated list of variables to shift")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.shift.psims.nc", type = "string",
                  help = "Output pSIMS file", metavar = "FILE")
options, args = parser.parse_args()

psims_in  = options.inputfile
gcm_file  = options.gcmfile
end_year  = options.endyear
variables = options.variables
psims_out = options.outputfile

variables = options.variables.split(',')

# load all daily data
ddat = DailyData(psims_in)

# all variables
allvars = list(ddat.vars)
nvars   = len(allvars)

# get variable units
units = [0] * len(variables)
for i in range(len(variables)):
    units[i] = ddat.units[allvars.index(variables[i])]

# load monthly data
mdat = MonthlyData(gcm_file, ddat.lat, ddat.lon, variables)
mdat.convertUnits(units) # convert units to match daily data

# daily data
dmat = ddat.selYears()

# monthly data
mmat = mdat.selYears()

# monthly averages from daily data
mmatave = ddat.average()

# pr, tmax, tmin indices
dpridx, dmaidx, dmiidx = ddat.pridx, ddat.maidx, ddat.miidx
mpridx, mmaidx, mmiidx = mdat.pridx, mdat.maidx, mdat.miidx

# normalized monthly averages
dpr = normalize(mmatave[dpridx])
dta = normalize(mmatave[[dmaidx, dmiidx]].mean(axis = 0))
mpr = normalize(mmat[mpridx])
mta = normalize(mmat[[mmaidx, mmiidx]].mean(axis = 0))

# all years in daily data
years = range(ddat.startYear(), ddat.endYear() + 1)

# future year range
yr0_futr, yr1_futr = years[-1] + 1, end_year

# future data
ndays = (datetime(yr1_futr, 12, 31) - datetime(yr0_futr, 1, 1)).days + 1
fut_data = zeros((nvars, ndays))

cnt = 0
for i in range(yr1_futr - yr0_futr + 1):
    # future year
    year_futr = yr0_futr + i

    # whether leap year or not
    isleapy = isleap(year_futr)

    # index into monthly data
    yidx = year_futr - mdat.startYear()

    for j in range(12):
        dist = (dpr[:, j] - mpr[yidx, j]) ** 2 + (dta[:, j] - mta[yidx, j]) ** 2
        opt_yidx = dist.argmin()

        pdata = ddat.selMonths(years[opt_yidx], j + 1).copy() # make sure to copy!

        for k in range(len(variables)):
            var_idx = allvars.index(variables[k])

            src = mmatave[var_idx, opt_yidx, j]
            des = mmat[k, yidx, j]

            if k == mpridx:
                if src: pdata[var_idx] *= des / src # multiplicative
            else:
                pdata[var_idx] += des - src # additive

        ndaysm = pdata.shape[1]
        if ndaysm == 29 and not isleapy:
            pdata = pdata[:, : 28]
            ndaysm -= 1
        elif ndaysm == 28 and isleapy:
            pdata = append(pdata, reshape(pdata.mean(axis = 1), (nvars, 1)), axis = 1)        
            ndaysm += 1

        fut_data[:, cnt : cnt + ndaysm] = pdata
        cnt += ndaysm

# concatenate times
time = concatenate((ddat.time, arange(ddat.time[-1] + 1, ddat.time[-1] + 1 + ndays)))
data = concatenate((dmat, fut_data), axis = 1)

with nc(psims_out, 'w') as f:
    f.createDimension('longitude', 1)
    lonvar = f.createVariable('longitude', 'f8', 'longitude')
    lonvar[:] = ddat.lon
    lonvar.units = 'degrees_east'
    lonvar.long_name = 'longitude'

    f.createDimension('latitude', 1)
    latvar = f.createVariable('latitude', 'f8', 'latitude')
    latvar[:] = ddat.lat
    latvar.units = 'degrees_north'
    latvar.long_name = 'latitude'

    f.createDimension('time', None)
    timevar = f.createVariable('time', 'i4', 'time')
    timevar[:] = time
    timevar.units = 'days since %s' % str(ddat.reftime)

    for i in range(nvars):
        vvar = f.createVariable(allvars[i], 'f4', ('time', 'latitude', 'longitude'))
        vvar[:] = data[i]
        vvar.units = ddat.units[i]
        vvar.long_name = ddat.longnames[i]
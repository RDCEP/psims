#!/usr/bin/env python

# add paths
import os, sys
for p in os.environ['PATH'].split(':'):
    sys.path.append(p)

# import modules
from calendar import isleap
from netCDF4 import Dataset as nc
from optparse import OptionParser
from pSIMSloader import DailyData, MonthlyData
from numpy import zeros, append, delete, insert, newaxis, repeat, reshape

class Perturber(object):
    def __init__(self, dailydata, monthlydata):
        self.ddat = dailydata
        self.mdat = monthlydata

        # daily year range
        self.syear1, self.eyear1 = self.ddat.startYear(), self.ddat.endYear()

        # monthly year range
        self.syear2, self.eyear2 = self.mdat.startYear(), self.ddat.startYear() - 1

        # monthly data
        self.mmat = self.mdat.selYears(self.syear2, self.eyear2)

        # monthly averages
        self.mmatave = self.ddat.average()

        # pr, tmax, tmin indices
        self.dpridx = self.ddat.pridx
        self.dmaidx = self.ddat.maidx
        self.dmiidx = self.ddat.miidx
        self.mpridx = self.mdat.pridx
        self.mmaidx = self.mdat.maidx
        self.mmiidx = self.mdat.miidx

        # normalized monthly averages
        self.dpr = self.__normalize(self.mmatave[self.dpridx])
        self.dta = self.__normalize(self.mmatave[[self.dmaidx, self.dmiidx]].mean(axis = 0))
        self.mpr = self.__normalize(self.mmat[self.mpridx])
        self.mta = self.__normalize(self.mmat[[self.mmaidx, self.mmiidx]].mean(axis = 0))        

        # variable names
        self.allvars = list(self.ddat.vars)
        self.monvars = list(self.mdat.vars)

    def perturb(self, year1, year2):
        # year1 - year to exclude
        # year2 - year to match to
        isleapy = isleap(year1)

        years1 = range(self.syear1, self.eyear1 + 1)
        yidx1 = years1.index(year1)
        years1.remove(year1)

        years2 = range(self.syear2, self.eyear2 + 1)
        yidx2 = years2.index(year2)

        # remove year
        mdatac = self.mmatave.copy()
        mdatac = delete(mdatac, yidx1, axis = 1)
        dprc, dtac = self.dpr.copy(), self.dta.copy()
        dprc, dtac = delete(dprc, yidx1, axis = 0), delete(dtac, yidx1, axis = 0)

        perdata = zeros((len(mdatac), 365 + isleapy))
        cnt = 0
        for i in range(12):
            opt_yidx = ((dprc[:, i] - self.mpr[yidx2, i]) ** 2 + \
                        (dtac[:, i] - self.mta[yidx2, i]) ** 2).argmin()

            pdata = ddat.selMonths(years1[opt_yidx], i + 1).copy() # make sure to copy!

            for j in range(len(self.monvars)):
                var_idx = self.allvars.index(self.monvars[j])

                src = mdatac[var_idx, opt_yidx, i]
                des = self.mmat[j, yidx2, i]

                if j == self.mpridx:
                    if src: pdata[var_idx] *= des / src # multiplicative
                else:
                    pdata[var_idx] += des - src # additive

            ndaysm = pdata.shape[1]
            if ndaysm == 29 and not isleapy:
                pdata = pdata[:, : 28]
                ndaysm -= 1
            elif ndaysm == 28 and isleapy:
                pdata = append(pdata, reshape(pdata.mean(axis = 1), (len(mdatac), 1)), axis = 1)        
                ndaysm += 1

            perdata[:, cnt : cnt + ndaysm] = pdata
            cnt += ndaysm

        return perdata

    def __normalize(self, vec): return (vec - vec.mean(axis = 0)) / vec.std(axis = 0)

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string",
                  help = "NetCDF4 file to parse", metavar = "FILE")
parser.add_option("-r", "--refdata", dest = "refdata", default = "pgf2_1901-2012_masked_US.nc4", type = "string",
                  help = "Monthly reference data used to perturb input", metavar = "FILE")
parser.add_option("-v", "--variables", dest = "variables", default = "pr,tasmax,tasmin,rsds", type = "string",
                  help = "Comma-separated list of variables to parse")
parser.add_option("-d", "--day", dest = "day", default = 1, type = "int",
                  help = "Day of year in julian days")
parser.add_option("-y", "--years", dest = "years", default = "", type = "string",
                  help = "Comma-separated year range")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.psims.nc", type = "string",
                  help = "Output pSIMS file", metavar = "FILE")
options, args = parser.parse_args()

inputfile  = options.inputfile
refdata    = options.refdata
variables  = options.variables
day        = options.day
years      = options.years
outputfile = options.outputfile

variables = variables.split(',')
years     = [int(y) for y in years.split(',')]

# full daily data
ddat = DailyData(inputfile)

# get variable units
units = [0] * len(variables)
for i in range(len(variables)):
    units[i] = ddat.units[list(ddat.vars).index(variables[i])]

# full monthly data
mdat = MonthlyData(refdata, ddat.lat, ddat.lon, variables)
mdat.convertUnits(units) # convert units to match daily data

# year range
years = range(years[0], years[-1] + 1)

# monthly year range
myears = range(mdat.startYear(), ddat.startYear())

# daily data for year range
ddatsub = ddat.selYears(years[0], years[-1])

# perturber
ptbr = Perturber(ddat, mdat)

# number of years in daily data
yrfst, yrlst = ddat.startYear(), ddat.endYear()
nyers1 = yrlst - yrfst

# number of years in monthly data
nyers2 = len(myears)

# number of variables and days
nv, nd = ddatsub.shape

# forecasts
fdat = ddatsub[newaxis, ...]
fdat = repeat(fdat, nyers1 + nyers2, axis = 0) # fill with realized data
fdat = fdat.transpose((1, 0, 2))

days = 0
for y in years:
    yersall = range(yrfst, yrlst + 1)
    yersall.remove(y)

    isleapy = isleap(y)
    ndy = 365 + isleapy

    # historical continuations
    for i in range(nyers1):
        cdat = ddat.selYears(yersall[i])

        isleapyi = isleap(yersall[i]) # handle leap years
        if isleapy and not isleapyi:
            cdat = insert(cdat, 59, cdat[:, 30 : 58].mean(axis = 1), axis = 1)
        elif not isleapy and isleapyi:
            cdat = delete(cdat, 59, axis = 1)

        fdat[:, i, days + day - 1 : days + ndy] = cdat[:, day - 1 :]

    # perturbed continuations
    for i in range(nyers2):
        cdat = ptbr.perturb(y, myears[i])
        fdat[:, nyers1 + i, days + day - 1 : days + ndy] = cdat[:, day - 1 :]

    days += ndy

# write pSIMS file with scenario dimension
with nc(outputfile, 'w') as f:
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

    f.createDimension('scen', nyers1 + nyers2)
    scenvar = f.createVariable('scen', 'i4', 'scen')
    scenvar[:] = range(1, 1 + nyers1 + nyers2)
    scenvar.units = 'no'
    scenvar.long_name = 'scenario number'

    f.createDimension('time', nd)
    timevar = f.createVariable('time', 'i4', 'time')
    timevar[:] = range(nd)
    timevar.units = 'days since %d-01-01 00:00:00' % years[0]

    for i in range(nv):
        var = f.createVariable(ddat.vars[i], 'f4', ('scen', 'time', 'latitude', 'longitude'))
        var[:] = fdat[i]
        var.units = ddat.units[i]
        var.long_name = ddat.longnames[i]
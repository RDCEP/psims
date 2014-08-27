#!/usr/bin/env python

# import modules
import os, re, stat, datetime, csv
from netCDF4 import Dataset as nc
from optparse import OptionParser
from collections import OrderedDict as od
from numpy import array, savetxt, zeros, where, double, interp, concatenate, reshape

def writeCL(filename, day, month, year, alldata):
    varnames = ['Max temp', 'min temp', 'radn', 'rainfall', 'co2']
    varfrmts = ['%5.2f  ', '%5.2f ', '%5.2f  ', '%5.2f ', '%3d ']
    ndays, nvars = alldata.shape
    mat = zeros((ndays, nvars + 3))
    mat[:, : nvars]   = alldata
    mat[:, nvars]     = day
    mat[:, nvars + 1] = month
    mat[:, nvars + 2] = [int(str(y)[2 :]) for y in year] # select last two digits
    with open(filename, 'w') as f:
        f.write('* Weather file for CenW\n')
        f.write('* ' + ', '.join(varnames[: nvars]) + ', date (not used)\n')
        f.write('*\n')
        savetxt(f, mat, fmt = varfrmts[: nvars] + ['%d/', '%02d/', '%d'], delimiter = '')
    f = os.open(filename, os.O_RDONLY)
    os.fchmod(f, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    os.close(f)

def indices(dates, startyear, endyear):
    startdate = startyear * 10000 + 1 * 100 + 1
    enddate = endyear * 10000 + 12 * 100 + 31
    startidx = where(dates == startdate)[0][0]
    if enddate > dates[-1]:
        endidx = len(dates)
        idx = range(startidx, endidx)
        ndays = (datetime.datetime(endyear, 12, 31) - datetime.datetime(startyear, 1, 1)).days + 1
        idx += (ndays - len(idx)) * [endidx - 1] # repeat last year
    else:
        endidx = where(dates == enddate)[0][0] + 1
        idx = range(startidx, endidx)
    return idx

def isin(var, varlist):
    vararr = array(varlist)
    patt = re.compile(var + '_*')
    matches = array([bool(patt.match(v)) for v in vararr])
    return list(vararr[matches])

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string", 
                  help = "psims file to parse", metavar = "FILE")
parser.add_option("-v", "--variables", dest = "variables", default = "tmin,tmax,precip,solar", type = "string",
                  help = "Comma-separated list of variables to parse")
parser.add_option("-c", "--co2file", dest = "co2file", default = "", type = "string",
                  help = "csv file of CO2 values", metavar = "FILE")
parser.add_option("-o", "--output", dest = "output", default = "Generic.met", type = "string",
                  help = "Output CL! file pattern")
options, args = parser.parse_args()

variables = options.variables.split(',')

infile = nc(options.inputfile)
vlist  = infile.variables.keys()
time   = infile.variables['time'][:]
tunits = infile.variables['time'].units

varlists = od([('TMAX', ['tmax', 'tasmax']), \
               ('TMIN', ['tmin', 'tasmin']), \
               ('SRAD', ['solar', 'rad', 'rsds', 'srad']), \
               ('RAIN', ['precip', 'pr', 'rain'])])
varnames  = array(varlists.keys())
unitnames = array([['oc', 'degc'], ['oc', 'degc'], ['mj/m^2', 'mj/m2', 'mjm-2'], ['mm']])
varnames  = array(varlists.keys())
alldata   = zeros((len(time), len(varnames)))
for i in range(len(varnames)):
    var_name = varnames[i]
    var_list = varlists[var_name]
    found_var = False
    for v in var_list:
        matchvar = isin(v, variables)
        if matchvar != []:
            matchvar = matchvar[0]
            if matchvar in vlist:
                alldata[:, i] = infile.variables[matchvar][:].squeeze()
                units = '' 
                if 'units' in infile.variables[matchvar].ncattrs():
                    units = infile.variables[matchvar].units
                units = units.lower().replace(' ', '')
                if (var_name == 'TMAX' or var_name == 'TMIN') and units in ['k', 'degrees(k)', 'deg(k)']:
                    alldata[:, i] -= 273.15
                    units = unitnames[i][0]
                elif var_name == 'SRAD' and units in ['wm-2', 'w/m^2', 'w/m2']:
                    alldata[:, i] *= 0.0864
                    units = unitnames[i][0]
                elif var_name == 'RAIN' and units in ['kgm-2s-1', 'kg/m^2/s', 'kg/m2/s']:
                    alldata[:, i] *= 86400
                    units = unitnames[i][0]
                if not units.lower() in unitnames[i]:
                    raise Exception('Unknown units for %s' % var_name)
                found_var = True
                break
    if not found_var:
        raise Exception('Missing necessary variable {:s}'.format(var_name))

ts = tunits.split('days since ')[1].split(' ')
yr0, mth0, day0 = ts[0].split('-')[0 : 3]
if len(ts) > 1:
    hr0, min0, sec0 = ts[1].split(':')[0 : 3]
else:
    hr0 = 0; min0 = 0; sec0 = 0
ref    = datetime.datetime(int(yr0), int(mth0), int(day0), int(hr0), int(min0), int(sec0))
datear = [ref + datetime.timedelta(int(t)) for t in time]
days   = array([d.day for d in datear])
months = array([d.month for d in datear])
years  = array([d.year for d in datear])

dates = years * 10000 + months * 100 + days

co2file = options.co2file
if co2file != '':
    co2reader = csv.reader(open(co2file), delimiter = ',')
    co2data = []
    cnt = 0
    for row in co2reader:
        if cnt:
            year, jday, co2 = row
            d = datetime.datetime(int(year), 1, 1) + datetime.timedelta(int(jday) - 1)
            co2data.append([d.year * 10000 + d.month * 100 + d.day, double(co2)])
        cnt += 1
    co2data = array(co2data)
    co2interp = interp(dates, co2data[:, 0], co2data[:, 1]) # linear interpolate to dates
else:
    co2interp = None # no co2 data

firstyear  = years[0]
lastyear   = years[-1]
yeartostop = lastyear - 30 + 1

cnt = 1
for i in range(firstyear, yeartostop + 1, 5):
    idx = indices(dates, i, i + 49)
    data = alldata[idx]
    if not co2interp is None: # add co2
        co2 = reshape(co2interp[idx], (len(idx), 1))
        data = concatenate((data, co2), axis = 1)
    writeCL(options.output + str(cnt) + '.CL!', days[idx], months[idx], years[idx], data)
    cnt += 1
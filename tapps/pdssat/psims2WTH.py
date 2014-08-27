#!/usr/bin/env python

# import modules
import os, re, stat, datetime
from netCDF4 import Dataset as nc
from optparse import OptionParser
from collections import OrderedDict as od
from numpy.ma import masked_where, is_masked, masked_array
from numpy import empty, array, zeros, reshape, concatenate, savetxt, exp, log, intersect1d, inf, ones

# search for patterns in variable list
def isin(var, varlist):
    vararr = array(varlist)
    patt = re.compile(var + '$|' + var + '_.*')
    matches = array([bool(patt.match(v)) for v in vararr])
    return list(vararr[matches])

# fill gaps in data
def fillgaps(data, time, ref, varname):
    var = masked_array(data)

    for i in range(len(data)):
        isfill = var[i] > 1e10
        var[i] = masked_where(var[i] > 1e10, var[i]) # remove fill values
        var[i] = var[i].astype(float) # convert to float

        if isfill.sum():
            if 100. * isfill.sum() / var[i].size > 1.:
                raise Exception('More than one percent of values for variable %s are masked!' % varname)
            if varname == 'RAIN':
                var[i, isfill] = 0. # fill with zeros
            else:
                days = array([int((ref + datetime.timedelta(int(t))).strftime('%j')) for t in time])
                fdays = days[isfill]
                varave = zeros(len(fdays))
                for j in range(len(fdays)):
                    ave = var[i, days == fdays[j]].mean()
                    varave[j] = ave if not is_masked(ave) else 1e20 
                var[i, isfill] = varave # fill with daily average

    return var

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string",
                  help = "NetCDF3 file to parse", metavar = "FILE")
parser.add_option("-v", "--variables", dest = "variables", default = "time,tmin,tmax,precip,solar", type = "string",
                  help = "Comma-separated list of variables to parse")
parser.add_option("-t", "--tapp", dest = "tapp", default = None, type = "string",
                  help = "Translator app with options separated by semicolons")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.WTH", type = "string",
                  help = "Output WTH file", metavar = "FILE")
options, args = parser.parse_args()

filler, filler2 = -99, 10 # used for ELEV, REFHT, WNDHT, respectively

inputfile  = options.inputfile
variables  = options.variables.split(',')
tapp       = options.tapp
outputfile = options.outputfile

# call translator app if applicable
istmp = False
if not tapp is None:
    tmpfile = inputfile + '.shift'
    tapp += ' -i %s -o %s' % (inputfile, tmpfile) # add input and output file options
    os.system(tapp)
    inputfile = tmpfile
    istmp = True

# open netcdf file
infile = nc(inputfile)

# get time
vlist = infile.variables.keys()
if 'time' in vlist: # make sure time is in file
    time = infile.variables['time'][:]
    time_units = infile.variables['time'].units
else:
    raise Exception('Missing variable time')

# get reference time
ts = time_units.split('days since ')[1].split(' ')
yr0, mth0, day0 = ts[0].split('-')[0 : 3]
if len(ts) > 1:
    hr0, min0, sec0 = ts[1].split(':')[0 : 3]
else:
    hr0 = 0; min0 = 0; sec0 = 0
ref = datetime.datetime(int(yr0), int(mth0), int(day0), int(hr0), int(min0), int(sec0))

# get latitude, longitude
latitude  = infile.variables['latitude'][0]
longitude = infile.variables['longitude'][0]

# get scenarios
ns = infile.variables['scen'].size if 'scen' in infile.variables else 1

# get all data
var_lists = od([('SRAD', ['solar', 'rad', 'rsds', 'srad']), \
                ('TMAX', ['tmax', 'tasmax']), \
                ('TMIN', ['tmin', 'tasmin']), \
                ('RAIN', ['precip', 'pr', 'rain', 'prcp']), \
                ('WIND', ['wind', 'windspeed']), \
                ('DEWP', ['dew', 'dewp', 'dewpoint', 'tdew']), \
                ('HUR',  ['rhum', 'hur']), \
                ('HUS',  ['hus']), \
                ('VAP',  ['vap', 'vapr', 'vap']), \
                ('TAS',  ['tas']), \
                ('PS',   ['ps'])])
unit_names = array([['mj/m^2', 'mj/m2', 'mjm-2', 'mjm-2day-1', 'mjm-2d-1', 'mj/m^2/day', 'mj/m2/day'], \
                    ['oc', 'degc', 'degreesc', 'c'], ['oc', 'degc', 'degreesc', 'c'], ['mm', 'mm/day'], \
                    ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], ['oc', 'degc', 'c'], \
                    ['%'], ['kgkg-1', 'kg/kg'], ['mb'], ['oc', 'degc', 'c'], ['mb']])
var_keys = var_lists.keys()
var_names = array(var_keys)
nt, nv = len(time), len(var_names)
alldata = empty((nv, ns, nt))
found_var = zeros(nv, dtype = bool)
for i in range(nv):
    var_name = var_names[i]
    var_list = var_lists[var_name]

    for v in var_list:
        matchvar = isin(v, variables)
        if matchvar != []:
            matchvar = matchvar[0] # take first match
            if matchvar in vlist:
                alldata[i] = infile.variables[matchvar][:].squeeze()
                alldata[i] = fillgaps(alldata[i], time, ref, var_name)

                units = '' 
                if 'units' in infile.variables[matchvar].ncattrs():
                    units = infile.variables[matchvar].units
                units = units.lower().replace(' ', '')

                # convert units, if necessary
                if var_name == 'SRAD' and units in ['wm-2', 'w/m^2', 'w/m2']: # solar
                    alldata[i] *= 0.0864
                    units = unit_names[i][0]
                elif var_name in ['TMAX', 'TMIN', 'TAS', 'DEWP'] and units in ['k', 'degrees(k)', 'deg(k)']: # temperature
                    alldata[i] -= 273.15
                    units = unit_names[i][0]
                elif var_name == 'RAIN' and units in ['kgm-2s-1', 'kg/m^2/s', 'kg/m2/s']: # precip
                    alldata[i] *= 86400
                    units = unit_names[i][0]
                elif var_name == 'WIND': # wind
                    if units in ['ms-1', 'm/s']:
                        alldata[i] *= 86.4
                        units = unit_names[i][0]
                    elif units in ['kmh-1', 'km/h', 'kmhr-1', 'km/hr']:
                        alldata[i] *= 24
                        units = unit_names[i][0]
                    elif units in ['milesh-1', 'miles/h', 'mileshr-1', 'miles/hr']:
                        alldata[i] *= 38.624256
                        units = unit_names[i][0]
                elif var_name in ['VAP', 'PS'] and units == 'pa': # vapor pressure (mb)
                    alldata[i] /= 100.
                    units = unit_names[i][0]
                elif var_name == 'HUS' and units == 'gkg-1': # specific humidity (kg kg-1)
                    alldata[i] /= 1000.
                    units = unit_names[i][0]
                elif var_name == 'HUR' and units in ['', '0-1']: # relative humidity (%)
                    alldata[i] *= 100.
                    units = unit_names[i][0]

                if not units.lower() in unit_names[i]:
                    raise Exception('Unknown units for %s' % var_name)         

                found_var[i] = True
                break

    if not found_var[i]:
        if var_name == 'SRAD' or var_name == 'TMAX' or var_name == 'TMIN' or var_name == 'RAIN':
            raise Exception('Missing necessary variable {:s}'.format(var_name))

# calculate dewpoint temperature if possible
dewp_idx = var_keys.index('DEWP')
hur_idx  = var_keys.index('HUR')
hus_idx  = var_keys.index('HUS')
vap_idx  = var_keys.index('VAP')
tas_idx  = var_keys.index('TAS')
ps_idx   = var_keys.index('PS')
if not found_var[dewp_idx] and intersect1d(var_lists['DEWP'], variables).size:
    if found_var[vap_idx]: # use vapor pressure
        vap = alldata[vap_idx]
        alldata[dewp_idx] = 4302.65 / (19.4803 - log(vap)) - 243.5
        found_var[dewp_idx] = True
    elif found_var[hur_idx]: # use relative humidity and temperature
        if found_var[tas_idx]:
            T = alldata[tas_idx]
        else:
            tmax_idx = var_keys.index('TMAX')
            tmin_idx = var_keys.index('TMIN')
            T = alldata[[tmax_idx, tmin_idx]].mean(axis = 0) # average
        hur = alldata[hur_idx]
        N = 243.5 * log(0.01 * hur * exp((17.67 * T) / (T + 243.5)))
        D = 22.2752 - log(hur * exp((17.67 * T) / (T + 243.5)))
        alldata[dewp_idx] = N / D
        found_var[dewp_idx] = True
    elif found_var[hus_idx] and found_var[ps_idx]: # use specific humidity and surface pressure
        hus, ps = alldata[hus_idx], alldata[ps_idx]
        hus[hus == 0] = 0.00001
        N = -243.5 * log((2.31034 * hus + 3.80166) / (ps * hus))
        D = log((hus + 1.6455) / (ps * hus)) + 18.5074
        alldata[dewp_idx] = N / D
        found_var[dewp_idx] = True
    else:
        raise Exception('Failed to compute dewpoint temperature')

# close input file
infile.close()

# remove missing nonmandatory variables from array
alldata = alldata[: 6]
found_var = found_var[: 6]
nv = found_var.sum()
var_names = var_names[found_var]
alldata = reshape(alldata[found_var], (nv, ns, nt))

# compute day, month, year for every entry
datear = array([ref + datetime.timedelta(int(t)) for t in time])
days   = array([d.timetuple().tm_yday for d in datear]) # convert to numpy array
months = array([d.month for d in datear])
years  = array([d.year for d in datear])

# compute tav
tmin_idx = var_keys.index('TMIN')
tmax_idx = var_keys.index('TMAX')
tmin = alldata[tmin_idx]
tmax = alldata[tmax_idx]
tav = 0.5 * (tmin.sum(axis = 1) + tmax.sum(axis = 1)) / nt # function of scen

# compute amp
monmax = -inf * ones(ns)
monmin = inf * ones(ns)
for i in range(1, 13):
    ismonth = months == i
    if ismonth.sum():
        t = 0.5 * (tmin[:, ismonth].sum(axis = 1) + tmax[:, ismonth].sum(axis = 1)) / ismonth.sum()
        monmax[t > monmax] = t[t > monmax]
        monmin[t < monmin] = t[t < monmin]
amp = monmax - monmin

# round data
date = (1000 * (years % 100) + days).reshape((nt, 1))
alldata = alldata.round(1)

# ensure that after rounding tmax > tmin and solar > 0.0
bad_idx = alldata[tmax_idx] <= alldata[tmin_idx]
alldata[tmax_idx, bad_idx] = alldata[tmin_idx, bad_idx] + 0.1
alldata[0, alldata[0] <= 0.0] = 0.1

# write files
filenames = [outputfile] if ns == 1 else ['WTH' + str(i).zfill(5) + '.WTH' for i in range(ns)]
for i in range(ns):
    # write header
    head = '*WEATHER DATA : ' + os.path.basename(inputfile) + '\n'
    head += '@ INSI      LAT     LONG  ELEV   TAV   AMP REFHT WNDHT\n    CI'
    head += '%9.3f' % latitude
    head += '%9.3f' % longitude
    head += '%6d' % filler + '%6.1f' % tav[i] + '%6.1f' % amp[i]
    head += '%6d' % filler + '%6d' % filler2 + '\n'
    head += '@DATE  ' + '  '.join(var_names) + '\n'

    # write body
    with open(filenames[i], 'w') as f:
        f.write(head)
        savetxt(f, concatenate((date, alldata[:, i].T), axis = 1), fmt = ['%.5d'] + ['%6.1f'] * nv, delimiter = '')

    # change permissions
    f = os.open(filenames[i], os.O_RDONLY)
    os.fchmod(f, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    os.close(f)

# delete temporary file if necessary
if istmp:
    os.remove(inputfile)
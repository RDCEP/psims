#!/usr/bin/env python

# import modules
from calendar import isleap
from netCDF4 import Dataset as nc
from optparse import OptionParser
from datetime import datetime, timedelta
from numpy.ma import where, masked_where
from numpy import resize, array, zeros, setdiff1d, delete, append, concatenate, reshape, arange

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string", 
                  help = "Input pSIMS file", metavar = "FILE")
parser.add_option("-g", "--gcmfile", dest = "gcmfile", default = "ACCESS1-0.nc4", type = "string",
                  help = "GCM netCDF file", metavar = "FILE")
parser.add_option("-r", "--rcp", dest = "rcp", default = "4.5", type = "string",
                  help = "RCP to use (either 4.5 or 8.5)")
parser.add_option("-y", "--endyear", dest = "endyear", default = "2050", type = "int",
                  help = "End year of simulation")
parser.add_option("-v", "--variables", dest = "variables", default = "pr,tasmax,tasmin", type = "string",
                  help = "Variable names for precipitation, maximum and minimum temperatures, in that order")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.shift.psims.nc", type = "string",
                  help = "Output pSIMS file", metavar = "FILE")
parser.add_option("--noshift", action = "store_true", dest = "noshift", default = False,
                  help = "Whether to not shift the data (default = False)")
options, args = parser.parse_args()

decs = arange(2010, 2100, 10) # 2010, 2020, . . ., 2090

psims_in  = options.inputfile
gcm_file  = options.gcmfile
rcp       = options.rcp
end_year  = options.endyear
variables = options.variables
psims_out = options.outputfile
noshift   = options.noshift

rcp = rcp.replace('.', '')
if not rcp in ['45', '85']: raise Exception('Unknown RCP')

pr_name, ma_name, mi_name = variables.split(',')

with nc(psims_in) as f:
    lat, lon = f.variables['latitude'][:], f.variables['longitude'][:] # lat, lon

    time = f.variables['time'][:] # time
    tunits = f.variables['time'].units

    vars = f.variables.keys()
    vars = setdiff1d(vars, ['longitude', 'latitude', 'time'])

    nv, nt = len(vars), len(time)

    data = zeros((nv, nt))
    units, long_names = [0] * nv, [0] * nv

    pr_var = f.variables[pr_name] # pr
    data[0] = pr_var[:, 0, 0]
    units[0] = pr_var.units
    long_names[0] = pr_var.long_name

    ma_var = f.variables[ma_name] # ma
    data[1] = ma_var[:, 0, 0]
    units[1] = ma_var.units
    long_names[1] = ma_var.long_name

    mi_var = f.variables[mi_name] # mi
    data[2] = mi_var[:, 0, 0]
    units[2] = mi_var.units
    long_names[2] = mi_var.long_name

    rem_vars = setdiff1d(vars, [pr_name, ma_name, mi_name])
    for i in range(len(rem_vars)):
        var = f.variables[rem_vars[i]]
        data[i + 3] = var[:, 0, 0]
        units[i + 3] = var.units
        long_names[i + 3] = var.long_name

ts = tunits.split('days since ')[1].split(' ')
yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
if len(ts) > 1:
    hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
else:
    hr0 = min0 = sec0 = 0
refdate = datetime(yr0, mth0, day0, hr0, min0, sec0)

with nc(gcm_file) as f:
    glat, glon = f.variables['lat'][:], f.variables['lon'][:]
    land_mask = f.variables['meanpr_hist'][0, 0, :, :].mask.T # land mask

    glatd = resize(glat, (len(glon), len(glat))).T - lat
    glond = resize(glon, (len(glat), len(glon))) - lon
    gtotd = glatd ** 2 + glond ** 2
    gtotd = masked_where(land_mask, gtotd) # apply land mask
    latidx, lonidx = where(gtotd == gtotd.min())
    latidx, lonidx = latidx[0], lonidx[0] # use first

    mean_pr_hist = f.variables['meanpr_hist'][:, :, lonidx, latidx].mean(axis = 0)
    mean_ma_hist = f.variables['meantasmax_hist'][:, :, lonidx, latidx].mean(axis = 0)
    mean_mi_hist = f.variables['meantasmin_hist'][:, :, lonidx, latidx].mean(axis = 0)

    mean_pr_rcp = f.variables['meanpr_rcp' + rcp][:, :, lonidx, latidx]
    mean_ma_rcp = f.variables['meantasmax_rcp' + rcp][:, :, lonidx, latidx]
    mean_mi_rcp = f.variables['meantasmin_rcp' + rcp][:, :, lonidx, latidx]

# year ranges
yr0_hist = (refdate + timedelta(int(time[0]))).year
yr1_hist = (refdate + timedelta(int(time[-1]))).year
yr0_futr = yr1_hist + 1
yr1_futr = end_year

# number of years
nyrs_hist = yr1_hist - yr0_hist + 1
nyrs_futr = yr1_futr - yr0_futr + 1

# future data
ndays = (datetime(yr1_futr, 12, 31) - datetime(yr0_futr, 1, 1)).days + 1
fut_data = zeros((nv, ndays))

cnt_hist = cnt_futr = 0
for i in range(nyrs_futr):
    # historical year
    hist_idx = cnt_hist % nyrs_hist
    year_hist = yr0_hist + hist_idx

    # future year
    year_futr = yr0_futr + i

    # which decade year is in
    dec_idx = where(decs <= year_futr)[0][-1]

    # deltas
    mean_pr_delta = mean_pr_rcp[dec_idx] / mean_pr_hist
    mean_ma_delta = mean_ma_rcp[dec_idx] - mean_ma_hist
    mean_mi_delta = mean_mi_rcp[dec_idx] - mean_mi_hist

    mean_pr_delta[mean_pr_delta > 3.] = 3. # cap pr delta at 300%

    # historical data
    idx1 = where(time == (datetime(year_hist, 1, 1) - refdate).days)[0][0]
    idx2 = where(time == (datetime(year_hist, 12, 31) - refdate).days)[0][0]
    data_hist = data[:, idx1 : idx2 + 1].copy() # make copy

    # perturb data
    if not noshift:
        month = array([(refdate + timedelta(t)).month for t in range(idx1, idx2 + 1)])
        for m in range(1, 13):
            is_month = month == m
            data_hist[0, is_month] *= mean_pr_delta[m - 1] # pr
            data_hist[1, is_month] += mean_ma_delta[m - 1] # ma
            data_hist[2, is_month] += mean_mi_delta[m - 1] # mi

    data_hist[0, data_hist[0] > 999.9] = 999.9 # cap pr at 999.9

    mi_gt = data_hist[1] < data_hist[2] # ensure tasmax > tasmin
    data_hist[1, mi_gt] = (data_hist[1, mi_gt] + data_hist[2, mi_gt]) / 2. + 0.1
    data_hist[2, mi_gt] = data_hist[1, mi_gt] - 0.2

    lp_fut, lp_hist = isleap(year_futr), isleap(year_hist)
    if lp_fut and not lp_hist:
        data_hist = append(data_hist, reshape(data_hist[:, -1], (nv, 1)), axis = 1) # add day
    elif not lp_fut and lp_hist:
        data_hist = delete(data_hist, 59, axis = 1) # remove day

    fut_data[:, cnt_futr : cnt_futr + 365 + lp_fut] = data_hist

    cnt_hist += 1
    cnt_futr += 365 + lp_fut

# concatenate times
time = concatenate((time, arange(time[-1] + 1, time[-1] + 1 + ndays)))
data = concatenate((data, fut_data), axis = 1)

with nc(psims_out, 'w') as f:
    f.createDimension('longitude', 1)
    lonvar = f.createVariable('longitude', 'f8', 'longitude')
    lonvar[:] = lon
    lonvar.units = 'degrees_east'
    lonvar.long_name = 'longitude'

    f.createDimension('latitude', 1)
    latvar = f.createVariable('latitude', 'f8', 'latitude')
    latvar[:] = lat
    latvar.units = 'degrees_north'
    latvar.long_name = 'latitude'

    f.createDimension('time', None)
    timevar = f.createVariable('time', 'i4', 'time')
    timevar[:] = time
    timevar.units = 'days since %s' % str(refdate)

    vars = [pr_name, ma_name, mi_name] + list(rem_vars)
    for i in range(len(vars)):
        vvar = f.createVariable(vars[i], 'f4', ('time', 'latitude', 'longitude'))
        vvar[:] = data[i]
        vvar.units = units[i]
        vvar.long_name = long_names[i]
#!/usr/bin/env python

# import modules
from shutil import copyfile
from numpy import resize, array
from netCDF4 import Dataset as nc
from optparse import OptionParser
from datetime import datetime, timedelta
from numpy.ma import where, masked_where

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.psims.nc", type = "string", 
                  help = "Input pSIMS file", metavar = "FILE")
parser.add_option("-g", "--gcmfile", dest = "gcmfile", default = "ACCESS1-0.nc4", type = "string",
                  help = "GCM netCDF file", metavar = "FILE")
parser.add_option("-r", "--rcp", dest = "rcp", default = "4.5", type = "string",
                  help = "RCP to use (either 4.5 or 8.5)")
parser.add_option("-d", "--decades", dest = "decades", default = "1,2,3", type = "string",
                  help = "Comma-separated list of decades to use (e.g., 1,2,3)")
parser.add_option("-v", "--variables", dest = "variables", default = "pr,tasmax,tasmin", type = "string",
                  help = "Variable names for precipitation, maximum and minimum temperatures, in that order")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.shift.psims.nc", type = "string",
                  help = "Output pSIMS file", metavar = "FILE")
options, args = parser.parse_args()

psims_in = options.inputfile
psims_out = options.outputfile

gcm_file = options.gcmfile
rcp = options.rcp
fut_decades = options.decades
variables = options.variables

copyfile(psims_in, psims_out) # make copy

rcp = rcp.replace('.', '')
if not rcp in ['45', '85']: raise Exception('Unknown RCP')

fut_decades = [int(d) - 1 for d in fut_decades.split(',')]

pr_name, ma_name, mi_name = variables.split(',')

with nc(psims_in) as f:
    lat, lon = f.variables['latitude'][:], f.variables['longitude'][:]
    time = f.variables['time'][:]
    tunits = f.variables['time'].units
    pr = f.variables[pr_name][:].squeeze()
    ma = f.variables[ma_name][:].squeeze()
    mi = f.variables[mi_name][:].squeeze()

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

    mean_pr_hist = f.variables['meanpr_hist'][:, :, lonidx, latidx].squeeze() # 3 x 12
    mean_ma_hist = f.variables['meantasmax_hist'][:, :, lonidx, latidx].squeeze()
    mean_mi_hist = f.variables['meantasmin_hist'][:, :, lonidx, latidx].squeeze()

    mean_pr_rcp = f.variables['meanpr_rcp' + rcp][fut_decades, :, lonidx, latidx].squeeze()
    mean_ma_rcp = f.variables['meantasmax_rcp' + rcp][fut_decades, :, lonidx, latidx].squeeze()
    mean_mi_rcp = f.variables['meantasmin_rcp' + rcp][fut_decades, :, lonidx, latidx].squeeze()

mean_pr_delta = mean_pr_rcp.mean(axis = 0) / mean_pr_hist.mean(axis = 0)
mean_ma_delta = mean_ma_rcp.mean(axis = 0) - mean_ma_hist.mean(axis = 0)
mean_mi_delta = mean_mi_rcp.mean(axis = 0) - mean_mi_hist.mean(axis = 0)

mean_pr_delta[mean_pr_delta > 3.] = 3. # cap pr delta at 300%

month = array([(refdate + timedelta(int(t))).month for t in time])

pr_shifted = pr.copy()
ma_shifted = ma.copy()
mi_shifted = mi.copy()

for m in range(1, 13):
    is_month = month == m
    pr_shifted[is_month] = pr[is_month] * mean_pr_delta[m - 1]
    ma_shifted[is_month] = ma[is_month] + mean_ma_delta[m - 1]
    mi_shifted[is_month] = mi[is_month] + mean_mi_delta[m - 1]

pr_shifted[pr_shifted > 999.9] = 999.9 # cap pr at 999.9

is_mi_greater = ma_shifted < mi_shifted # ensure tasmax > tasmin
ma_shifted[is_mi_greater] = (ma_shifted[is_mi_greater] + mi_shifted[is_mi_greater]) / 2. + 0.1
mi_shifted[is_mi_greater] = ma_shifted[is_mi_greater] - 0.2

with nc(psims_out, 'a') as f:
    pr = f.variables[pr_name]
    pr[:] = pr_shifted
    ma = f.variables[ma_name]
    ma[:] = ma_shifted
    mi = f.variables[mi_name]
    mi[:] = mi_shifted

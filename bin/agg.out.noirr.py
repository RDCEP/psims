#!/usr/bin/env python

# add paths
import os, sys
for p in os.environ['PATH'].split(':'): sys.path.append(p)

# import modules
from optparse import OptionParser
from netCDF4 import Dataset as nc
from averager import MeanAverager
from numpy.ma import masked_where
from aggmaskloader import AggMaskLoader
from numpy import logical_and, logical_not, double, where

def createAggFile(filename, time, tunits, adata, anames, aunits, alongnames, scens, leaddim):
    if leaddim == 'scen':
        nscens = None
        ntime  = len(time)
    else:
        nscens = len(scens)
        ntime  = None

    with nc(filename, 'w', format = 'NETCDF4_CLASSIC') as f:
        f.createDimension('time', ntime)
        timevar = f.createVariable('time', 'i4', 'time')
        timevar[:] = time
        timevar.units = tunits
        timevar.long_name = 'time'
        f.createDimension('scen', nscens)
        scenvar = f.createVariable('scen', 'i4', 'scen')
        scenvar[:] = scens
        scenvar.units = 'no'
        scenvar.long_name = 'scenarios'
        for i in range(len(anames)):
            rname = anames[i] + '_index'
            f.createDimension(rname, len(adata[i]))
            rvar = f.createVariable(rname, 'i4', rname)
            rvar[:] = adata[i]
            rvar.units = aunits[i]
            rvar.long_name = alongnames[i]

def getyieldmask(yieldvar, yieldthr1 = 0.1, yieldthr2 = 30):
    yieldm = masked_where(yieldvar < yieldthr1, yieldvar)
    yieldm = masked_where(yieldm > yieldthr2, yieldm)
    return logical_not(yieldm.mask)

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "input", default = "", type = "string",
                  help = "File to aggregate:var 1,var 2,...,var M")
parser.add_option("-w", "--weights", dest = "weights", default = None, type = "string",
                  help = "Weights file (optional)", metavar = "FILE")
parser.add_option("-a", "--agg", dest = "agg", default = "", type = "string",
                  help = "Aggregation file")
parser.add_option("-n", "--numchunks", dest = "numchunks", default = 1, type = int,
                  help = "Number of chunks to split the data into (default = 1)")
parser.add_option("-s", "--scen", dest = "scen", default = None, type = "string",
                  help = "Comma-separated list of scenarios to aggregate (default = all)")
parser.add_option("-l", "--leaddim", dest = "leaddim", default = "scen", type = "string",
                  help = "Lead dimension of output file (default = scen)")
parser.add_option("-o", "--output", dest = "output", default = "", type = "string",
                  help = "Output file", metavar = "FILE")
parser.add_option("-y", "--yieldvar", dest = "yieldvar", default = None, type = "string",
                  help = "Name of yield variable (optional)")
parser.add_option("--ll_lim", dest = "lllim", default = None, type = "string",
                  help = "llat,ulat,llon,ulon representing bounding box (optional)")
parser.add_option("--calc_area", action = "store_true", dest = "calcarea", default = False,
                  help = "Flag to indicate weights are fractions (optional)")
options, args = parser.parse_args()

inputf    = options.input
lllim     = options.lllim
weightsf  = options.weights
aggf      = options.agg
numchunks = options.numchunks
scen      = options.scen
yieldvar  = options.yieldvar
calcarea  = options.calcarea
leaddim   = options.leaddim
outputf   = options.output

if not leaddim in ['scen', 'time']: raise Exception('Unknown lead dimension')

yieldthr1, yieldthr2 = 90, 30000 # yield thresholds (kg/ha)
tol = 1e-5 # tolerance for comparisons

ifile, ivars = [i.strip() for i in inputf.split(':')]
ivars = [v.strip() for v in ivars.split(',')]
nvars = len(ivars)
var = [0] * nvars; dims = [0] * nvars; vunits = [0] * nvars
with nc(ifile) as f:
    lats, lons = f.variables['lat'][:], f.variables['lon'][:]

    t = f.variables['time']
    time = t[:]
    tunits = t.units if 'units' in t.ncattrs() else ''

    scenall = f.variables['scen'][:]
    if scen is None:
        scensel = scenall.copy()
        scenidx = range(len(scenall))
    else:
        scensel = [int(s) for s in scen.split(',')]
        scenidx = [0] * len(scensel)
        for i in range(len(scensel)):
            scenidx[i] = where(scenall == scensel[i])[0][0]

    for i in range(nvars):
        v = f.variables[ivars[i]]
        dims[i] = v.dimensions
        slicer = [slice(0, n) for n in v.shape]
        slicer[dims[i].index('scen')] = scenidx
        var[i] = v[slicer] # select scenarios
        vunits[i] = v.units if 'units' in v.ncattrs() else ''

    if yieldvar:
        yieldv = f.variables[yieldvar][:, :, :, scenidx] # pull yield

if lllim:
    llat, ulat, llon, ulon = [double(lim) for lim in lllim.split(',')]
    sellat = logical_and(lats >= llat - tol, lats <= ulat + tol)
    sellon = logical_and(lons >= llon - tol, lons <= ulon + tol)
    lats, lons = lats[sellat], lons[sellon]
    for i in range(nvars):
        var[i] = var[i][sellat][:, sellon]
else:
    llat, ulat = lats.min(), lats.max()
    llon, ulon = lons.min(), lons.max()

weights = None
if weightsf:
    with nc(weightsf) as f:
        wlats, wlons = f.variables['lat'][:], f.variables['lon'][:]
        sellat = logical_and(wlats >= llat - tol, wlats <= ulat + tol)
        sellon = logical_and(wlons >= llon - tol, wlons <= ulon + tol)
        wlats, wlons = wlats[sellat], wlons[sellon]        

        if abs(lats - wlats).max() > tol:
            raise Exception('Latitudes in output file and weights mask do not agree!')
        if abs(lons - wlons).max() > tol:
            raise Exception('Longitudes in output file and weights mask do not agree!')

        weights = f.variables['weights'][sellat][:, sellon]

aggloader  = AggMaskLoader(aggf, lats = lats, lons = lons)
adata      = aggloader.data()
audata     = aggloader.udata()
anames     = aggloader.names()
aunits     = aggloader.units()
alongnames = aggloader.longnames()
alats      = aggloader.latitudes()
alons      = aggloader.longitudes()

if abs(lats - alats).max() > tol:
    raise Exception('Latitudes in output file and aggregation mask do not agree!')
if abs(lons - alons).max() > tol:
    raise Exception('Longitudes in output file and aggregation mask do not agree!')

createAggFile(outputf, time, tunits, audata, anames, aunits, alongnames, scensel, leaddim)
f = nc(outputf, 'a')

avobj = MeanAverager()
for i in range(len(audata)):
    if leaddim == 'scen':
        dimsv = ('scen', 'time', anames[i] + '_index')
    else:
        dimsv = ('time', 'scen', anames[i] + '_index')

    for j in range(nvars):
        avev = f.createVariable(ivars[j] + '_' + anames[i], 'f4', dimsv, fill_value = 1e20, zlib = True, complevel = 9)
        avev.units = vunits[j]
        avev.long_name = 'average ' + anames[i] + ' ' + ivars[j]

        slicer = [slice(0, n) for n in var[j].shape]
        dimslist = list(dims[j])
        dimslist.remove('scen')
        timeidx, latidx, lonidx = dimslist.index('time'), dimslist.index('lat'), dimslist.index('lon')

        for k in range(len(scensel)):
            slicer[dims[j].index('scen')] = k
            data = var[j][slicer].transpose((timeidx, latidx, lonidx))

            if yieldvar:
                yld = yieldv[slicer].transpose((timeidx, latidx, lonidx))
                yldmask = getyieldmask(yld, yieldthr1, yieldthr2)
            else:
                yldmask = None

            data = avobj.av(data, adata[i], lats, weights, calcarea = calcarea, mask = yldmask, numchunks = numchunks)

            if leaddim == 'scen':
                avev[k, :, :] = data.transpose((1, 0))
            else:
                avev[:, k, :] = data.transpose((1, 0))

f.close()

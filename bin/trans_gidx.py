#!/usr/bin/env python

import sys
from os.path import isfile, sep
from numpy import double, floor

def translate(lat, lon, latdelta, londelta):
    latidx = int(floor((90. - lat) / latdelta + 1))
    lonidx = int(floor((lon + 180.) / londelta + 1))

    lat1 = 90. - latdelta * (latidx - 1)
    lat2 = 90. - latdelta * latidx
    lon1 = -180. + londelta * (lonidx - 1)
    lon2 = -180. + londelta * lonidx

    if lat > lat1 or lat < lat2 or lon < lon1 or lon > lon2:
        raise Exception('Not in cell!')

    return latidx, lonidx

if len(sys.argv) != 6:
    print 'Usage: trans_gidx.py latidx1 lonidx1 lat_delta1[,lon_delta1] lat_delta2[,lon_delta2] weathdir2'
    sys.exit(1)

latidx    = int(sys.argv[1])
lonidx    = int(sys.argv[2])
delta1    = [double(d) / 60. for d in sys.argv[3].split(',')] # arcminutes -> degrees
delta2    = [double(d) / 60. for d in sys.argv[4].split(',')]
weathdir2 = sys.argv[5]

if len(delta1) == 1:
    latdelta1 = londelta1 = delta1[0]
else:
    latdelta1, londelta1 = delta1
if len(delta2) == 1:
    latdelta2 = londelta2 = delta2[0]
else:
    latdelta2, londelta2 = delta2

latrat, lonrat = latdelta2 / latdelta1, londelta2 / londelta1

latd  = [0.5, 0, 1, 0, 1] # start at center
lond  = [0.5, 0, 0, 1, 1]
latd += [0.5 + i for i in [0,       0,      latrat, -latrat, latrat,  latrat, -latrat, -latrat]]
lond += [0.5 + i for i in [lonrat, -lonrat, 0,       0,      lonrat, -lonrat,  lonrat, -lonrat]]

lats = [90. - latdelta1 * (latidx - i) for i in latd]
lons = [-180. + londelta1 * (lonidx - i) for i in lond]

for i in range(len(lats)):
    latidx2, lonidx2 = translate(lats[i], lons[i], latdelta2, londelta2)
    latidx2, lonidx2 = '%03d' % latidx2, '%03d' % lonidx2
    wfile = sep.join([weathdir2, latidx2, lonidx2, '%s_%s.psims.nc' % (latidx2, lonidx2)])
    if isfile(wfile):
        print latidx2 + sep + lonidx2
        sys.exit(0) # success

sys.exit(1) # failure

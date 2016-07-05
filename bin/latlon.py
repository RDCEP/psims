#!/usr/bin/env python
#
# Convert a latitude and longitude to grid point
#

import argparse,math

def latlon_to_grid(delta, lat, lon, padding=4):
    delta = delta / 60.
    latidx = int(math.floor((90. - lat) / delta + 1))
    lonidx = int(math.floor((lon + 180.) / delta + 1))
    return "%s/%s" % (str(latidx).zfill(padding), str(lonidx).zfill(padding))

parser = argparse.ArgumentParser()
parser.add_argument('-lat', dest="lat", required=True, type=float, help='Latitude')
parser.add_argument('-lon', dest="lon", required=True, type=float, help='Longitude')
parser.add_argument('-delta', dest="delta", required=True, type=int, help='Simulation Delta')
parser.add_argument('-tdelta', dest="tdelta", required=True, type=int, help='Tile Delta')
args = parser.parse_args()

# Verify valid lat and lon values
if args.lat > 90 or args.lat < -90:
    print "Invalid lat %f" % args.lat
    sys.exit(-1)
if args.lon > 180 or args.lon < -180:
    print "Invalid lon %f" % args.lon
    sys.exit(-1)

# Compute latidx and lonidx
print "Tile grid: %s" % latlon_to_grid(args.tdelta, args.lat, args.lon)
print "Sims grid: %s" % latlon_to_grid(args.delta, args.lat, args.lon)

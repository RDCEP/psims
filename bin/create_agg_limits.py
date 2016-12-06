#!/usr/bin/env python

# import modules
# from re import findall
from shutil import copyfile
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import isMaskedArray
from numpy import setdiff1d, unique, resize, where, zeros, diff

# def higherLevel(level):
#     num = findall(r'\d+', level)
# 
#     if len(num):
#         num = int(num[0])
#         levtype = ''.join(i for i in level if not i.isdigit())
#         return levtype + str(num - 1)
#     else:
#         return []

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--inputfile", dest = "inputfile", default = "", type = "string",
                  help = "Input file")
parser.add_option("-o", "--outputfile", dest = "outputfile", default = "", type = "string",
                  help = "Output file")
options, args = parser.parse_args()

inputfile  = options.inputfile
outputfile = options.outputfile

copyfile(inputfile, outputfile)

with nc(outputfile, 'a') as f:
    lats, lons = f.variables['lat'][:], f.variables['lon'][:]
    dlat, dlon = abs(diff(lats)[0]), abs(diff(lons)[0])

    latd = resize(lats, (len(lons), len(lats))).T
    lond = resize(lons, (len(lats), len(lons)))

    levels = [str(s) for s in setdiff1d(f.variables.keys(), ['lat', 'lon'])]

    f.createDimension('bnds', 2)
    bndvar = f.createVariable('bnds', 'i4', 'bnds')
    bndvar[:] = [1, 2]
    bndvar.units = 'mapping'
    bndvar.long_name = 'lower, upper'

    for lev in levels:
        levg = f.variables[lev][:]

        levvals = unique(levg)
        if isMaskedArray(levvals):
            levvals = levvals[~levvals.mask]

        nlevs = len(levvals)

        # lhigh = higherLevel(lev)
        # if lhigh in levels:
        #     lhighg = f.variables[lhigh][:]
        #     lhigh_in_lev = zeros(nlevs)

        latbnds = zeros((nlevs, 2))
        lonbnds = zeros((nlevs, 2))
        for i in range(nlevs):
            latidx, lonidx = where(levg == levvals[i])
            latlev = latd[latidx, lonidx]
            lonlev = lond[latidx, lonidx]

            latbnds[i] = [latlev.min() - dlat / 2., latlev.max() + dlat / 2.]
            lonbnds[i] = [lonlev.min() - dlon / 2., lonlev.max() + dlon / 2.]

            # if lhigh in levels:
            #     uniql = unique(lhighg[latidx, lonidx])
            #     if len(uniql) == 1:
            #         lhigh_in_lev[i] = uniql[0]
            #     else:
            #         max_cnts = 0
            #         for j in range(len(uniql)):
            #             cnt = (lhighg[latidx, lonidx] == uniql[j]).sum()
            #             if not j or cnt > max_cnts:
            #                 idx = j
            #                 max_cnts = cnt
            #         lhigh_in_lev[i] = uniql[idx]

        f.createDimension('lev_' + lev, nlevs)
        levvar = f.createVariable('lev_' + lev, 'f8', ('lev_' + lev), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
        levvar[:] = levvals

        latbndvar = f.createVariable('latbnds_' + lev, 'f4', ('lev_' + lev, 'bnds'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
        latbndvar[:] = latbnds
        latbndvar.units = 'degrees_north'
        latbndvar.long_name = 'latitude bounds for ' + lev

        lonbndvar = f.createVariable('lonbnds_' + lev, 'f4', ('lev_' + lev, 'bnds'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
        lonbndvar[:] = lonbnds
        lonbndvar.units = 'degrees_east'
        lonbndvar.long_name = 'longitude bounds for ' + lev

        # if lhigh in levels:
        #     lvar = f.createVariable(lhigh + '_in_' + lev, 'f4', 'lev_' + lev, zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
        #     lvar[:] = lhigh_in_lev

#!/usr/bin/env python

# add paths
import os
import sys
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '../utils'))

# import modules
import glob
from nco import Nco
from re import findall
from .. import translator
from datetime import datetime
from pSIMSloader import foundVar
from netCDF4 import Dataset as nc
from numpy import double, diff, logical_and, where, array

def apply_prefix(files, prefix):
    for idx,f in enumerate(files):
        files[idx] = os.path.join(prefix, f)
    return files

def key_func(x):
    return os.path.split(x)[-1]

def list_tiles(path):
    return sorted(glob.glob(path), key=key_func)

def param_to_list(param):
    if isinstance(param, basestring):
        return param.split(',')
    return param

def inputs_to_outputs(inputs):
    outputs = []
    for idx,i in enumerate(inputs):
        outputs.append(os.path.basename(i).replace('.tile', ''))
    return outputs

class TileTranslator(translator.Translator):

    def run(self, latidx, lonidx):
        try:
            inputfile_dir      = self.config.get_dict(self.translator_type, 'inputfile_dir', default = os.path.join('..', '..'))
            inputfiles         = self.config.get_dict(self.translator_type, 'inputfile')
            variables          = self.config.get_dict(self.translator_type, 'variables', default = None)
            slicefirst         = self.config.get_dict(self.translator_type, 'slicefirst', default = False)
            latdelta, londelta = [double(d) / 60 for d in self.config.get('delta').split(',')] # convert to degrees
            refyear            = self.config.get('ref_year')
            numyears           = self.config.get('num_years')

            if inputfiles:
                inputfiles = param_to_list(inputfiles)
                inputfiles = apply_prefix(inputfiles, inputfile_dir)
            else:
                inputfiles = list_tiles(os.path.join(inputfile_dir, '*.clim.tile.nc4'))

            outputfiles = self.config.get_dict(self.translator_type, 'outputfile', default = inputs_to_outputs(inputfiles))
            outputfiles = param_to_list(outputfiles)

            if variables:
                variables = variables.split(',')

            nco = Nco()

            for i in range(len(inputfiles)):
                inputfile  = inputfiles[i]
                outputfile = outputfiles[i]

                with nc(inputfile) as f:
                    lats, lons = f.variables['lat'][:], f.variables['lon'][:]
                    varkeys    = array(f.variables.keys())
                    flatdelta  = abs(diff(lats)[0]) # assume uniform grid
                    flondelta  = abs(diff(lons)[0])

                    if slicefirst and not i:
                        time = f.variables['time'][:].astype(int) # convert to integers
                        refyeari = int(findall(r'\d+', f.variables['time'].units)[0])

                        ndays0 = (datetime(refyear, 1, 1) - datetime(refyeari, 1, 1)).days
                        ndays1 = (datetime(refyear + numyears, 12, 31) - datetime(refyeari, 1, 1)).days

                        tidx0 = where(time == ndays0)[0][0] if ndays0 in time else 0
                        tidx1 = where(time == ndays1)[0][0] if ndays1 in time else len(time) - 1

                if flatdelta > latdelta:
                    minlat = 90 - latdelta * (latidx - 0.5)
                    maxlat = minlat
                else:
                    minlat = 90 - latdelta * latidx
                    maxlat = minlat + latdelta
                if flondelta > londelta:
                    minlon = -180 + londelta * (lonidx - 0.5)
                    maxlon = minlon
                else:
                    minlon = -180 + londelta * (lonidx - 1)
                    maxlon = minlon + londelta

                # lookup variables
                if variables:
                    varnames = [0] * len(variables)
                    for j in range(len(variables)):
                        idx = foundVar(varkeys, variables[j])
                        if not len(idx):
                            raise Exception('Variable %s not found in file %s' % (variables[j], inputfile))
                        varnames[j] = str(','.join(varkeys[idx]))

                # basic options
                options = '-h -a lat,lon -d lat,%f,%f -d lon,%f,%f --rd' % (minlat, maxlat, minlon, maxlon)

                # select time
                if slicefirst and not i and (tidx0 != 0 or tidx1 != len(time) - 1):
                    options += ' -d time,%d,%d' % (tidx0, tidx1)

                # select variables
                if variables:
                    options += ' -v %s' % ','.join(varnames)

                # average over space
                if logical_and(lats >= minlat, lats <= maxlat).sum() > 1 or logical_and(lons >= minlon, lons <= maxlon).sum() > 1:
                    options += ' -w cropland'

                # average over latitude, longitude
                nco.ncwa(input = inputfile, output = outputfile, options = options);

                # change latitude, longitude to simulated point
                with nc(outputfile, 'a') as f:
                    latv = f.variables['lat']
                    latv[:] = 90 - latdelta * (latidx - 0.5)
                    lonv = f.variables['lon']
                    lonv[:] = -180 + londelta * (lonidx - 0.5)

            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

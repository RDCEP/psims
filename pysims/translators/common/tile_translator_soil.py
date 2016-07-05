#!/usr/bin/env python

# add paths
import os
import sys
import traceback
sys.path.append('../utils')

# import modules
from nco import Nco
from numpy import double
from .. import translator
from netCDF4 import Dataset as nc
import os

def param_to_list(param):
    if isinstance(param, basestring):
        return param.split(',')
    return param

def apply_prefix(files, prefix):
    for idx,f in enumerate(files):
        files[idx] = os.path.join(prefix, f)
    return files

def inputs_to_outputs(inputs):
    outputs = []
    for idx,i in enumerate(inputs):
        outputs.append(os.path.basename(i).replace('.tile', ''))
    return outputs

class SoilTileTranslator(translator.Translator):

    def run(self, latidx, lonidx):
        try:
            inputfile_dir      = self.config.get_dict(self.translator_type, 'inputfile_dir', default=os.path.join('..', '..'))
            inputfiles         = self.config.get_dict(self.translator_type, 'inputfile', default='1.soil.tile.nc4')
            inputfiles         = param_to_list(inputfiles)
            latdelta, londelta = [double(d) / 60 for d in self.config.get('delta').split(',')] # convert to degrees
            nco                = Nco()
            outputfiles        = self.config.get_dict(self.translator_type, 'outputfile', default=inputs_to_outputs(inputfiles))

            outputfiles        = param_to_list(outputfiles)
            inputfiles         = apply_prefix(inputfiles, inputfile_dir)

            for i in range(len(inputfiles)):
                inputfile  = inputfiles[i]
                outputfile = outputfiles[i]

                with nc(inputfile) as f:
                    variables = f.variables.keys()
                    soil_id   = f.getncattr('soil_id')

                # get latitude, longitude limits
                minlat = 90 - latdelta * latidx
                maxlat = minlat + latdelta
                minlon = -180 + londelta * (lonidx - 1)
                maxlon = minlon + londelta

                # additional options
                options = '-h -a lat,lon -d lat,%f,%f -d lon,%f,%f --rd' % (minlat, maxlat, minlon, maxlon)
                if 'cropland' in variables:
                    options += ' -w cropland'

                # perform aggregation
                nco.ncwa(input = inputfile, output = outputfile, options = options);

                # add degenerate profile dimension
                nco.ncecat(input = outputfile, output = outputfile, options = '-O -h -u profile')
                nco.ncap2(input = outputfile, output = outputfile, options = '-O -h -s profile[profile]=1')

                # add soil_id variable
                nco.ncap2(input = outputfile, output = outputfile, options = '-O -h -s soil_id[profile,lat,lon]=1')
                nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a units,soil_id,c,c,"mapping"')
                nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a long_name,soil_id,c,c,"%s"' % str(soil_id))
                nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a soil_id,global,d,c,""')

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

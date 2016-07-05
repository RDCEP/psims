#!/usr/bin/env python

# import modules
import sys,os
sys.path.append("%s/translators/utils" % os.path.dirname(__file__))

from nco import Nco
from fnmatch import filter
from os import listdir, sep
from shutil import copyfile
from os.path import basename
from os import rename, system
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import masked_array
import configuration.configuration
from numpy import setdiff1d, double, zeros, ones, arange, ceil
import multiprocessing

def combinelat(prefix, inputdir, outputfile, daily, year):
    try:    
        if daily:
            files = [inputdir + sep + f for f in filter(listdir(inputdir), '%s*.%d.psims.nc' % (prefix, year))]
        else:
            files = [inputdir + sep + f for f in filter(listdir(inputdir), '%s*.psims.nc' % prefix)]

        # tile latitude and longitude indices
        latidx = [int(basename(f).split('_')[1][: 4]) for f in files]
        
        # variables
        with nc(files[0]) as f:
            vars = setdiff1d(f.variables.keys(), ['time', 'scen', 'irr', 'lat', 'lon'])
        
        # fill longitude gaps
        for idx in setdiff1d(fulllatidx, latidx):
            if daily:
                latfile = inputdir + sep + '%s_%04d.%d.psims.nc' % (prefix, idx, year)
            else:
                latfile = inputdir + sep + '%s_%04d.psims.nc' % (prefix, idx)
            copyfile(files[0], latfile)
            lats = arange(90 - tlatd * (idx - 1) - latd / 2., 90 - tlatd * idx, -latd)
            with nc(latfile, 'a') as f:
                latvar = f.variables['lat']
                latvar[:] = lats
                for i in range(len(vars)):
                    var = f.variables[vars[i]]
                    var[:] = masked_array(zeros(var.shape), mask = ones(var.shape))
            files.append(latfile)

        # output file
        nco = Nco()

        # concatenate all files
        if daily:
            inputfiles = ' '.join([inputdir + sep + '%s_%04d.%d.psims.nc' % (prefix, idx, year) for idx in fulllatidx])
        else:
            inputfiles = ' '.join([inputdir + sep + '%s_%04d.psims.nc' % (prefix, idx) for idx in fulllatidx])
        nco.ncrcat(input = inputfiles, output = outputfile, options = '-h')

        # make time lead dimension
        if timelead:
            nco.ncpdq(input = outputfile, output = outputfile, options = '-O -h -a time,lat')

        # limit spatial extent to sim grid
        nco.ncks(input = outputfile, output = outputfile, options = '-O -h -d lat,%f,%f' % (lat1, lat0))

        # compress
        system('nccopy -d9 -k4 %s %s' % (outputfile, outputfile + '.tmp'))
        rename(outputfile + '.tmp', outputfile)
    except:
        print "[%s] %s" % (os.path.basename(__file__), traceback.format_exc())

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--inputdir", dest = "inputdir", default = ".", type = "string",
                  help = "Directory containing output files for each latitude band")
parser.add_option("-p", "--params", dest = "params", default = "params.dssat45.sample", type = "string",
                  help = "Parameter file", metavar = "FILE")
parser.add_option("-o", "--outputdir", dest = "outputdir", default = ".", type = "string",
                  help = "Output directory to save final file")
parser.add_option('-s', '--split', dest='split', type=int, help='Split value')
options, args = parser.parse_args()

inputdir      = options.inputdir
params        = options.params
outputdir     = options.outputdir
split         = options.split
config        = configuration.configuration.YAMLConfiguration(params)
nlats         = config.get('num_lats')
lat0          = config.get('lat_zero')
delta         = config.get('delta')
tdelta        = config.get('tdelta')
timelead      = bool(config.get('make_time_lead', default = True))
outputfile    = config.get('out_file')
dailyvars     = config.get('daily_variables')
daily_combine = config.get('daily_combine', default = True)
ref_year      = config.get('ref_year')
num_years     = config.get('num_years')
nlats         = int(nlats)
lat0          = double(lat0)
latd, _       = [double(d) / 60 for d in delta.split(',')]
tlatd, _      = [double(d) / 60 for d in tdelta.split(',')]
lat1          = lat0 - nlats * latd
tlatd        /= split

# full tile latitude indices
tlatidx0   = int((90 - lat0) / tlatd + 1)
ntlat      = int(ceil(nlats * latd / tlatd))
fulllatidx = range(tlatidx0, tlatidx0 + ntlat)

pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
standard_outputfile = outputdir + sep + outputfile + '.nc4'
pool.apply_async(combinelat, ["output", inputdir, standard_outputfile, False, None])

if dailyvars and daily_combine:
    for year in range(ref_year, ref_year+num_years):
        daily_outputfile = outputdir + sep + outputfile + '.daily.%d.nc4' % year
        pool.apply_async(combinelat, ["daily", inputdir, daily_outputfile, True, year])

pool.close()
pool.join()

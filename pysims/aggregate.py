#!/usr/bin/env python

# import modules
import datetime
import os
import sys
import tempfile
import traceback
from nco import Nco
import multiprocessing
from shutil import rmtree
from os.path import exists
from shutil import copyfile
from subprocess import Popen
from numpy.ma import masked_where
from netCDF4 import Dataset as nc
from optparse import OptionParser
from os import remove, makedirs, sep
from numpy import where, diff, isnan, ceil, double
from configuration.configuration import YAMLConfiguration

def run_nco(nco_obj, action, input, output, options):
    command = "%s %s %s %s" % (action, options, "--output=%s" % output, input)
    print "%s pid=%d %s" % (datetime.datetime.now(), os.getpid(), command)
    try:
        p = Popen(command, shell = True)
        p.wait()
    except:
        print "%s\n" % traceback.format_exc()
    print "Task completed at %s: %s" % (datetime.datetime.now(), command)

def aggregate(inputfile, outputfile, variable, level, region):
    try:
        # get lat/lon extents, etc.
        with nc(inputfile) as f:
            vidx = where(f.variables['lev_' + level][:] == region)[0][0]
            latlower, latupper = f.variables['latbnds_' + level][vidx]
            lonlower, lonupper = f.variables['lonbnds_' + level][vidx]

        regselect = '-d lat,%f,%f -d lon,%f,%f' % (latlower, latupper, lonlower, lonupper)
        nco = Nco()

        # average rainfed, irrigated
        options = '-h -B \'%s == %d\' -w weight -a lat,lon %s' % (level, region, regselect)
        run_nco(nco, 'ncwa', input = inputfile, output = outputfile, options = options)
        with nc(outputfile) as f:
            udim = str(f.variables[variable].dimensions[0])
        run_nco(nco, 'ncks',  input = outputfile, output = outputfile, options = '-O -h --mk_rec_dim irr')
        run_nco(nco, 'ncpdq', input = outputfile, output = outputfile, options = '-O -h -a irr,%s' % udim)
        run_nco(nco, 'ncks',  input = outputfile, output = outputfile, options = '-O -h -v %s' % variable)

        # replace NaNs with zeros
        with nc(outputfile, 'a') as f:
            var = f.variables[variable]
            vararr = var[:]
            vararr = masked_where(isnan(vararr), vararr)
            var[:] = vararr

        # total area
        tmpfile1 = next(tempfile._get_candidate_names())
        run_nco(nco, 'ncks', input = inputfile, output = tmpfile1,   options = '-h -v %s,weight' % level)
        run_nco(nco, 'ncwa', input = tmpfile1,  output = tmpfile1,   options = '-O -h -B \'%s == %d\' -N -a lat,lon %s' % (level, region, regselect))
        run_nco(nco, 'ncks', input = tmpfile1,  output = outputfile, options = '-h -A')
        remove(tmpfile1)

        # sum
        tmpfile2 = next(tempfile._get_candidate_names())
        run_nco(nco, 'ncwa',   input = outputfile, output = tmpfile2, options = '-h -a irr -w weight')
        run_nco(nco, 'ncecat', input = tmpfile2,   output = tmpfile2, options = '-O -h -u irr')
        run_nco(nco, 'ncap2',  input = tmpfile2,   output = tmpfile2, options = '-O -h -s "irr[irr]=3"')

        # concatenate sum
        run_nco(nco, 'ncks', input = outputfile, output = outputfile, options = '-O -v %s' % variable)
        run_nco(nco, 'ncrcat', input = '%s %s' % (outputfile, tmpfile2), output = outputfile, options = '-O -h')
        remove(tmpfile2)

        # create level dimension
        run_nco(nco, 'ncecat', input = outputfile, output = outputfile, options = '-O -h -u %s' % level)
        run_nco(nco, 'ncap2',  input = outputfile, output = outputfile, options = '-O -h -s "%s[%s]=%d"' % (level, level, region))

    except:
        print "%s\n" % traceback.format_exc()

def is_file(filename):
    if os.path.exists(filename):
        return True
    else:
        return False

def verify_params(config):
    aggfile    = param.get_dict('aggregator', 'aggfile')
    weightfile = param.get_dict('aggregator', 'weightfile')
    if not is_file(aggfile):
        return False
    if not is_file(weightfile):
        return False
    return True

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--rundir", dest = "rundir", default = "", type = "string",
                  help = "Run directory")
parser.add_option("-p", "--paramfile", dest = "paramfile", default = "", type = "string",
                  help = "Param file")
parser.add_option("-v", "--variable", dest = "variable", default = "", type = "string",
                  help = "Variable to aggregate")
parser.add_option("-c", "--chunk", dest = "chunk", default = 1, type = int,
                  help = "Chunk number")
parser.add_option("-l", "--level", dest = "level", default = False, type = "string",
                  help = "Level to aggregate")
parser.add_option("-r", "--region", dest = "region", default = False, type = int,
                  help = "Region to aggregate")
parser.add_option("-s", "--sanity", dest = "sanity", action='store_true',
                  help = "Run sanity checker only")
options, args = parser.parse_args()

chunk     = options.chunk
rundir    = options.rundir
paramfile = options.paramfile
variable  = options.variable
level     = options.level
region    = options.region
param     = YAMLConfiguration(paramfile)

if not param.get('aggregator'):
    exit(0)

inputfile  = param.get('out_file')
weightfile = param.get_dict('aggregator', 'weightfile')
aggfile    = param.get_dict('aggregator', 'aggfile')
levels     = param.get_dict('aggregator', 'levels').split(',')
chunkdim   = param.get_dict('aggregator', 'chunkdim', default = 'time')
numchunks  = param.get_dict('aggregator', 'numchunks', default = 1)
inputfile  = '%s/%s.nc4'      % (rundir, inputfile)
outputfile = '%s.agg.%s.%04d' % (inputfile, variable, chunk)

# Sanity check
if options.sanity:
    passed = verify_params(param)
    if passed:
        sys.exit(0)
    else:
        sys.exit(1)

# get lat/lon extents and number of times/scens
with nc(inputfile) as f:
    lats, lons     = f.variables['lat'][:], f.variables['lon'][:]
    dlat, dlon     = abs(diff(lats)[0]), abs(diff(lons)[0])
    minlat, maxlat = lats.min() - dlat / 2, lats.max() + dlat / 2.
    minlon, maxlon = lons.min() - dlon / 2, lons.max() + dlon / 2.
    ntimes, nscens = len(f.variables['time']), len(f.variables['scen'])

# get chunk information
ntasks  = ntimes if chunkdim == 'time' else nscens
jobsize = int(ceil(double(ntasks) / numchunks))
sidx    = jobsize * (chunk - 1)
eidx    = min(sidx + jobsize - 1, ntasks - 1)

chunkselect = '-d %s,%d,%d' % (chunkdim, sidx, eidx) if numchunks > 1 else ''

if sidx >= ntasks:
    print 'No tasks to process for chunk %d. Exiting . . .' % chunk
    exit(0)

# get level values
regions = {}
with nc(aggfile) as f:
    for lev in levels:
        regions[lev] = f.variables['lev_' + lev][:]

# make temporary directory
tempdir = os.getcwd() + sep + 'temp.%s.%04d' % (variable, chunk)
if not exists(tempdir):
    makedirs(tempdir)

nco = Nco()

# extract variable
tempinput = tempdir + sep + next(tempfile._get_candidate_names())
run_nco(nco, 'ncks', input = inputfile, output = tempinput, options = '-h -v %s %s' % (variable, chunkselect))

# append weight and agg files to input
for f in [weightfile, aggfile]:
    options = '-h -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
    with nc(f) as ncf:
        if chunkdim in ncf.dimensions:
            if len(ncf.dimensions[chunkdim]) != ntasks:
                raise Exception('Length of %s in file %s not consistent with input file' % (chunkdim, f))
            options += ' ' + chunkselect
    tempf = tempdir + sep + next(tempfile._get_candidate_names())
    run_nco(nco, 'ncks', input = f, output = tempf, options = options)
    run_nco(nco, 'ncks', input = tempf, output = tempinput, options = '-h -A')
    remove(tempf)

if level and region:
    aggregate(tempinput, outputfile, variable, level, region)
    run_nco(nco, 'ncpdq', input = outputfile, output = outputfile, options = '-O -h -a %s,%s' % (chunkdim, level))

    with nc(outputfile) as f:
        irr = str(f.variables['irr'].long_name)

    run_nco(nco, 'ncrename', input = outputfile, output = outputfile, options = '-O -h -v %s,%s_%s' % (variable, variable, level))
    run_nco(nco, 'ncatted',  input = outputfile, output = outputfile, options = '-O -h -a long_name,irr,m,c,"%s, sum"' % irr)
else:
    pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
    for lev in levels:
        reglist = list(set(regions[lev].tolist()))
        for reg in reglist:
            outputfileLR = tempdir + sep + 'tempfile.%s.%09d' % (lev, reg)
            pool.apply_async(aggregate, [tempinput, outputfileLR, variable, lev, reg])
    pool.close()
    pool.join()

    # concatenate and append
    for i in range(len(levels)):
        outputfileL = tempdir + sep + 'tempfile.%s' % levels[i]
        run_nco(nco, 'ncrcat', input = tempdir + sep + 'tempfile.%s.*' % levels[i], output = outputfileL, options = '-h')
        run_nco(nco, 'ncpdq', input = outputfileL, output = outputfileL, options = '-O -h -a %s,%s' % (chunkdim, levels[i]))
        run_nco(nco, 'ncrename', input = outputfileL, output = outputfileL, options = '-O -h -v %s,%s_%s' % (variable, variable, levels[i]))

        if not i:
            copyfile(outputfileL, outputfile)
        else:
            run_nco(nco, 'ncks', input = outputfileL, output = outputfile, options = '-h -A')

    with nc(outputfile) as f:
        irr = str(f.variables['irr'].long_name)

    # change irr attribute
    run_nco(nco, 'ncatted', input = outputfile, output = outputfile, options = '-O -h -a long_name,irr,m,c,"%s, sum"' % irr)

# remove temporary directory
rmtree(tempdir)

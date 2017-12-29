#!/usr/bin/env python
import argparse
import collections
import configuration.configuration
import dill
import errno
import glob
import multiprocessing
import os
import shutil
import sys
import tarfile
import traceback
import time
import models.model_factory as model_factory
import translators.translator_factory as translator_factory
import checkers.checker_factory as checker_factory
from nco import Nco
from fnmatch import filter
from numpy import double, arange, ceil

# Run a single translator
def run_translator(latidx, lonidx, translator, method='run'):
    translator_name = type(translator).__name__
    start_time = time.time()
    passed = getattr(translator, method)(latidx, lonidx)
    stop_time = time.time()
    print "%04d/%04d, %s, %s, %f, %s" % (latidx, lonidx, translator_name, method, stop_time-start_time, passed)
    return passed

# Process a tile
def process_tile(latidx, lonidx, translators_p):
    translators = dill.loads(translators_p)
    point_directory = os.path.join('%04d' % latidx, '%04d' % lonidx)
    mkdir_p(point_directory)
    os.chdir(point_directory)
    run_single_model(latidx, lonidx, translators)
    os.chdir('../..')

# Run a single invocation of a model (and any relevant translators)
def run_single_model(latidx, lonidx, translators):
    single_translators   = [('checker', 'run'),
                            ('stage_inputs_translator', 'run'),
                            ('soil_tile_translator', 'run'),
                            ('clim_tile_translator', 'run'),
                            ('merge_inputs', 'run'),
                            ('campaign_translator', 'run'),
                            ('pretranslator', 'run'),
                            ('weather_translator', 'run'),
                            ('input_translator', 'run'),
                            ('model', 'run'),
                            ('output_translator', 'run'),
                            ('stage_outputs_translator', 'run')]

    backup_translator = ('nooutput_translator', 'run')

    # Single translators
    for trans_data in single_translators:
        translator, method = trans_data
        success = run_translator(latidx, lonidx, translators[translator], method)

        if not success:
            translator, method = backup_translator
            run_translator(latidx, lonidx, translators[translator], method)
            return

# Simulate mkdir -p (no errors if a directory already exists)
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

# Combine given a single latidx
def combine(latidx, lonidx, output):
    try:
        files = ['outputs/%s' % file for file in filter(os.listdir('outputs'), 'output_%04d_*.psims.nc' % latidx)]
        for f in files:
            nco.ncpdq(input=f, output=f, options='-O -h -a lon,time');
        nco.ncrcat(input='outputs/output_%04d_*.psims.nc' % latidx, output=output, options='-h')
        nco.ncpdq(input=output, output=output, options='-O -h -a lat,lon')
    except:
        print "[%s] (%s/%s): %s" % (os.path.basename(__file__), latidx, lonidx, traceback.format_exc())

# Combine given a single latidx
def combine_daily(latidx, lonidx, year, output):
    try:
        files = ['outputs/%s' % file for file in filter(os.listdir('outputs'), 'daily_%04d_*.%04d.psims.nc' % (latidx, year))]
        for f in files:
            nco.ncpdq(input=f, output=f, options='-O -h -a lon,time');
        nco.ncrcat(input='outputs/daily_%04d_*.%04d.psims.nc' % (latidx, year), output=output, options='-h')
        nco.ncpdq(input=output, output=output, options='-O -h -a lat,lon')
    except:
       print "[%s] (%s/%s): %s" % (os.path.basename(__file__), latidx, lonidx, traceback.format_exc())

# Parse command line arguments
parser = argparse.ArgumentParser(description='pSIMS - The parallel system for integrating impact models and sectors')
parser.add_argument('--campaign', dest='campaign', required=True, help='Campaign directory')
parser.add_argument('--debug', dest='debug', default=False, action='store_true', help='Force failure for debugging')
parser.add_argument('--debug_dir', dest='debug_dir', help='Debug/failure root directory')
parser.add_argument('--debug_max', dest='debug_max', default=10, help='Maximum number of debug/failure directories')
parser.add_argument('--latidx', dest='latidx', required=False, type=int, help='Optional point latitude index to only run a single point')
parser.add_argument('--lonidx', dest='lonidx', required=False, type=int, help='Optional point longitude index to only run a single point')
parser.add_argument('--param', '--params', dest='params', required=True, help='Param file')
parser.add_argument('--test', dest='test', required=False, help='File containing known simulation results')
parser.add_argument('--tlatidx', dest='tlatidx', required=True, help='Tile latitude index')
parser.add_argument('--tlonidx', dest='tlonidx', required=True, help='Tile longitude index')
parser.add_argument('--slatidx', dest='slatidx', required=False, default=1, help='Split latitude index')
parser.add_argument('--slonidx', dest='slonidx', required=False, default=1, help='Split longitude index')
parser.add_argument('--split', dest='split', required=False, type=int, default=1, help='Number of splits')
parser.add_argument('--rundir', dest='rundir', required=False, default=None, help='psims runXXX directory to push data to')
args = parser.parse_args()

# Set some additional config values based on command line arguments
config = configuration.configuration.YAMLConfiguration(args.params)
config.set('campaign',  args.campaign)
config.set('debug',     args.debug)
config.set('debug_dir', args.debug_dir)
config.set('debug_max', args.debug_max)
config.set('tlatidx',   args.tlatidx)
config.set('tlonidx',   args.tlonidx)
config.set('params',    args.params)
config.set('test',      args.test)
config.set('rundir',    args.rundir)
config.set('slatidx',   args.slatidx)
config.set('slonidx',   args.slonidx)
config.set('split',     args.split)

# Set simulation deltas
delta_list = str(config.get('delta')).split(',')
if len(delta_list) == 1:
   latdelta = double(delta_list[0])
   londelta = latdelta
elif len(delta_list) == 2:
   latdelta = double(delta_list[0])
   londelta = double(delta_list[1])
else:
    sys.exit("Invalid delta value. Please specify 1, 2, or 4 values.")

# Set tile deltas and indices
tdelta_list = str(config.get('tdelta')).split(',')
if len(tdelta_list) == 1:
   tlatdelta = double(tdelta_list[0])
   tlondelta = tlatdelta
elif len(tdelta_list) == 2 or len(tdelta_list) == 4:
   tlatdelta = double(tdelta_list[0])
   tlondelta = double(tdelta_list[1])
else:
   sys.exit("Invalid tdelta value. Please specify 1, 2, or 4 values.")

config.set('latdelta',  latdelta)
config.set('londelta',  londelta)
config.set('tlatdelta', tlatdelta)
config.set('tlondelta', tlondelta)

ref_year      = config.get('ref_year')
num_years     = config.get('num_years')
daily         = config.get('daily_variables')
daily_combine = config.get('daily_combine', default=True)

# Instantiate model
model_factory_obj = model_factory.ModelFactory()
model             = model_factory_obj.create_model(config)

# Checker
checker_factory_obj = checker_factory.CheckerFactory()
checker             = checker_factory_obj.create_checker(config, 'checker')

# Instantiate translators
translator_factory_obj   = translator_factory.TranslatorFactory()
campaign_translator      = translator_factory_obj.create_translator(config, "tappcmp")
clim_tile_translator     = translator_factory_obj.create_translator(config, 'tapptilewth')
input_translator         = translator_factory_obj.create_translator(config, "tappinp")
merge_inputs             = translator_factory_obj.create_translator(config, 'mergeinputs')
nooutput_translator      = translator_factory_obj.create_translator(config, 'tappnooutput')
output_translator        = translator_factory_obj.create_translator(config, "postprocess")
pretranslator            = translator_factory_obj.create_translator(config, "pretranslator")
soil_tile_translator     = translator_factory_obj.create_translator(config, 'tapptilesoil')
stage_inputs_translator  = translator_factory_obj.create_translator(config, 'stageinputs')
stage_outputs_translator = translator_factory_obj.create_translator(config, 'stageoutputs')
tile_translator          = translator_factory_obj.create_translator(config, 'tapptile')
weather_translator       = translator_factory_obj.create_translator(config, "tappwth")

# Set names and order of translators
translators = collections.OrderedDict()
translators['campaign_translator']      = campaign_translator
translators['checker']                  = checker
translators['clim_tile_translator']     = clim_tile_translator
translators['input_translator']         = input_translator
translators['merge_inputs']             = merge_inputs
translators['model']                    = model
translators['nooutput_translator']      = nooutput_translator
translators['output_translator']        = output_translator
translators['pretranslator']            = pretranslator
translators['soil_tile_translator']     = soil_tile_translator
translators['stage_inputs_translator']  = stage_inputs_translator
translators['stage_outputs_translator'] = stage_outputs_translator
translators['weather_translator']       = weather_translator
translators_p = dill.dumps(translators)

# Simulation deltas
latdelta, londelta = [double(d) for d in config.get('delta').split(',')]

# Tile deltas and indices
tlatdelta, tlondelta = [double(d) for d in config.get('tdelta').split(',')]
tlatidx,   tlonidx   = int(args.tlatidx), int(args.tlonidx)

# Subtile deltas and indices
split      = int(args.split)
slatidx    = int(args.slatidx)
slonidx    = int(args.slonidx)
tslatdelta = tlatdelta / split
tslondelta = tlondelta / split
tslatidx   = split * (tlatidx - 1) + slatidx
tslonidx   = split * (tlonidx - 1) + slonidx

# Stage tile inputs
result = run_translator(tlatidx, tlonidx, stage_inputs_translator, method='run_tile')
if not result:
    sys.exit('Error staging in tile inputs')

mkdir_p('outputs')
pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
part_directories = []

# Debug with just a single point
if args.latidx and args.lonidx:
    process_tile(args.latidx, args.lonidx, translators_p)
    sys.exit(0)
# Process all points in the tile in parallel
else:
    for i in arange(1, tslatdelta / latdelta + 1):
        for j in arange(1, tslondelta / londelta + 1):
            latidx = int((tlatdelta * (tlatidx - 1) + tslatdelta * (slatidx - 1) + latdelta * i) / latdelta)
            lonidx = int((tlondelta * (tlonidx - 1) + tslondelta * (slonidx - 1) + londelta * j) / londelta)
            part_directories.append('%04d/%04d' % (latidx, lonidx))
            pool.apply_async(process_tile, [latidx, lonidx, translators_p])
    pool.close()
    pool.join()

# Create tarballs
print "Creating tarballs"
outtypes = config.get('outtypes').split(',')
tar_filename = 'outputs/outputs_%04d_%04d.tar' % (tslatidx, tslonidx)
outputs_tar = tarfile.open(tar_filename, 'w')
for dir in part_directories:
    os.chdir(dir)
    tar = tarfile.open('output.tar.gz', 'w:gz')
    for outtype in outtypes:
        for outfile in glob.glob('*%s' % outtype):
            tar.add(outfile)
    tar.close()
    os.chdir('../..')
    outputs_tar.add('%s/output.tar.gz' % dir)
outputs_tar.close()

# Combine
files_to_remove = []
files_to_copy   = []
print "Running combine"
nco = Nco()
pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
for i in arange(1, tslatdelta / latdelta + 1):
    latidx = int((tlatdelta * (tlatidx - 1) + tslatdelta * (slatidx - 1) + latdelta * i) / latdelta)
    filename = 'output_%04d.psims.nc' % latidx
    files_to_remove.append(filename)
    pool.apply_async(combine, [latidx, lonidx, filename])
pool.close()
pool.join()

# Daily combine
if daily and daily_combine:
    print "Running combine daily"
    pool = multiprocessing.Pool(processes = multiprocessing.cpu_count())
    for i in arange(1, tslatdelta / latdelta + 1):
        for year in range(ref_year, ref_year + num_years):
            latidx = int((tlatdelta * (tlatidx - 1) + tslatdelta * (slatidx - 1) + latdelta * i) / latdelta)
            filename = 'daily_%04d.%04d.psims.nc' % (latidx, year)
            files_to_remove.append(filename)
            pool.apply_async(combine_daily, [latidx, lonidx, year, filename])
    pool.close()
    pool.join()

# Concatenate along latitude and permute dimensions of final file
print "Running concat"
part_directory = os.path.join('parts', '%04d' % tslatidx)
finalfile = os.path.join(part_directory, 'output_%04d_%04d.psims.nc' % (tslatidx, tslonidx))
files_to_copy.append(finalfile)
mkdir_p(part_directory)
nco.ncrcat(input = 'output_*.psims.nc', output = finalfile, options = '-h')
nco.ncpdq(input = finalfile, output = finalfile, options = '-O -h -a lon,lat')
nco.ncpdq(input = finalfile, output = finalfile, options = '-O -h -a time,lon')

# Concatenate along latitude and permute dimensions of final file
if daily and daily_combine:
    print "Running concat daily"
    for year in range(ref_year, ref_year + num_years):
        part_directory = os.path.join('parts', '%04d' % tslatidx)
        finalfile_daily = os.path.join(part_directory, 'daily_%04d_%04d.%04d.psims.nc' % (tslatidx, tslonidx, year))
        files_to_copy.append(finalfile_daily)
        mkdir_p(part_directory)
        nco.ncrcat(input = 'daily_*.%04d.psims.nc' % year, output = finalfile_daily, options = '-h')
        nco.ncpdq(input = finalfile_daily, output = finalfile_daily, options = '-O -h -a lon,lat')
        nco.ncpdq(input = finalfile_daily, output = finalfile_daily, options = '-O -h -a time,lon')

# Stage outputs
result = run_translator(tlatidx, tlonidx, stage_outputs_translator, method='run_tile')
if not result:
    sys.exit('Error staging in tile inputs')

# Remove intermediates
for file in files_to_remove:
    os.remove(file)

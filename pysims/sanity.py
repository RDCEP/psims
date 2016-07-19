#!/usr/bin/env python
#
# This program is a parameter file sanity checker used by psims to determine is a run should proceed
#
import argparse
import datetime
import gzip
import netCDF4
import os
import sys
import yaml
from colorama import init, Fore, Style
import configuration.configuration
import translators.translator_factory as translator_factory
import checkers.checker_factory as checker_factory

# Exit with error if test fails
def assert_true(passed):
    check = Fore.GREEN + 'o' + Style.RESET_ALL
    fail  = Fore.RED + 'x' + Style.RESET_ALL
    if passed[0]:
        print check + " " + passed[1]
    else:
        sys.exit(fail + " " + passed[1])

# Is a parameter defined?
def is_defined(name, value):
    if value:
        return (True, "%s is defined" % name)
    else:
        return (False, "%s is not defined!" % name)

# Is a list empty?
def is_not_empty(name, value):
    if len(value) > 0:
        return (True, "%s is defined" % name)
    else:
        return (False, "%s is undefined!" % name)

# Does the parameter value/directory exist?
def is_directory(name, value):
    if os.path.isdir(value):
        return (True, "%s directory exists" % name)
    else:
        return (False, "%s directory %s does not exist!" % (name, value))

# Is a parameter value/file executable?
def is_executable(name, value):
    if os.access(value, os.X_OK):
        return (True, "%s has execution bit" % name)
    else:
        return (False, "%s file %s does not have execution bit!" % (name, value))

# Does a parameter value/file exist?
def is_file(name, value):
    if os.path.exists(value):
        return (True, "%s file exists" % name)
    else:
        return (False, "%s file %s does not exist!" % (name, value))

# Is the parameter value/file NetCDF?
def is_netcdf(name, value):
    try:
        netCDF4.Dataset(value, 'r')
        return (True, "%s tile is NetCDF" % name)
    except:
        return (False, "%s file %s is not a NetCDF" % (name, value))

# Is the parameter value/file gzipped?
def is_gzip(name, value):
    try:
        gfile = gzip.GzipFile(value, 'r')
        return (True, "%s is gzipped" % (name))
    except:
        return (False, "%s file %s is not gzipped" % (name, value))

# Is the parameter value/file YAML?
def is_yaml(name, value):
    try:
        yaml.load(open(value))
        return (True, "%s file is YAML" % name)
    except:
        return (False, "%s file is not YAML, check formatting" % (name, value))

# Run a test for system command. An exit code of 0 passes, anything else fails
def test_system(command):
    try:
        ec = os.system(command)
        exe = os.path.basename(command.split(' ')[0])
        if ec == 0:
            return (True, "%s likes the parameters" % exe)
        return (False, "%s failed" % exe)
    except:
        return (False, "%s failed" % exe)

# Parse command line arguments
parser = argparse.ArgumentParser(description='pSIMS params sanity checker')
parser.add_argument('--campaign', dest='campaign', required=True, help='Campaign directory')
parser.add_argument('--param', '--params', dest='params', required=True, help='Param file')
parser.add_argument('--tlatidx', dest='tlatidx', required=True, help='Tile latitude index')
parser.add_argument('--tlonidx', dest='tlonidx', required=True, help='Tile longitude index')
args = parser.parse_args()

print "\nRunning Sanity checks on parameter file %s" % args.params

# Basic param testsa
assert_true(is_file('params', args.params))
assert_true(is_yaml('params', args.params))

# Set some additional config values based on command line arguments
config = configuration.configuration.YAMLConfiguration(args.params)
config.set('campaign',  args.campaign)
config.set('tlatidx',   args.tlatidx)
config.set('tlonidx',   args.tlonidx)
config.set('params',    args.params)

init()

# Weather tests
weathers = []
for w in config.get('weather', default="").split(','):
    if w:
        weathers.append(w)
for w in config.get_dict('stageinputs', 'weather', default=""):
    if w:
        weathers.append(w)
assert_true(is_not_empty("weather", weathers))
for weather in weathers:
    assert_true(is_directory('weather', weather))
    wth_tile_dir = os.path.join(weather, config.get('tlatidx'))
    assert_true(is_directory('weather tile', wth_tile_dir))
    wth_tile = os.path.join(wth_tile_dir, "clim_%s_%s.tile.nc4" % (config.get('tlatidx'), config.get('tlonidx')))
    assert_true(is_file('weather tile', wth_tile))
    assert_true(is_netcdf('weather netcdf', wth_tile))

# Soil tests
soils = []
for s in config.get('soils', default="").split(','):
    if s:
        soils.append(s)
for s in config.get_dict('stageinputs', 'soils', default=""):
    if s:
        soils.append(s)
assert_true(is_not_empty("soils", soils))
for soil in soils:
    assert_true(is_directory('soils', soil))
    soils_tile_dir = os.path.join(soil, config.get('tlatidx'))
    assert_true(is_directory('soils tile', soils_tile_dir))
    soils_tile = os.path.join(soils_tile_dir, 'soil_%s_%s.tile.nc4' % (config.get('tlatidx'), config.get('tlonidx')))
    assert_true(is_file('soils tile', soils_tile))
    assert_true(is_netcdf('soils netcdf', soils_tile))

# Refdata
refdata=config.get('refdata')
if refdata:
    assert_true(is_directory('refdata', refdata))

# Executable
assert_true(is_defined('executable', config.get('executable')))
if config.get('model') in ['apsim', 'apsim75', 'apsim77']:
    assert_true(is_gzip('executable', config.get('executable')))
else:
    assert_true(is_executable('executable', config.get('executable').split()[0]))

# Misc
must_be_defined = ["out_file", "ref_year", "num_years", "scen_years", "scens", "delta", "tdelta", "num_lats",
                   "num_lons", "lat_zero", "lon_zero", "variables", "var_units", "long_names"]
for p in must_be_defined:
    assert_true(is_defined(p, config.get(p)))

# Now that the general cases are tested, each translator must be responsible for its own specific parameters
translator_factory_obj = translator_factory.TranslatorFactory()
tile_translator        = translator_factory_obj.create_translator(config, 'tapptile')
campaign_translator    = translator_factory_obj.create_translator(config, "tappcmp")
input_translator       = translator_factory_obj.create_translator(config, "tappinp")
pretranslator          = translator_factory_obj.create_translator(config, "pretranslator")
weather_translator     = translator_factory_obj.create_translator(config, "tappwth")
output_translator      = translator_factory_obj.create_translator(config, "postprocess")
optimizer_translator   = translator_factory_obj.create_translator(config, 'tappopt')
soil_tile_translator   = translator_factory_obj.create_translator(config, 'tapptilesoil')
clim_tile_translator   = translator_factory_obj.create_translator(config, 'tapptilewth')
nooutput_translator    = translator_factory_obj.create_translator(config, 'tappnooutput')

translators = [tile_translator, campaign_translator, input_translator, pretranslator, weather_translator,
output_translator, optimizer_translator, soil_tile_translator, clim_tile_translator, nooutput_translator]

# Test each translator
for translator in translators:
    try:
        assert_true(translator.verify_params(config.get('tlatidx'), config.get('tlonidx')))
    except AttributeError:
        print "WARNING: Translator %s does not have a verify_params() method! Unable to test parameters for this translator" % type(translator).__name__

# Test the checker
checker_factory_obj = checker_factory.CheckerFactory()
checker             = checker_factory_obj.create_checker(config, 'checker')
assert_true(checker.verify_params(config.get('tlatidx'), config.get('tlonidx')))

# Test aggregator
psims_directory = os.path.dirname(os.path.realpath(__file__))
aggregate_path  = os.path.join(psims_directory, "aggregate.py")
command = "%s -p %s --sanity" % (aggregate_path, args.params)
assert_true(test_system(command))

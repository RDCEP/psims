#!/usr/bin/env python
#
# This program is a parameter file sanity checker used by psims to determine if a run should proceed
#
import argparse
import datetime
import gzip
import netCDF4
import os
import subprocess
import sys
import yaml
import configuration.configuration
import translators.translator_factory as translator_factory
import checkers.checker_factory as checker_factory


def assert_true(passed, quiet=False):
    """
    Exit with an error if a test fails
    Args:
        passed: Boolean representing pass/fail state
        quiet: Don't print successes
    """
    check = 'o'
    fail = 'x'
    (status, message) = passed
    if status:
        if not quiet:
            print "%s %s" % (check, message)
    else:
        sys.exit(fail + " " + message)


def is_defined(name, value):
    """
    Test if a parameter is defined
    Args:
         name: Parameter name
         value: Parameter value
    Returns:
        True/False and string to be printed
    """
    if value:
        return True, "%s is defined" % name
    else:
        return False, "%s is not defined!" % name


def has_data(name, value):
    """
    Test if a list contains data
    Args:
        name: Description of list
        value: List itself
    Returns:
        True if it has data or False otherwise, and string to be printed
    """
    if len(value) > 0:
        return True, "%s is defined" % name
    else:
        return False, "%s is undefined!" % name


def is_directory(name, value):
    """
    Test if a parameter representing a directory actually exists in the filesystem
    Args:
       name: Parameter name
       value: Parameter value
    Returns:
        True/False and string to be printed
    """
    if os.path.isdir(value):
        return True, "%s directory exists" % name
    else:
        return False, "%s directory %s does not exist!" % (name, value)


def is_executable(name, value):
    """
    Test if a parameter representing an executable program exists on the filesystem and is executable
    Args:
        name: Parameter name
        value: Parameter value
    Returns:
        True/False and string to be printed
    """
    if os.access(value, os.X_OK):
        return True, "%s has execution bit" % name
    else:
        return False, "%s file %s does not have execution bit!" % (name, value)


def is_file(name, value):
    """
    Does a parameter representing a file actually exist in the filesystem?
    Args:
        name: Parameter name
        value: Parameter value
    Returns: True/False and a string to be printed
    """
    if os.path.exists(value):
        return True, "%s file exists" % name
    else:
        return False, "%s file %s does not exist!" % (name, value)


def is_netcdf(name, value):
    """
    Does a parameter representing a NetCDF file actually a NetCDF file?
    Args:
        name: Parameter name
        value: Parameter value
    Returns:
        True/False and a string to be printed
    """
    try:
        netCDF4.Dataset(value, 'r')
        return True, "%s tile is NetCDF" % name
    except IOError:
        return False, "%s file %s is not a NetCDF" % (name, value)


def is_gzip(name, value):
    """
    Is a parameter representing a gzipped file actually a gzipped file?
    Args:
        name: Parameter name
        value: Parameter value
    Returns:
        True/False and a string to be printed
    """
    try:
        gzip.GzipFile(value, 'r').read(1)
        return True, "%s is gzipped" % name
    except IOError:
        return False, "%s file %s is not gzipped" % (name, value)


def is_yaml(name, value):
    """
    Check if a file is yaml
    Args:
        name: Description of file
        value: Filename
    Returns:
        True/False and string to be printed
    """
    try:
        yaml.load(open(value))
        return True, "%s file is YAML" % name
    except yaml.YAMLError:
        return False, "%s file %s is not YAML, check formatting" % (name, value)


def test_system(command):
    """
    Test for a parameter representing a command
    Args:
        command: String representing command to run
    Returns:
        True if exit code is zero or False if exit code is non-zero, and a string to print
    """
    ec = os.system(command)
    exe = os.path.basename(command.split(' ')[0])
    if ec == 0:
        return True, "%s command passed" % exe
    return False, "%s failed" % exe


def test_soil(conf, tilefile):
    """
    Run all soil tests
    Args:
        conf: YAML configuration
        tilefile: String representing tilelist file
    """
    soils = []
    for s in conf.get('soils', default="").split(','):
        if s:
            soils.append(s)
    for s in conf.get_dict('stageinputs', 'soils', default=""):
        if s:
            soils.append(s)
    assert_true(has_data("soils", soils))
    tiles = open(tilefile, 'r').readlines()
    for soil in soils:
        assert_true(is_directory('soils', soil))
        assert_true((True, "Checking %s soil tiles in %s" % (len(tiles), soil)))
        for tile in tiles:
            latidx, lonidx = tile.strip().split('/')
            soils_tile_dir = os.path.join(soil, latidx)
            soils_tile = os.path.join(soils_tile_dir, 'soil_%s_%s.tile.nc4' % (latidx, lonidx))
            assert_true(is_file('soil tile', soils_tile), quiet=True)


def test_weather(conf, tilefile):
    """
    Run all weather tests
    Args:
        conf: YAML configuration
        tilefile: String representing tilelist file
    """
    weathers = []
    for w in conf.get('weather', default="").split(','):
        if w:
            weathers.append(w)
    for w in conf.get_dict('stageinputs', 'weather', default=""):
        if w:
            weathers.append(w)
    assert_true(has_data("weather", weathers))
    tiles = open(tilefile, 'r').readlines()
    for weather in weathers:
        assert_true(is_directory('weather', weather))
        assert_true((True, "Checking %s weather tiles in %s" % (len(tiles), weather)))
        for tile in tiles:
            latidx, lonidx = tile.strip().split('/')
            wth_tile_dir = os.path.join(weather, latidx)
            wth_tile = os.path.join(wth_tile_dir, "clim_%s_%s.tile.nc4" % (latidx, lonidx))
            assert_true(is_file('weather tile', wth_tile), quiet=True)


def test_refdata(conf):
    """
    Run tests related to refdata
    Args:
        conf: YAML configuration
    """
    refdata = conf.get('refdata')
    if refdata:
        assert_true(is_directory('refdata', refdata))


def test_executable(conf):
    """
    Run tests related to executable
    Args:
        conf: YAML configuration
    """
    assert_true(is_defined('executable', conf.get('executable')))
    if conf.get('model') in ['apsim', 'apsim75', 'apsim77']:
        assert_true(is_gzip('executable', conf.get('executable')))
    else:
        assert_true(is_executable('executable', conf.get('executable').split()[0]))


def test_required_definitions(conf):
    """
    Test if all required parameters are defined
    Args:
        conf: YAML configuration
    """
    must_be_defined = ["delta", "lat_zero", "lon_zero", "long_names", "num_lats", "num_lons", "num_years", "out_file",
                       "ref_year", "scen_years", "scens", "tdelta", "variables", "var_units"]
    for p in must_be_defined:
        assert_true(is_defined(p, conf.get(p)))


def test_all_translators(conf):
    """
    Every translator can have its own tests. Run these now.
    Args:
        conf: YAML configuration
    """
    translator_factory_obj = translator_factory.TranslatorFactory()
    tile_translator = translator_factory_obj.create_translator(conf, 'tapptile')
    campaign_translator = translator_factory_obj.create_translator(conf, "tappcmp")
    input_translator = translator_factory_obj.create_translator(conf, "tappinp")
    pretranslator = translator_factory_obj.create_translator(conf, "pretranslator")
    weather_translator = translator_factory_obj.create_translator(conf, "tappwth")
    output_translator = translator_factory_obj.create_translator(conf, "postprocess")
    optimizer_translator = translator_factory_obj.create_translator(conf, 'tappopt')
    soil_tile_translator = translator_factory_obj.create_translator(conf, 'tapptilesoil')
    clim_tile_translator = translator_factory_obj.create_translator(conf, 'tapptilewth')
    nooutput_translator = translator_factory_obj.create_translator(conf, 'tappnooutput')

    translators = [tile_translator, campaign_translator, input_translator, pretranslator, weather_translator,
                   output_translator, optimizer_translator, soil_tile_translator, clim_tile_translator,
                   nooutput_translator]

    for translator in translators:
        assert_true(translator.verify_params(conf.get('tlatidx'), conf.get('tlonidx')))


def test_checker(conf):
    """
    Test checker
    Args:
        conf: YAML configuration
    """
    checker_factory_obj = checker_factory.CheckerFactory()
    checker = checker_factory_obj.create_checker(conf, 'checker')
    assert_true(checker.verify_params(conf.get('tlatidx'), conf.get('tlonidx')))


def test_aggregator(conf):
    """
    Test aggregator
    Args:
        conf: YAML configuration
    """
    psims_directory = os.path.dirname(os.path.realpath(__file__))
    aggregate_path = os.path.join(psims_directory, "aggregate.py")
    process = subprocess.Popen([aggregate_path, "-p", conf.get('params'), '--sanity'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        assert_true((True, stdout))
    else:
        assert_true((False, stderr))


# Parse command line arguments
parser = argparse.ArgumentParser(description='pSIMS params sanity checker')
parser.add_argument('--campaign', required=True, help='Campaign directory')
parser.add_argument('--params', required=True, help='Param file')
parser.add_argument('--tilelist', required=True, help='Simulation tilelist')
parser.add_argument('--tlatidx', required=True, help='Tile latitude index')
parser.add_argument('--tlonidx', required=True, help='Tile longitude index')
args = parser.parse_args()

print "\nRunning Sanity checks on parameter file %s" % args.params

# Ensure params file is legit before running other tests
assert_true(is_file('params', args.params))
assert_true(is_yaml('params', args.params))

# Set some additional config values based on command line arguments
config = configuration.configuration.YAMLConfiguration(args.params)
config.set('campaign', args.campaign)
config.set('tlatidx', args.tlatidx)
config.set('tlonidx', args.tlonidx)
config.set('params', args.params)

# Run all tests
test_refdata(config)
test_executable(config)
test_checker(config)
test_weather(config, args.tilelist)
test_soil(config, args.tilelist)
test_required_definitions(config)
test_all_translators(config)
if config.get('aggregator', default=None):
    test_aggregator(config)

#!/usr/bin/env python

import sys,os
sys.path.append("%s/translators/utils" % os.path.dirname(__file__))

# import modules
from nco import Nco
from fnmatch import filter
from os import listdir, sep
from shutil import copyfile
from os.path import basename
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import masked_array
import configuration.configuration
from numpy import setdiff1d, double, zeros, ones, arange, ceil
import netCDF4

def combinelon(prefix, inputdir, fill_value='1e20', daily=False, year=None):
    if daily:
        files = [inputdir + sep + f for f in filter(listdir(inputdir), '%s*.%d.psims.nc' % (prefix, year))]
    else:
        files = [inputdir + sep + f for f in filter(listdir(inputdir), '%s*.psims.nc' % prefix)]

    # tile latitude and longitude indices
    tlatidx = basename(files[0]).split('_')[1]
    lonidx  = [int(basename(f).split('_')[2][: 4]) for f in files]

    # get file information
    with nc(files[0]) as f:
        vars  = setdiff1d(f.variables.keys(), ['time', 'scen', 'irr', 'lat', 'lon'])
        nscen = f.variables['scen'].size
        ldim  = f.variables[vars[0]].dimensions[0]

        vunits  = [0] * len(vars)
        vlnames = [0] * len(vars)
        for i in range(len(vars)):
            var        = f.variables[vars[i]]
            vunits[i]  = var.units     if 'units'     in var.ncattrs() else ''
            vlnames[i] = var.long_name if 'long_name' in var.ncattrs() else ''

    # fill longitude gaps
    for idx in setdiff1d(fulllonidx, lonidx):
        if daily:
            lonfile = inputdir + sep + '%s_%s_%04d.%d.psims.nc' % (prefix, tlatidx, idx, year)
        else:
            lonfile = inputdir + sep + '%s_%s_%04d.psims.nc' % (prefix, tlatidx, idx)
        copyfile(files[0], lonfile)
        lons = arange(-180 + tlond * (idx - 1) + lond / 2., -180 + tlond * idx, lond)
        with nc(lonfile, 'a') as f:
            lonvar = f.variables['lon']
            lonvar[:] = lons
            for i in range(len(vars)):
                var = f.variables[vars[i]]
                var[:] = masked_array(zeros(var.shape), mask = ones(var.shape))
        files.append(lonfile)

    # output file
    if daily:
        outputfile = outputdir + sep + '%s_%s.%d.psims.nc' % (prefix, tlatidx, year)
    else:
        outputfile = outputdir + sep + '%s_%s.psims.nc' % (prefix, tlatidx)
    nco = Nco()

    # make longitude lead dimension
    for i in range(len(files)):
        nco.ncpdq(input = files[i], output = files[i], options = '-O -h -a lon,%s' % str(ldim))

    # concatenate all files
    if daily:
        inputfiles = ' '.join([inputdir + sep + '%s_%s_%04d.%d.psims.nc' % (prefix, tlatidx, idx, year) for idx in fulllonidx])
    else:
        inputfiles = ' '.join([inputdir + sep + '%s_%s_%04d.psims.nc' % (prefix, tlatidx, idx) for idx in fulllonidx])
    nco.ncrcat(input = inputfiles, output = outputfile, options = '-h')

    # make latitude lead dimension
    nco.ncpdq(input = outputfile, output = outputfile, options = '-O -h -a lat,lon')

    # add new scenario dimension
    nscennew   = nscen / (1 + irrflag)
    scen_range = ','.join([str(s) for s in range(1, nscennew + 1)])
    scenopt    = '-O -h -s \'defdim("scen_new",%d)\' -s "scen_new[scen_new]={%s}"' % (nscennew, scen_range)
    nco.ncap2(input = outputfile, output = outputfile, options = scenopt)
    nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a units,scen_new,c,c,"no"')
    nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a long_name,scen_new,c,c,"scenario"')

    # add irr dimension
    nirr       = 1 + irrflag
    irr_range  = ','.join([str(i) for i in range(1, nirr + 1)])
    irr_lname  = ['ir', 'rf'][: 1 + irrflag] if irr1st else ['rf', 'ir'][: 1 + irrflag]
    irropt     = '-O -h -s \'defdim("irr",%d)\' -s "irr[irr]={%s}"' % (nirr, irr_range)
    nco.ncap2(input = outputfile, output = outputfile, options = irropt)
    nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a units,irr,c,c,"mapping"')
    nco.ncatted(input = outputfile, output = outputfile, options = '-O -h -a long_name,irr,c,c,"%s"' % ','.join(irr_lname))

    # refactor variables
    for i in range(len(vars)):
        var = str(vars[i])

        # create new variable
        opt = '-O -h -s "\'%s_new\'[lat,scen_new,irr,lon,time]=0.0f"' % var
        nco.ncap2(input = outputfile, output = outputfile, options = opt)

        # set attributes
        opt = '-O -h -a _FillValue,%s_new,c,f,%s' % (var, fill_value)
        nco.ncatted(input = outputfile, output = outputfile, options = opt)
        if vunits[i]:
            opt = '-O -h -a units,%s_new,c,c,"%s"' % (var, str(vunits[i]))
            nco.ncatted(input = outputfile, output = outputfile, options = opt)
        if vlnames[i]:
            opt = '-O -h -a long_name,%s_new,c,c,"%s"' % (var, str(vlnames[i]))
            nco.ncatted(input = outputfile, output = outputfile, options = opt)

        # set value
        opt = '-O -h -s "\'%s_new\'(:,:,:,:,:)=\'%s\'"' % (var, var)
        nco.ncap2(input = outputfile, output = outputfile, options = opt)

        # remove old variable
        opt = '-O -h -x -v %s' % var
        nco.ncks(input = outputfile, output = outputfile, options = opt)

        # rename new variable
        opt = '-O -h -v %s_new,%s' % (var, var)
        nco.ncrename(input = outputfile, output = outputfile, options = opt)

    # remove old scenario dimension
    nco.ncks(input = outputfile, output = outputfile, options = '-O -h -x -v scen')
    nco.ncrename(input = outputfile, output = outputfile, options = '-O -h -v scen_new,scen')

    # limit spatial extent to sim grid
    nco.ncks(input = outputfile, output = outputfile, options = '-O -h -d lon,%f,%f' % (lon0, lon1))

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--inputdir", dest = "inputdir", default = ".", type = "string",
                  help = "Directory containing parts file for particular latitude band")
parser.add_option("-p", "--params", dest = "params", default = "params.dssat45.sample", type = "string",
                  help = "Parameter file", metavar = "FILE")
parser.add_option("-o", "--outputdir", dest = "outputdir", default = ".", type = "string",
                  help = "Output directory to save final file")
parser.add_option('-s', '--split', dest='split', type=int, help='Split value')
options, args = parser.parse_args()

inputdir       = options.inputdir
params         = options.params
outputdir      = options.outputdir
split          = options.split
config         = configuration.configuration.YAMLConfiguration(params)
nlons          = config.get('num_lons')
lon0           = config.get('lon_zero')
delta          = config.get('delta')
tdelta         = config.get('tdelta')
irrflag        = config.get('irr_flag', default = False)
irr1st         = config.get('irr_1st', default = True)
dailyv         = config.get('daily_variables')
daily_combine  = config.get('daily_combine', default = True)
ref_year       = config.get('ref_year')
num_years      = config.get('num_years')
nlons          = int(nlons)
lon0           = double(lon0)
_, lond        = [double(d) / 60 for d in delta.split(',')]
_, tlond       = [double(d) / 60 for d in tdelta.split(',')]
lon1           = lon0 + nlons * lond
tlond         /= split

# full tile longitude indices
tlonidx0   = int((lon0 + 180) / tlond + 1)
ntlon      = int(ceil(nlons * lond / tlond))
fulllonidx = range(tlonidx0, tlonidx0 + ntlon)

combinelon("output", inputdir)

if dailyv and daily_combine:
    for year in range(ref_year, ref_year+num_years):
        combinelon("daily", inputdir, fill_value=netCDF4.default_fillvals['f4'], daily=True, year=year)

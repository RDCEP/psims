#!/usr/bin/env python

# import modules
import airspeed
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy import resize, where, array

parser = OptionParser()
parser.add_option("-c", "--campaign_file", dest = "campaignfile", default = "campaign.nc4", type = "string", 
                  help = "campaign netcdf4 file", metavar = "FILE")
parser.add_option("-t", "--template_file", dest = "templatefile", default = "template.PJ!", type = "string", 
                  help = "template PJ! file", metavar = "FILE")
parser.add_option("--latidx", dest = "latidx", default = 1, type = "string",
                  help = "Latitude coordinate")
parser.add_option("--lonidx", dest = "lonidx", default = 1, type = "string",
                  help = "Longitude coordinate")
parser.add_option("-d", "--delta", dest = "delta", default = 1, type = "float",
                  help = "Distance between each grid cell in arcminutes")
parser.add_option("-r", "--ref_year", dest = "ref_year", default = 1958, type = "int",
                  help = "Reference year from which to record times")
parser.add_option("-n", "--nyers", dest = "nyers", default = 31, type = "int",
                  help = "Number of years in simulation")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic", type = "string",
                  help = "output PJ! file pattern")
options, args = parser.parse_args()

refyear = options.ref_year
numyears = options.nyers

template = airspeed.Template(open(options.templatefile, 'r').read())

defevents = {}
with nc(options.campaignfile) as f:
    lat = f.variables['lat'][:]
    lon = f.variables['lon'][:]
    scenarios = f.variables['scen'][:]
    fertility = f.variables['fertility'][:]
    numevents = f.variables['num_events'][:]
    
    stocking = f.variables['stocking'][:]
    mortality = f.variables['mortality'][:]
    mortsize = f.variables['mort_size'][:]
    
    co2flag = array(f.variables['co2flag'].long_name.split(','))
    co2flag = co2flag[f.variables['co2flag'][:] - 1]
    
    eventyear = f.variables['event_year'][:]
    eventmonth = f.variables['event_month'][:]
    eventday = f.variables['event_day'][:]
    eventdaystotal = f.variables['event_days_total'][:]
    harvstems = f.variables['harv_stems'][:]
    harvsize = f.variables['harv_size'][:]
    branchcut = f.variables['branch_cut'][:]
    stemsremoved = f.variables['stems_removed'][:]
    branchremoved = f.variables['branch_removed'][:]

    defevents['event_year'] = f.variables['event_year'].default
    defevents['event_month'] = f.variables['event_month'].default
    defevents['event_day'] = f.variables['event_day'].default
    defevents['event_days_total'] = f.variables['event_days_total'].default
    defevents['harv_stems'] = f.variables['harv_stems'].default
    defevents['harv_size'] = f.variables['harv_size'].default
    defevents['branch_cut'] = f.variables['branch_cut'].default
    defevents['stems_removed'] = f.variables['stems_removed'].default
    defevents['branch_removed'] = f.variables['branch_removed'].default

delta = options.delta / 60. # convert from arcminutes to degrees
latd = resize(lat, (len(lon), len(lat))).T - 90. + delta * (int(options.latidx) - 0.5)
lond = resize(lon, (len(lat), len(lon))) + 180. - delta * (int(options.lonidx) - 0.5)
totd = latd ** 2 + lond ** 2
idx = where(totd == totd.min())
latidx = idx[0][0]
lonidx = idx[1][0]

fertility = fertility[latidx, lonidx] if not fertility.mask[latidx, lonidx] else 1.

for s in range(len(scenarios)):
    nevents = numevents[s]
    dic = {}
    dic['fertility'] = fertility
    dic['stocking'] = stocking[s]
    dic['mortality'] = mortality[s]
    dic['mort_size'] = mortsize[s]
    dic['num_events'] = nevents
    dic['ref_year'] = refyear
    dic['num_years'] = numyears
    dic['co2flag'] = co2flag[s]
    dic['events'] = {}
    if nevents:
        dic['events'] = [0] * nevents
        for e in range(nevents):
            dic['events'][e] = {}
            dic['events'][e]['event_year'] = eventyear[s, e]
            dic['events'][e]['event_month'] = eventmonth[s, e]
            dic['events'][e]['event_day'] = eventday[s, e]
            dic['events'][e]['event_days_total'] = eventdaystotal[s, e]
            dic['events'][e]['harv_stems'] = harvstems[s, e]
            dic['events'][e]['harv_size'] = harvsize[s, e]
            dic['events'][e]['branch_cut'] = branchcut[s, e]
            dic['events'][e]['stems_removed'] = stemsremoved[s, e]
            dic['events'][e]['branch_removed'] = branchremoved[s, e]            
    else:
        dic['events'] = [defevents]
    with open(options.outputfile + str(s + 1) + '.PJ!', 'w') as f:
        f.write(template.merge(dic))
#!/usr/bin/env python

# import modules
import json, airspeed
from numpy import double
from optparse import OptionParser

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "soil.json", 
                  help = "JSON file to parse", metavar = "FILE")
parser.add_option("-t", "--template", dest = "templatefile", default = "template.ST!", 
                  help = "template ST! file", metavar = "FILE")
parser.add_option("--latidx", dest = "latidx", default = "001", type = "string",
                  help = "Latitude coordinate")
parser.add_option("--lonidx", dest = "lonidx", default = "001", type = "string",
                  help = "Longitude coordinate")
parser.add_option("-d", "--delta", dest = "delta", default = 30, type = "string",
                  help = "Distance(s) between each latitude/longitude grid cell in arcminutes")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.ST!",
                  help = "output ST! file", metavar = "FILE")
options, args = parser.parse_args()

delta = options.delta.split(',')
if len(delta) < 1 or len(delta) > 2: raise Exception('Wrong number of delta values')
latdelta = double(delta[0]) / 60.

template = airspeed.Template(open(options.templatefile, 'r').read())

data = json.load(open(options.inputfile))
soils = data['soils'][0]['soilLayer']
nlayers = len(soils)

s = {}
s['num_layers'] = nlayers
s['fine_soil_fraction'] = (double(soils[0]['slsil']) + double(soils[0]['slcly'])) / 100.
s['latitude'] = 90. - latdelta * (int(options.latidx) - 0.5)

s['layers'] = [0] * nlayers
total_max_water = 0
for i in range(nlayers):
    if not i:
        depth = double(soils[i]['sllb'])
        orgmatter = 0.1
    else:
        depth = double(soils[i]['sllb']) - double(soils[i - 1]['sllb'])
        orgmatter = 0.
    s['layers'][i] = {}
    s['layers'][i]['depth'] = depth
    s['layers'][i]['per_pores'] = 10.
    s['layers'][i]['max_water'] = double(soils[i]['sldul']) * depth
    s['layers'][i]['rel_decomp'] = 0.3496650340
    s['layers'][i]['rel_root'] = 0.1832366470
    s['layers'][i]['org_matter'] = orgmatter
    s['layers'][i]['rel_evap'] = 0.4
    s['layers'][i]['rel_water_stress'] = 0.
    s['layers'][i]['water_extract'] = 0.2539253930
    total_max_water += s['layers'][i]['max_water']
s['max_water_amount'] = total_max_water

with open(options.outputfile, 'w') as f:
    f.write(template.merge(s))

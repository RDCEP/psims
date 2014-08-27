#!/usr/bin/env python

# import modules
import abc
import json, airspeed
from numpy import double
from optparse import OptionParser
from scipy.interpolate import interp1d as interp1d

# helper functions
def get_field(struct, field, default = '?'):
    return default if not field in struct else struct[field]
def format_date(yyyymmdd):
    if yyyymmdd == '?':
        return '?'
    else:
        return yyyymmdd[6 : 8] + '/' + yyyymmdd[4 : 6] + '/' + yyyymmdd[: 4]
def date2num(ddmmyyyy):
    if ddmmyyyy:
        return '?'
    else:
        return int(ddmmyyyy[: 2]) + 100 * int(ddmmyyyy[3 : 5]) + 10000 * int(ddmmyyyy[6 : 10])


# management event base class
class Event(object):
    __metaclass__ = abc.ABCMeta
    def __init__(self, event_struct):
        self.date = get_field(event_struct, 'date')
        if self.date != '?':
            self.date = format_date(self.date)
    @abc.abstractmethod 
    def get_apsim_action(self): return
    

# management subclasses
# tillage
class Tillage(Event):
    def __init__(self, event_struct):
        super(Tillage, self).__init__(event_struct) # class superclass
        self.implement_name = get_field(event_struct, 'tiimp')
        self.depth = get_field(event_struct, 'tidep')
    def get_apsim_action(self):
        act = 'SurfaceOrganicMatter tillage type=' + self.implement_name
        act += ', f_incorp=0, tillage_depth=' + self.depth
        return act
        

# planting
class Planting(Event):
    def __init__(self, event_struct):
        super(Planting, self).__init__(event_struct) # call superclass
        self.crop_name = get_field(event_struct, 'crid')
        self.population = get_field(event_struct, 'plpop')
        self.depth = get_field(event_struct, 'pldp')
        self.cultivar = get_field(event_struct, 'apsim_cul_id')
        if self.cultivar == '?':
            cul_id = get_field(event_struct, 'cul_id')
            if cul_id != '?':
                self.cultivar = cul_id
        self.row_spacing = get_field(event_struct, 'plrs')
        if self.row_spacing != '?':
            self.row_spacing = str(10. * double(self.row_spacing))
    def get_apsim_action(self):
        act = self.crop_name
        act += " sow plants = " + self.population
        act += ", sowing_depth = " + self.depth
        act += ", cultivar = " + self.cultivar
        act += ", row_spacing = " + self.row_spacing
        act += ", crop_class = plant"
        return act
        

# irrigation
class Irrigation(Event):
    def __init__(self, event_struct):
        super(Irrigation, self).__init__(event_struct) # call superclass
        self.amount = get_field(event_struct, 'irval')
    def get_apsim_action(self):
        return 'irrigation apply amount = ' + self.amount + ' (mm) '
        

# fertilizer
class Fertilizer(Event):
    def __init__(self, event_struct):
        super(Fertilizer, self).__init__(event_struct) # call superclass
        self.nitrogen = get_field(event_struct, 'feamn')
        self.depth = get_field(event_struct, 'fedep')        
    def get_apsim_action(self):
        act = 'fertiliser apply amount = ' + self.nitrogen + ' (kg/ha)'
        act += ', type = no3_n (), depth = ' + self.depth + ' (mm)'
        return act
        

# organic matter
class OrganicMatter(Event):
    def __init__(self, event_struct):
        super(OrganicMatter, self).__init__(event_struct) # call superclass
        self.amount = get_field(event_struct, 'omamt')
        self.depth = get_field(event_struct, 'omdep')
        self.carbon = get_field(event_struct, 'omc%')
        self.nitrogen = get_field(event_struct, 'omn%')
        self.phosphorus = get_field(event_struct, 'omp%')        
    def get_apsim_action(self):
        cnr = '?'
        cpr = '?'
        act = 'SurfaceOrganicMatter add_surfaceom type=manure, name=manure, '
        act += 'mass=' + self.amount + '(kg/ha), '
        act += 'depth = ' + self.depth + ' (mm)'
        if self.amount != '?':
            if self.carbon != '?':
                if self.nitrogen != '?':
                    amount_carbon = double(self.carbon) / 100. * double(self.amount)
                    amount_nitrogen = double(self.nitrogen) / 100. * double(self.amount)
                    if amount_nitrogen == 0.:
                        cnr = '0'
                    else:
                        cnr = str(amount_carbon / amount_nitrogen * 100.)
                act += ', cnr = ' + cnr
                if self.phosphorus != '?':
                    amount_carbon = double(self.carbon) / 100. * double(self.amount)
                    amount_phosphorus = double(self.phosphorus) / 100. * double(self.amount)
                    if amount_phosphorus == 0.:
                        cpr = '0';
                    else:
                        cpr = str(amount_carbon / amount_phosphorus * 100.)
                    act += ', cpr = ' + cpr
        return act
        

# chemical
class Chemical(Event):
    def __init__(self, event_struct):
        super(Chemical, self).__init__(event_struct) # call superclass
    def get_apsim_action(self): return ''


# harvest
class Harvest(Event):
    def __init__(self, event_struct):
        super(Harvest, self).__init__(event_struct) # call superclass
    def get_apsim_action(self): return ''
    

def get_layers(soil):
    # variables used for computation
    num_layers = len(soil['soilLayer'])  
    kl_x = [0, 15, 30, 60, 90, 120, 150, 180, 1e10] # add leftmost and rightmost bin edges
    kl_y = [0.08, 0.08, 0.08, 0.08, 0.06, 0.06, 0.04, 0.02, 0.02]
    kl_interp = interp1d(kl_x, kl_y)
    fbiom_per_layer = 0.03 / (num_layers - 1) if num_layers > 1 else 0.03
    finert_x = [0, 15, 30, 60, 90, 1e10] # add leftmost and rightmost bin edges
    finert_y = [0.4, 0.4, 0.5, 0.7, 0.95, 0.95]
    finert_interp = interp1d(finert_x, finert_y)
    
    # layer data
    layers = [0] * num_layers 
    cum_thickness = 0
    for i in range(num_layers):
        layers[i] = {}
        layer = soil['soilLayer'][i]
        bottom_depth = get_field(layer, 'sllb')
        if bottom_depth == '?':
            raise Exception('Soil layer depth not specified')
        else:
            bottom_depth = double(bottom_depth)
        layers[i]['thickness'] = 10 * bottom_depth - cum_thickness
        layers[i]['lowerLimit'] = get_field(layer, 'slll')
        layers[i]['kl'] = str(kl_interp(bottom_depth))
        layers[i]['bulkDensity'] = get_field(layer, 'slbdm')
        if layers[i]['lowerLimit'] == '?':
            layers[i]['airDry'] = '?'
        else:
            layers[i]['airDry'] = str(0.5 * double(layers[i]['lowerLimit']))
        layers[i]['drainedUpperLimit'] = get_field(layer, 'sldul')
        layers[i]['saturation'] = get_field(layer, 'slsat')
        layers[i]['organicCarbon'] = get_field(layer, 'sloc')
        if layers[i]['organicCarbon'] != '?':
            organic_carbon = double(layers[i]['organicCarbon'])
            if not organic_carbon: layers[i]['organicCarbon'] = '0.1'
        layers[i]['fbiom'] = str(0.04 - fbiom_per_layer * i)
        layers[i]['finert'] = str(finert_interp(bottom_depth))
        layers[i]['ph'] = get_field(layer, 'slphw')
        cum_thickness = 10 * bottom_depth

    return layers
        

def get_soil_structure(soil):
    soil_struct = {}
    
    # profile-wide values
    classification = get_field(soil, 'classification')
    soil_name = get_field(soil, 'soil_name')
    if 'sand' in classification or 'sand' in soil_name:
        diffus_const = 250
        diffus_slope = 22
    elif 'loam' in classification or 'loam' in soil_name:
        diffus_const = 88
        diffus_slope = 35
    elif 'clay' in classification or 'clay' in soil_name:
        diffus_const = 40
        diffus_slope = 16
    else:
        diffus_const = 40
        diffus_slope = 16
    soil_struct['u'] = get_field(soil, 'slu1')
    soil_struct['salb'] = get_field(soil, 'salb')
    soil_struct['cn2bare'] = get_field(soil, 'slro')
    soil_struct['diffusConst'] = diffus_const
    soil_struct['diffusSlope'] = diffus_slope
    soil_struct['classification'] = soil['classification']
    soil_struct['site'] = get_field(soil, 'soil_site')
    soil_struct['latitude'] = get_field(soil, 'soil_lat')
    soil_struct['longitude'] = get_field(soil, 'soil_long')
    soil_struct['source'] = get_field(soil, 'sl_source')
    
    # layer data
    soil_struct['layers'] = get_layers(soil)
    
    return soil_struct

    
def get_management(exp):
    man = {}
    
    if not 'management' in exp: return man
    if not 'events' in exp['management']: return man
    
    # planting crop name
    num_events = len(exp['management']['events'])
    for i in range(num_events):
        # find crop to be planted
        event = exp['management']['events'][i]
        if get_field(event, 'event') == 'planting':
            man['plantingCropName'] = get_field(event, 'crid')
            break
        elif i == num_events - 1:
            Exception('No planting event found')
    
    # events data
    man['events'] = [0] * num_events
    for i in range(num_events):
        man['events'][i] = {}
        event_struct = exp['management']['events'][i]
        if get_field(event_struct, 'event') == 'tillage':
            event_obj = Tillage(event_struct)
        elif get_field(event_struct, 'event') == 'planting':
            event_obj = Planting(event_struct)
        elif get_field(event_struct, 'event')  == 'irrigation':
            event_obj = Irrigation(event_struct)
        elif get_field(event_struct, 'event') == 'fertilizer':
            event_obj = Fertilizer(event_struct)
        elif get_field(event_struct, 'event') == 'organic_matter':
            event_obj = OrganicMatter(event_struct)
        elif get_field(event_struct, 'event') == 'chemical':
            event_obj = Chemical(event_struct)
        elif get_field(event_struct, 'event') == 'harvest':
            event_obj = Harvest(event_struct)
        else:
            Exception('Unknown management event')
        man['events'][i]['date'] = event_obj.date
        man['events'][i]['apsimAction'] = event_obj.get_apsim_action()
    man['events'] = sorted(man['events'], key = lambda x: date2num(x['date'])) # sort events
    
    return man


def get_initial_condition(exp, thicknesses):
    ic_struct = {}
    ic = exp['initial_condition']
    
    # date, residue type, residue weight
    ic_struct['date'] = format_date(get_field(ic, 'icdat'))
    ic_struct['residueType'] = get_field(exp, 'crop_name')
    ic_struct['residueWeight'] = get_field(ic, 'icrag')
    ic_struct['standing_fraction'] = get_field(ic, 'standing_fraction')
    ic_struct['water_fraction_full'] = get_field(ic, 'water_fraction_full')
    
    # layer data
    layers = [0] * len(thicknesses)
    for i in range(len(thicknesses)):
        layers[i] = {}
        layers[i]['thickness'] = thicknesses[i]
        layers[i]['no3'] = get_field(ic['soilLayer'][i], 'icno3')
        layers[i]['nh4'] = get_field(ic['soilLayer'][i], 'icnh4')
        layers[i]['soilWater'] = get_field(ic['soilLayer'][i], 'ich2o')
    ic_struct['soilLayers'] = layers
    
    # carbon to nitrogen ratio
    carbon = 0.4 * double(ic_struct['residueWeight'])
    nitrogen = double(get_field(ic, 'icrn')) / 100. * double(ic_struct['residueWeight'])
    ic_struct['cnr'] = carbon / nitrogen
    
    return ic_struct

    
# parse inputs
parser = OptionParser()
parser.add_option("-s", "--soil_file", dest = "soilfile", default = "soil.json", type = "string", 
                  help = "soil JSON file", metavar = "FILE")
parser.add_option("-e", "--exp_file", dest = "expfile", default = "exp.json", type = "string", 
                  help = "experiment JSON file", metavar = "FILE")
parser.add_option("-t", "--template_file", dest = "templatefile", default = "template.apsim", type = "string", 
                  help = "template APSIM file", metavar = "FILE")
parser.add_option("--latidx", dest = "latidx", default = "001", type = "string",
                  help = "Latitude coordinate")
parser.add_option("--lonidx", dest = "lonidx", default = "001", type = "string",
                  help = "Longitude coordinate")
parser.add_option("-d", "--delta", dest = "delta", default = 30, type = "string",
                  help = "Distance(s) between each latitude/longitude grid cell in arcminutes")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.apsim", type = "string",
                  help = "output APSIM file", metavar = "FILE")
(options, args) = parser.parse_args()

# open json files
soil_json = json.load(open(options.soilfile, 'r'))
exp_json = json.load(open(options.expfile, 'r'))

num_experiments = len(exp_json['experiments'])

# simulation structure
s = {'experiments': [0] * num_experiments}

for i in range(num_experiments):
    exp_i = exp_json['experiments'][i]
    # global
    s_tmp = {}
    s_tmp['cropName'] = exp_i['crop_name']
    s_tmp['startDate'] = exp_i['start_date']
    s_tmp['endDate'] = exp_i['end_date']
    s_tmp['log'] = exp_i['log']
    s_tmp['reporting_frequency'] = exp_i['reporting_frequency']
    if 'micromet' in exp_i.keys():
        s_tmp['micromet'] = exp_i['micromet']
    else:
        s_tmp['micromet'] = 'off' # default to off
    # weather
    s_tmp['weather'] = exp_i['weather']
    # soil
    s_tmp['soil'] = get_soil_structure(soil_json['soils'][0])
    # management
    s_tmp['management'] = get_management(exp_i)
    # initial condition
    thicknesses = [L['thickness'] for L in s_tmp['soil']['layers']]
    s_tmp['initialCondition'] = get_initial_condition(exp_i, thicknesses)
    # planting
    s_tmp['planting'] = exp_i['planting']
    # fertilizer
    s_tmp['fertilizer'] = exp_i['fertilizer']
    # irrigation
    s_tmp['irrigation'] = exp_i['irrigation']
    # reset
    s_tmp['reset'] = exp_i['reset']
    # output variables
    s_tmp['output_variables'] = exp_i['output_variables']
    s['experiments'][i] = s_tmp

# find and replace within template and write output file
template = airspeed.Template(open(options.templatefile, 'r').read())
with open(options.outputfile, 'w') as f:
    f.write(template.merge(s))

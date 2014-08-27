#!/usr/bin/env python

# import modules
from netCDF4 import Dataset as nc
from optparse import OptionParser
import re, json, copy, datetime as dt
from numpy import nan, isnan, double, resize, where, prod, newaxis, repeat, reshape, zeros, array, append

# UTILITY FUNCTIONS
def list_replace(arr, var, val, occ = nan, cnt = 1):
    for item in arr:
        if isinstance(item, list):
            cnt = list_replace(item, var, val, occ = occ, cnt = cnt)
        elif isinstance(item, dict):
            cnt = dict_replace(item, var, val, occ = occ, cnt = cnt)
    return cnt
def dict_replace(dic, var, val, occ = nan, cnt = 1):
    keys = dic.keys()
    for i in range(len(keys)):
        key = keys[i]
        item = dic[key]
        if isinstance(item, list):
            cnt = list_replace(item, var, val, occ = occ, cnt = cnt)
        elif isinstance(item, dict):
            cnt = dict_replace(item, var, val, occ = occ, cnt = cnt)
        elif key == var:
            if isnan(occ) or cnt == occ:
                dic[key] = val
            cnt += 1
    return cnt
def convert_var(var, val):
    if var == 'pdate':
        day = int(round(val))
        val = (dt.date(1900, 1, 1) + dt.timedelta(day - 1)).strftime('%e-%b')
    elif var == 'wst_id':
        val = 'WTH%05d' % val
    return val
def get_obj(dic, key, dft):
    return dic[key] if key in dic else dft
def repvals(vals, dimsizes, orders, order):
    def repeat_n(arr, n):
        arr2 = arr.copy()
        sh = list(arr2.shape)
        sh[0] *= n
        arr2 = arr2[newaxis, ...]
        arr2 = repeat(arr2, n, axis = 0)
        arr2 = reshape(arr2, sh)
        return arr2
    nabove = prod(dimsizes[orders > order])
    dupvals = repeat(vals, nabove)
    nbelow = prod(dimsizes[orders < order])
    dupvals = repeat_n(dupvals, nbelow)
    return dupvals
def repvals2(vals, dimsizes, orders, order1, order2):
    if order2 < order1:
        vals = vals.T # make first dimension lower order
    dupvals = array([])
    for i in range(len(vals)):
        dnew = dimsizes[orders > order1]
        onew = orders[orders > order1] - order1 # reset orders
        dupvals = append(dupvals, repvals(vals[i], dnew, onew, order2 - order1))
    dnew = dimsizes[orders <= order1]
    onew = orders[orders <= order1]
    dupvals = repvals(dupvals, dnew, onew, order1)
    return dupvals

# parse inputs
parser = OptionParser()
parser.add_option("-c", "--campaign_file", dest = "campaignfile", default = "campaign.nc4", type = "string", 
                  help = "campaign netcdf4 file", metavar = "FILE")
parser.add_option("-e", "--exp_file", dest = "expfile", default = "expin.json", type = "string", 
                  help = "input experiment JSON file", metavar = "FILE")
parser.add_option("--latidx", dest = "latidx", default = 1, type = "string",
                  help = "Latitude coordinate")
parser.add_option("--lonidx", dest = "lonidx", default = 1, type = "string",
                  help = "Longitude coordinate")
parser.add_option("-d", "--delta", dest = "delta", default = 30, type = "string",
                  help = "Distance(s) between each latitude/longitude grid cell in arcminutes")
parser.add_option("-r", "--ref_year", dest = "ref_year", default = 1958, type = "int",
                  help = "Reference year from which to record times")
parser.add_option("-n", "--nyers", dest = "nyers", default = 31, type = "int",
                  help = "Number of years in simulation")
parser.add_option("-s", "--nscens", dest = "nscens", default = 12, type = "int",
                  help = "Number of scenarios")
parser.add_option("-o", "--output", dest = "outputfile", default = "expout.json", type = "string",
                  help = "output experiment JSON file", metavar = "FILE")
options, args = parser.parse_args()

# open campaign netcdf4 file
campaign = nc(options.campaignfile, 'r', format = 'NETCDF4')

# open experiment json file
template = json.load(open(options.expfile, 'r'))

# determine gridpoint with nearest latitude and longitude
delta = options.delta.split(',')
if len(delta) < 1 or len(delta) > 2: raise Exception('Wrong number of delta values')
latdelta = double(delta[0]) / 60. # convert from arcminutes to degrees
londelta = latdelta if len(delta) == 1 else double(delta[1]) / 60.
lat = campaign.variables['lat'][:]
lon = campaign.variables['lon'][:]
latd = resize(lat, (len(lon), len(lat))).T - 90. + latdelta * (int(options.latidx) - 0.5)
lond = resize(lon, (len(lat), len(lon))) + 180. - londelta * (int(options.lonidx) - 0.5)
totd = latd ** 2 + lond ** 2
idx = where(totd == totd.min())
latidx = idx[0][0]
lonidx = idx[1][0]

# latitude and longitude
lat = lat[latidx]
lon = lon[lonidx]

# perform global replace
for attr in campaign.ncattrs():
    dict_replace(template, attr.lower(), campaign.getncattr(attr))
dict_replace(template, 'site_name', str(lat) + ', ' + str(lon))

# dimensions
dimensions = campaign.dimensions.keys()
dimensions.remove('lat') # remove lat, lon
dimensions.remove('lon')
ndims = len(dimensions)
orders, dimsizes = zeros(ndims), zeros(ndims)
for i in range(ndims): # order of dimension (1 = slowest moving, etc.) and dimension size
    dimvar = campaign.variables[dimensions[i]]
    orders[i] = int(dimvar.order) if 'order' in dimvar.ncattrs() else 1
    dimsizes[i] = dimvar.size

# number of scenarios
num_scenarios = int(min(prod(dimsizes), options.nscens)) # limit to nscens

# duplicate experiment for each scenario
exp = {'experiments': []}
for i in range(num_scenarios):
    exp['experiments'].append(copy.deepcopy(template)) # need to deepcopy!

# get variables
variables = campaign.variables.keys()
variables.remove('lat') # remove lat, lon, and all dimensions
variables.remove('lon')
for d in dimensions:
    variables.remove(d)

# replace trno
for i in range(num_scenarios): 
    dict_replace(exp['experiments'][i], 'trno', str(i + 1))

# replace nyers globally
nyers = options.nyers
list_replace(exp['experiments'], 'nyers', str(nyers))

# iterate through variables
for var in variables:
    # get netCDF4 variable 
    v = campaign.variables[var]
    v.set_auto_maskandscale(False)

    # get dimensions
    dim = list(v.dimensions) # tuple to list

    # get variable array
    if v.ndim == 1:
        if not dim[0] in dimensions:
            raise Exception('Unrecognized dimension in variable %s' % var)

        dim_idx = dimensions.index(dim[0])
        var_array = repvals(v[:], dimsizes, orders, orders[dim_idx])
    else:
        if not 'lat' in dim:
            raise Exception('Latitude dimension is missing')
        if not 'lon' in dim:
            raise Exception('Longitude dimension is missing')
        dim.remove('lat')
        dim.remove('lon')

        if v.ndim == 2:
            var_array = resize(v[latidx, lonidx], num_scenarios) # duplicate for all scenarios
        elif v.ndim == 3:
            if not dim[0] in dimensions:
                raise Exception('Unrecognized dimension in variable %s' % var)

            dim_idx = dimensions.index(dim[0])
            var_array = repvals(v[:, latidx, lonidx], dimsizes, orders, orders[dim_idx])
        elif v.ndim == 4:
            if not dim[0] in dimensions or not dim[1] in dimensions:
                raise Exception('Unrecognized dimension in variable %s' % var)

            dim_idx1, dim_idx2 = dimensions.index(dim[0]), dimensions.index(dim[1])
            var_array = repvals2(v[:, :, latidx, lonidx], dimsizes, orders, orders[dim_idx1], orders[dim_idx2])
        else:
            raise Exception('Data contain variables with improper dimensions')    

    # limit to nscens
    var_array = var_array[: num_scenarios]

    # get attributes
    attrs = v.ncattrs()

    # get missing and fill values, if available
    fill_value = v._FillValue if '_FillValue' in attrs else nan
    missing_value = v.missing_value if 'missing_value' in attrs else nan

    # get mapping, if available
    is_mapping = False
    if 'units' in attrs and v.units == 'Mapping' and 'long_name' in attrs:
        mapping = v.long_name.split(',')
        is_mapping = True

    # get replacement number
    occ = nan # indicates to replace all instances of key
    nums = re.findall('.*_(\d+)', var)
    if nums != []:
        var = re.sub('_\d+', '', var) # remove number
        occ = int(nums[0])

    # iterate over scenarios
    if len(var_array) != num_scenarios:
        raise Exception('Disagreement between variable length and number of scenarios!')
    for j in range(num_scenarios):
        val = var_array[j]

        if val == fill_value or val == missing_value:
            continue

        if is_mapping:
            val = mapping[int(val - 1)]

        # convert variable to different representation, if necessary
        val_old = val
        val = convert_var(var, val)

        dict_replace(exp['experiments'][j], var, str(val), occ = occ) # make sure val is str!

        # SPECIAL CASE FOR APSIM!
        # CHANGE EDATE TO PDATE - 30 days
        # CHANGE RESET DATE TO PDATE - 60 days
        if var == 'pdate':
            eday = int(round(val_old)) - 30
            if eday < 1:
                eday = 365 + eday # non-leap year
            rday = int(round(val_old)) - 60
            if rday < 1:
                rday = 365 + rday # non-leap year
            edate = (dt.date(1900, 1, 1) + dt.timedelta(eday - 1)).strftime('%e-%b')
            rdate = (dt.date(1900, 1, 1) + dt.timedelta(rday - 1)).strftime('%e-%b')
            dict_replace(exp['experiments'][j], 'edate', str(edate), occ = occ)
            dict_replace(exp['experiments'][j], 'date', str(rdate), occ = occ)

# change dates based on reference year and number of years
if 'ref_year' in variables:
    yers = campaign.variables['ref_year'][:].astype(int)
    dim = list(campaign.variables['ref_year'].dimensions)
    dim_idx = dimensions.index(dim[0])
    yers = repvals(yers, dimsizes, orders, orders[dim_idx])
else:
    yers = resize(options.ref_year, num_scenarios)
for i in range(len(exp['experiments'])):
    e = exp['experiments'][i]
    ref_year = yers[i]
    yer = ref_year % 100
    dict_replace(e, 'pfyer', str(yer))
    dict_replace(e, 'plyer', str(yer))
    dict_replace(e, 'hlyer', str(yer + 1))
    dict_replace(e, 'sdyer', str(yer))
    dict_replace(e, 'odyer', str(yer))
    man = get_obj(e, 'management', {})
    if man != {}:
        pdate = man['events'][0]['date']
        dict_replace(e, 'date', str(ref_year) + pdate[4 :], occ = 1) # planting date
        idate = man['events'][3]['date']
        dict_replace(e, 'date', str(ref_year) + idate[4 :], occ = 4) # irrigation date
        hdate = man['events'][4]['date']
        dict_replace(e, 'date', str(ref_year + 1) + '1231', occ = 5) # harvest date
    soil = get_obj(e, 'soil', {})
    if soil != {}:
        sdate = soil['sadat']
        dict_replace(e, 'sadat', str(ref_year) + sdate[4 :])
    ic = get_obj(e, 'initial_conditions', {})
    if ic == {}:
        ic = get_obj(e, 'initial_condition', {})
    if ic != {}:
        icdate = ic['icdat']
        dict_replace(e, 'icdat', str(ref_year) + icdate[4 :])
    start_date = get_obj(e, 'start_date', '')
    if start_date != '':
        dict_replace(e, 'start_date', '01/01/' + str(ref_year)) # always January 1st
    end_date = get_obj(e, 'end_date', '')
    if end_date != '':
        dict_replace(e, 'end_date', '31/12/' + str(ref_year + nyers - 1)) # always December 31st

# correct plyer, if available and necessary
# correct hlday and hlyer (ADDED 12/17/13 to handle vernalization problem in DSSAT)
for e in exp['experiments']:
    plt_dic = get_obj(e, 'dssat_simulation_control', {}) # only applies for DSSAT!
    if plt_dic != {}:
        planting = plt_dic['data'][0]['planting']
        pfday = double(planting['pfday'])
        plday = double(planting['plday'])
        if pfday > plday:
            plyer = str(double(planting['pfyer']) + 1)
            dict_replace(e, 'plyer', plyer)
        if pfday <= 15:
            hlyer = planting['pfyer']
        else:
            hlyer = str(double(planting['pfyer']) + 1)
        hlday = (pfday - 15) % 366
        dict_replace(e, 'hlyer', str(hlyer))
        dict_replace(e, 'hlday', str(hlday))

# close file
campaign.close()

# write experiment json file
json.dump(exp, open(options.outputfile, 'w'), indent = 2, separators = (',', ': '))

#!/usr/bin/env python

# import modules
import traceback
from .. import translator
from netCDF4 import Dataset
import os, datetime, warnings
from collections import OrderedDict as od
from numpy.ma import masked_array, masked_where
from numpy import nan, isnan, empty, zeros, ones, double, array, resize, vectorize, logical_and, floor, where
import out2psimsdaily
import sys

# Return headers and variable descriptions
def get_headers(indexes, orig_variables, long_names):
    result = {}
    for k in indexes.keys():
        try:
            vidx = orig_variables.index(k)
            long_name = long_names[vidx]
        except ValueError:
            long_name = ''
        result[k] = long_name
    return result

# Number of lines until data starts
def get_header_size(filename):
    count=0
    if os.path.exists(filename):
        f = open(filename, 'r')
        for line in f:
            count = count + 1
            if line.startswith('@'):
                break
    return count

# Return ordered dict with headers and header index locations
def get_indexes(filename):
    result = od()
    if os.path.exists(filename):
        f = open(filename, 'r')
        for line in f:
            if line.startswith('@'):
                headers = line.replace('.', '').strip().split()
                for i in range(len(headers) - 1, 0, -1):
                    prev = headers[i - 1]
                    result[headers[i]] = line.find(prev) + len(prev)
                break
    return reverse(result)

# Reverse an OrderedDict
def reverse(d1):
    d2 = od()
    while(len(d1) != 0):
        (k, v) = d1.popitem()
        d2[k] = v
    return d2

class Out2Psims(translator.Translator):

    def verify_params(self, latidx, lonidx):
        # Verify delta
        delta = self.config.get('delta', '30')
        delta = delta.split(',') 
        if len(delta) < 1 or len(delta) > 2:
            return (False, "Translator %s: wrong number of delta values (%s)" % (type(self).__name__, len(delta)))

        # Verify units
        units = self.config.get('var_units', '').split(',')
        variables = self.config.get('variables', '').split(',')
        if len(units) != len(variables):
            return (False, "Translator %s: Number of units (%s) must be same as number of variables (%s) " % (type(self).__name__, len(units), len(variables)))
        
        return(True, "Translator %s likes the parameters" % type(self).__name__)

    def run(self, latidx, lonidx):
        try:
            num_scenarios   = self.config.get('scens', '1')
            num_years       = self.config.get('num_years', '1')
            orig_variables  = self.config.get('variables').split(',')
            daily_variables = self.config.get('daily_variables')
            units           = self.config.get('var_units', '')
            delta           = self.config.get('delta', '30')
            ref_year        = self.config.get('ref_year', '1958')
            inputfiles      = self.config.get_dict(self.translator_type, 'inputfile', default = 'Summary.OUT,Evaluate.OUT').split(',')
            outputfile      = self.config.get_dict(self.translator_type, 'outputfile', default = '../../outputs/output_%04d_%04d.psims.nc' % (latidx, lonidx))
            failed_is_null  = bool(self.config.get_dict(self.translator_type, 'failed_is_null', default = False))
            scen_years      = self.config.get('scen_years', num_years)
            long_names      = self.config.get('long_names').split(',')

            start_idx = {}
            start_idx['Evaluate.OUT'] = get_indexes('Evaluate.OUT')
            start_idx['Summary.OUT']  = get_indexes('Summary.OUT')

            var_names = {}
            var_names['Evaluate.OUT'] = get_headers(start_idx['Evaluate.OUT'], orig_variables, long_names)
            var_names['Summary.OUT'] = {'SDAT': 'Simulation start date', 'PDAT': 'Planting date', \
                                        'EDAT': 'Emergence date', 'ADAT': 'Anthesis date', \
                                        'MDAT': 'Physiological maturity date', 'HDAT': 'Harvest date', \
                                        'DWAP': 'Planting material weight', 'CWAM': 'Tops weight at maturity', \
                                        'HWAM': 'Yield at harvest maturity', 'HWAH': 'Harvested yield', \
                                        'BWAH': 'By-product removed during harvest', 'PWAM': 'Pod/Ear/Panicle weight at maturity', \
                                        'HWUM': 'Unit wt at maturity', 'H#AM': 'Number of maturity', \
                                        'H#UM': 'Number at maturity', 'HIAM': 'Harvest index at maturity', \
                                        'LAIX': 'Leaf area index, maximum', 'IR#M': 'Irrigation applications', \
                                        'IRCM': 'Season irrigation', 'PRCM': 'Total season precipitation, simulation - harvest', \
                                        'ETCM': 'Total season evapotranspiration, simulation - harvest', 'EPCM': 'Total season transpiration', \
                                        'ESCM': 'Total season soil evaporation', 'ROCM': 'Season surface runoff', \
                                        'DRCM': 'Season water drainage', 'SWXM': 'Extractable water at maturity', \
                                        'NI#M': 'N applications', 'NICM': 'Inorganic N applied', \
                                        'NFXM': 'N fixed during season (kg/ha)', 'NUCM': 'N uptake during season', \
                                        'NLCM': 'N leached during season', 'NIAM': 'Inorganic N at maturity', \
                                        'CNAM': 'Tops N at maturity', 'GNAM': 'Grain N at maturity', \
                                        'PI#M': 'Number of P applications', 'PICM': 'Inorganic P applied', \
                                        'PUPC': 'Seasonal cumulative P uptake', 'SPAM': 'Soil P at maturity', \
                                        'KI#M': 'Number of K applications', 'KUPC': 'Seasonal cumulative K uptake', \
                                        'SKAM': 'Soil K at maturity', 'RECM': 'Residue applied', \
                                        'ONTAM': 'Total organic N at maturity, soil and surface', 'ONAM': 'Organic soil N at maturity', \
                                        'OPTAM': 'Total organic P at maturity, soil and surface', 'OPAM': 'Organic soil P at maturity', \
                                        'OCTAM': 'Total organic C at maturity, soil and surface', 'OCAM': 'Organic soil C at maturity', \
                                        'DMPPM': 'Dry matter-rainfall productivity', 'DMPEM': 'Dry matter-ET productivity', \
                                        'DMPTM': 'Dry matter-transp. productivity', 'DMPIM': 'Dry matter-irrigation productivity', \
                                        'YPPM': 'Yield-rainfall productivity', 'YPEM': 'Yield-ET productivity', \
                                        'YPTM': 'Yield-transportation productivity', 'YPIM': 'Yield-irrigation productivity', \
                                        'DPNAM': 'Dry matter-N fertilizer productivity', 'DPNUM': 'Dry matter-N uptake productivity', \
                                        'YPNAM': 'Yield-N fertilizer productivity', 'YPNUM': 'Yield-N uptake productivity', \
                                        'NDCH': 'Number of days from planting to harvest', 'TMAXA': 'Avg maximum air temperature', \
                                        'TMINA': 'Avg minimum air temperature', 'SRADA': 'Average solar radiation, planting - harvest', \
                                        'DAYLA': 'Average daylength, planting - harvest', 'CO2A': 'Average atmospheric CO2, planting - harvest', \
                                        'PRCP': 'Total season precipitation, planting - harvest', 'ETCP': 'Total evapotransportation, planting - harvest', \
                                        'ESCP': '', 'EPCP': ''}
            header_lengths = {}
            for inputfile in inputfiles:
                header_lengths[inputfile] = get_header_size(inputfile)

            # compute number of scenarios
            num_scenarios = int(num_scenarios * double(scen_years) / num_years)
            num_scenarios = num_scenarios
            num_years = num_years
            variables = {}

            # open summary file
            data = {}
            for fname in inputfiles:
                data[fname]  = open(fname).readlines()
                variables[fname] = []
                for v in orig_variables:
                    if v in var_names[fname].keys():
                        variables[fname].append(v)
                variables[fname] = array(variables[fname])

            latidx = int(latidx)
            lonidx = int(lonidx)
            delta = delta.split(',')
            if len(delta) < 1 or len(delta) > 2:
                raise Exception('Wrong number of delta values')
            latdelta = double(delta[0]) / 60. # convert from arcminutes to degrees
            londelta = latdelta if len(delta) == 1 else double(delta[1]) / 60.

            # get units
            units = units.split(',')
            if len(units) != len(orig_variables):
                raise Exception('Number of units must be same as number of variables')

            # Create daily output if needed
            if daily_variables: 
                o2pd = out2psimsdaily.Out2PsimsDaily(self.config, self.translator_type)
                result = o2pd.run(latidx, lonidx)
                if not result:
                    return result

            # compute latitude and longitude
            lat = 90. - latdelta * (latidx - 0.5)
            lon = -180. + londelta * (lonidx - 0.5)
            ref_date = datetime.datetime(ref_year, 1, 1)
            trim_data = {}
            all_variables = {}
            prohibited_variables = ['C#', 'CR', 'MODEL', 'TNAM', 'FNAM', 'WSTA', 'SOIL_ID']
            variable_idx = {}

            for fname in inputfiles:
                all_variables[fname] = start_idx[fname].keys()
                # search for variables within list of all variables
                variable_idx[fname] = zeros(len(variables[fname]))

                for i in range(len(variables[fname])):
                    v = variables[fname][i]
                    if not v in all_variables[fname]:
                        raise Exception('Variable {:s} not in summary file'.format(v))
                    if v in prohibited_variables:
                        variable_idx[fname][i] = -1 # skip variable
                        print 'Skipping variable', v
                    else:
                        variable_idx[fname][i] = all_variables[fname].index(v)

                # remove bad variables
                variables[fname] = variables[fname][variable_idx[fname] != -1]
                variable_idx[fname] = variable_idx[fname][variable_idx[fname] != -1]
                trim_data[fname] = self.parse_data(data[fname], all_variables[fname], variable_idx[fname], num_years, num_scenarios, variables[fname], start_idx[fname], header_lengths[fname])

            # create pSIMS NetCDF4 file
            dirname = os.path.dirname(outputfile)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            if dirname and not os.path.exists(dirname):
                raise Exception('Directory to output file does not exist')
            root_grp = Dataset(outputfile, 'w')

            # add latitude and longitude
            root_grp.createDimension('lon', 1)
            root_grp.createDimension('lat', 1)
            lon_var = root_grp.createVariable('lon', 'f8', 'lon')
            lon_var[:] = lon
            lon_var.units = 'degrees_east'
            lon_var.long_name = 'longitude'
            lat_var = root_grp.createVariable('lat', 'f8', 'lat')
            lat_var[:] = lat
            lat_var.units = 'degrees_north'
            lat_var.long_name = 'latitude'

            # create time and scenario dimensions
            root_grp.createDimension('time', None)
            root_grp.createDimension('scen', num_scenarios)

            # add time and scenario variables
            time_var = root_grp.createVariable('time', 'i4', 'time')
            time_var[:] = range(1, num_years + 1)
            time_var.units = 'growing seasons since {:s}'.format(str(ref_date))
            time_var.long_name = 'time'
            scenario_var = root_grp.createVariable('scen', 'i4', 'scen')
            scenario_var[:] = range(1, num_scenarios + 1)
            scenario_var.units = 'no'
            scenario_var.long_name = 'scenario'

            for fname in inputfiles:
                # resize data
                vararr = masked_array(zeros((len(variables[fname]), num_years, num_scenarios)), mask = ones((len(variables[fname]), num_years, num_scenarios)))
                for i in range(len(variables[fname])):
                    vararr[i] = resize(trim_data[fname][: num_years * num_scenarios, i], (num_scenarios, num_years)).T

                # mask against HWAM/HWAMS, if available
                HWAM_varname = None
                if 'HWAM' in variables[fname]:
                    HWAM_varname = 'HWAM'
                elif 'HWAMS' in variables[fname]:
                    HWAM_varname = 'HWAMS'

                if HWAM_varname:
                    hidx = where(variables[fname] == HWAM_varname)[0][0]
                    for i in range(len(variables[fname])):
                        if variables[fname][i] != HWAM_varname:
                            vararr[i] = masked_where(vararr[hidx] < 0, vararr[i])
                    if failed_is_null:
                        vararr[hidx] = masked_where(vararr[hidx] < 0, vararr[hidx]) # null
                    else:
                        vararr[hidx, vararr[hidx] < 0] = 0 # zero

                # add selected variables
                for i in range(len(variables[fname])):
                    var = root_grp.createVariable(variables[fname][i], 'f4', ('time', 'scen', 'lat', 'lon'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
                    var[:] = vararr[i]
                    var.units = units[i]
                    var.long_name = var_names[fname][variables[fname][i]]

            # close file
            root_grp.close()
            return True

        except:
            print "[%s] (%s/%s): %s" % (os.path.basename(__file__), latidx, lonidx, traceback.format_exc())
            return False

    # Parse DSSAT data
    def parse_data(self, data, all_variables, variable_idx, num_years, num_scenarios, variables, start_idx, header_length):
        nrows = len(data) - header_length
        header = data[header_length - 1]
        tot_years = num_years * num_scenarios
        if nrows % num_years:
            warnings.warn('Size of data not divisible by number of years')
            trim_data = -99 * ones((tot_years, len(variable_idx)))
        elif nrows < tot_years:
            warnings.warn('Exceeded size of data')
            trim_data = -99 * ones((tot_years, len(variable_idx)))
        else:
            ncols = len(all_variables)
            trim_data = empty((nrows, ncols), dtype = '|S20')
            trim_data[:] = '-99'

            for i in range(nrows):
                offs = 0 # offset to handle anomalous parsing
                for j in range(ncols):
                    sidx = start_idx.values()[j]
                    eidx = len(header) - 1 if j == ncols - 1 else start_idx.values()[j + 1]
                    if sidx + offs < len(header) and eidx > sidx:
                        dstr = data[i + header_length][sidx + offs : eidx + offs]
                        if '*' in dstr and not dstr.endswith('*'): # '*' not in last position
                            offset = dstr.rfind('*') - len(dstr) + 1
                            dstr = dstr[: offset]
                            offs += offset
                        trim_data[i, j] = dstr.strip() # remove spaces

            # select variables
            trim_data = trim_data[:, list(variable_idx)]

            # change values with *, -99.9, -99.90, and 9999999 to -99
            func = vectorize(lambda x: '*' in x or '-99.9' == x or '-99.90' == x or '9999999' == x or '0' == x)
            trim_data[func(trim_data)] = '-99'

            # convert to double
            trim_data = trim_data.astype(double)
            # convert units on the date variables
            trim_data[trim_data == -99] = nan
            v_idx = logical_and(variables != 'PDAT', variables != 'ADAT')
            for i in range(nrows):
                pdat = trim_data[i, variables == 'PDAT']
                adat = trim_data[i, variables == 'ADAT']
                mdat = trim_data[i, variables == 'MDAT']

                if pdat.size != 0 and not isnan(pdat):
                    pyer = int(floor(pdat / 1000.))
                    pday = int(pdat % 1000)
                    pdate = datetime.datetime(pyer, 1, 1) + datetime.timedelta(pday - 1)
                    trim_data[i, variables == 'PDAT'] = pday

                if adat.size != 0 and not isnan(adat):
                    ayer = int(floor(adat / 1000.))
                    aday = int(adat % 1000)
                    adate = datetime.datetime(ayer, 1, 1) + datetime.timedelta(aday - 1)
                    if not isnan(pdat):
                        trim_data[i, variables == 'ADAT'] = (adate - pdate).days

                if 'HDAT' in variables:
                    hdat = trim_data[i, variables == 'HDAT']
                    if isnan(mdat):
                        mdat = hdat
                    if not isnan(hdat):
                        hyer = int(floor(hdat / 1000.))
                        hday = int(hdat % 1000)
                        hdate = datetime.datetime(hyer, 1, 1) + datetime.timedelta(hday - 1)
                        if not isnan(pdat):
                            trim_data[i, variables == 'HDAT'] = (hdate - pdate).days

                if mdat.size != 0 and not isnan(mdat):
                    myer = int(floor(mdat / 1000.))
                    mday = int(mdat % 1000)
                    mdate = datetime.datetime(myer, 1, 1) + datetime.timedelta(mday - 1)
                    if not isnan(pdat):
                        trim_data[i, variables == 'MDAT'] = (mdate - pdate).days

                # null out years where MDAT > 365
                if trim_data[i, variables == 'MDAT'] > 365:
                    trim_data[i, v_idx] = nan
            trim_data[isnan(trim_data)] = -99
        return trim_data

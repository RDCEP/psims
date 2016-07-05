#!/usr/bin/env python

# import modules
from .. import translator
from netCDF4 import Dataset
import os, datetime, warnings, traceback
from collections import OrderedDict as od
from numpy.ma import masked_array, masked_where
from numpy import nan, isnan, empty, zeros, ones, double, array, resize, vectorize, logical_and, floor, where

class Out2Psims(translator.Translator):
    # dictionary of variable descriptions
    var_names = {'SDAT': 'Simulation start date', 'PDAT': 'Planting date', \
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

    # WORKS FOR DSSAT VER 4.5.1.023
    # NOTE: MAY NEED TO CHANGE FOR FUTURE VERSIONS!
    start_idx = od([('RUNNO', 0), ('TRNO', 9), ('R#', 16), ('O#', 19), ('C#', 22), \
                    ('CR', 25), ('MODEL', 28), ('TNAM', 37), ('FNAM', 63), ('WSTA', 72), \
                    ('SOIL_ID', 81), ('SDAT', 92), ('PDAT', 100), ('EDAT', 108), \
                    ('ADAT', 116), ('MDAT', 124), ('HDAT', 132), ('DWAP', 140), \
                    ('CWAM', 146), ('HWAM', 154), ('HWAH', 162), ('BWAH', 170), \
                    ('PWAM', 178), ('HWUM', 184), ('H#AM', 192), ('H#UM', 198), \
                    ('HIAM', 206), ('LAIX', 212), ('IR#M', 218), ('IRCM', 224), \
                    ('PRCM', 230), ('ETCM', 236), ('EPCM', 242), ('ESCM', 248), \
                    ('ROCM', 254), ('DRCM', 260), ('SWXM', 266), ('NI#M', 272), \
                    ('NICM', 278), ('NFXM', 284), ('NUCM', 290), ('NLCM', 296), \
                    ('NIAM', 302), ('CNAM', 308), ('GNAM', 314), ('PI#M', 320), \
                    ('PICM', 326), ('PUPC', 332), ('SPAM', 338), ('KI#M', 344), \
                    ('KICM', 350), ('KUPC', 356), ('SKAM', 362), ('RECM', 368), \
                    ('ONTAM', 374), ('ONAM', 381), ('OPTAM', 388), ('OPAM', 395), \
                    ('OCTAM', 402), ('OCAM', 410), ('DMPPM', 418), ('DMPEM', 427), \
                    ('DMPTM', 436), ('DMPIM', 445), ('YPPM', 454), ('YPEM', 463), \
                    ('YPTM', 472), ('YPIM', 481), ('DPNAM', 490), ('DPNUM', 499), \
                    ('YPNAM', 508), ('YPNUM', 517), ('NDCH', 526), ('TMAXA', 532), \
                    ('TMINA', 538), ('SRADA', 544), ('DAYLA', 550), ('CO2A', 556), \
                    ('PRCP', 563), ('ETCP', 570), ('ESCP', 577), ('EPCP', 584)]) # goes to len(data[3]) - 1

    def run(self, latidx, lonidx):
        try:
            num_scenarios  = self.config.get('scens', '1')
            num_years      = self.config.get('num_years', '1')
            variables      = self.config.get('variables', '')
            units          = self.config.get('var_units', '')
            delta          = self.config.get('delta', '30')
            ref_year       = self.config.get('ref_year', '1958')
            inputfile      = self.config.get_dict(self.translator_type, 'inputfile', default = 'data/Summary.OUT')
            outputfile     = self.config.get_dict(self.translator_type, 'outputfile', default = '../../outputs/output_%04d_%04d.psims.nc' % (latidx, lonidx))
            failed_is_null = bool(self.config.get_dict(self.translator_type, 'failed_is_null', default = False))
            scen_years     = self.config.get('scen_years', num_years)

            # compute number of scenarios
            num_scenarios = int(num_scenarios * double(scen_years) / num_years)

            # open summary file
            data = open(inputfile).readlines()

            # get variables
            num_scenarios = num_scenarios
            num_years = num_years
            variables = array(variables.split(',')) # split variable names
            latidx = int(latidx)
            lonidx = int(lonidx)
            delta = delta.split(',')
            if len(delta) < 1 or len(delta) > 2: raise Exception('Wrong number of delta values')
            latdelta = double(delta[0]) / 60. # convert from arcminutes to degrees
            londelta = latdelta if len(delta) == 1 else double(delta[1]) / 60.

            # get units
            units = units.split(',')
            if len(units) != len(variables):
                raise Exception('Number of units must be same as number of variables')

            # get all variables
            all_variables = self.start_idx.keys()

            # search for variables within list of all variables
            prohibited_variables = ['C#', 'CR', 'MODEL', 'TNAM', 'FNAM', 'WSTA', 'SOIL_ID']
            variable_idx = zeros(len(variables))
            for i in range(len(variables)):
                v = variables[i]
                if not v in all_variables:
                    raise Exception('Variable {:s} not in summary file'.format(v))
                if v in prohibited_variables:
                    variable_idx[i] = -1 # skip variable
                    print 'Skipping variable', v
                else:
                    variable_idx[i] = all_variables.index(v)

            # remove bad variables
            variables    = variables[variable_idx != -1]
            variable_idx = variable_idx[variable_idx != -1]

            # compute latitude and longitude
            lat = 90. - latdelta * (latidx - 0.5)
            lon = -180. + londelta * (lonidx - 0.5)

            # get reference time
            ref_date = datetime.datetime(ref_year, 1, 1)

            # parse data body
            nrows = len(data) - 4
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
                        sidx = self.start_idx.values()[j]
                        eidx = len(data[3]) - 1 if j == ncols - 1 else self.start_idx.values()[j + 1]
                        if sidx + offs < len(data[3]) and eidx > sidx:
                            dstr = data[i + 4][sidx + offs : eidx + offs]
                            if '*' in dstr and not dstr.endswith('*'): # '*' not in last position
                                offset = dstr.rfind('*') - len(dstr) + 1
                                dstr = dstr[: offset]
                                offs += offset
                            trim_data[i, j] = dstr.strip() # remove spaces

                # select variables
                trim_data = trim_data[:, list(variable_idx)]

                # change values with *, -99.9, -99.90, and 9999999 to -99
                func = vectorize(lambda x: '*' in x or '-99.9' == x or '-99.90' == x or '9999999' == x)
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

                    if not isnan(pdat):
                        pyer = int(floor(pdat / 1000.))
                        pday = int(pdat % 1000)
                        pdate = datetime.datetime(pyer, 1, 1) + datetime.timedelta(pday - 1)
                        trim_data[i, variables == 'PDAT'] = pday

                    if not isnan(adat):
                        ayer = int(floor(adat / 1000.))
                        aday = int(adat % 1000)
                        adate = datetime.datetime(ayer, 1, 1) + datetime.timedelta(aday - 1)
                        if not isnan(pdat):
                            trim_data[i, variables == 'ADAT'] = (adate - pdate).days

                    if not isnan(mdat):
                        myer = int(floor(mdat / 1000.))
                        mday = int(mdat % 1000)
                        mdate = datetime.datetime(myer, 1, 1) + datetime.timedelta(mday - 1)
                        if not isnan(pdat):
                            trim_data[i, variables == 'MDAT'] = (mdate - pdate).days

                    # null out years where MDAT > 365
                    if trim_data[i, variables == 'MDAT'] > 365:
                        trim_data[i, v_idx] = nan
                trim_data[isnan(trim_data)] = -99

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

            # resize data
            vararr = masked_array(zeros((len(variables), num_years, num_scenarios)), mask = ones((len(variables), num_years, num_scenarios)))
            for i in range(len(variables)):
                vararr[i] = resize(trim_data[: num_years * num_scenarios, i], (num_scenarios, num_years)).T

            # mask against HWAM, if available
            if 'HWAM' in variables:
                hidx = where(variables == 'HWAM')[0][0]
                for i in range(len(variables)):
                    if variables[i] != 'HWAM':
                        vararr[i] = masked_where(vararr[hidx] < 0, vararr[i])
                if failed_is_null:
                    vararr[hidx] = masked_where(vararr[hidx] < 0, vararr[hidx]) # null
                else:
                    vararr[hidx, vararr[hidx] < 0] = 0 # zero

            # add selected variables
            for i in range(len(variables)):
                var = root_grp.createVariable(variables[i], 'f4', ('time', 'scen', 'lat', 'lon'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
                var[:] = vararr[i]
                var.units = units[i]
                var.long_name = self.var_names[variables[i]]

            # close file
            root_grp.close()
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

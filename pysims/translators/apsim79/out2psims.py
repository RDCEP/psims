#!/usr/bin/env python

import calendar
import datetime
import os
import traceback
from netCDF4 import Dataset
from numpy import array, ones, asarray, double, where
from .. import translator


def compute_next_idx(year, month, prev_idx, prev_year):
    dy = year - prev_year
    if dy <= 1:
        # same year but different month OR next year => next growing season
        idx = prev_idx + 1
    else:
        # more than one year has elapsed
        idx = prev_idx + dy - (month <= 2)
    return idx


class Out2Psims(translator.Translator):
    def run(self, latidx, lonidx):
        try:
            num_scenarios = self.config.get('scens')
            num_years = self.config.get('num_years')
            variables = self.config.get('variables')
            units = self.config.get('var_units')
            delta = self.config.get('delta')
            ref_year = self.config.get('ref_year')
            inputfile = self.config.get_dict(self.translator_type, 'inputfile', default='Generic.out')
            outputfile = self.config.get_dict(self.translator_type, 'outputfile',
                                              default='../../outputs/output_%04d_%04d.psims.nc' % (latidx, lonidx))
 
            # get out files(s)
            num_scenarios = num_scenarios
            basename, fileext = os.path.splitext(inputfile)
            outfiles = [''] * num_scenarios
            for i in range(num_scenarios):
                outfiles[i] = inputfile if not i else basename + str(i) + fileext
            
            # get variables
            variables = array(variables.split(','))
            latidx = int(latidx)
            lonidx = int(lonidx)
            delta = delta.split(',')
            if len(delta) < 1 or len(delta) > 2:
                raise Exception('Wrong number of delta values')
            # convert from arcminutes to degrees
            latdelta = double(delta[0]) / 60.
            londelta = latdelta if len(delta) == 1 else double(delta[1]) / 60.
            
            # get number of variables
            num_vars = len(variables)
            
            # get units
            units = units.split(',')
            if len(units) != num_vars:
                raise Exception('Number of units must be same as number of variables')
            
            # compute latitude and longitude
            lat = 90. - latdelta * (latidx - 0.5)
            lon = -180. + londelta * (lonidx - 0.5)
            
            # get reference time, number of years, and dates
            ref_year = ref_year
            ref_date = datetime.datetime(ref_year, 1, 1)
            num_years = num_years
            dates = range(ref_year, ref_year + num_years)
            
            # whether or not planting_date is among reported variables
            has_pdate = 'planting_date' in variables
            if has_pdate:
                pdate_idx = where(variables == 'planting_date')[0][0]
                mth2num = {v: k for k, v in enumerate(calendar.month_abbr)}
            
            # iterate through scenarios
            var_data = -99 * ones((num_years, num_scenarios, num_vars))
            for i in range(num_scenarios):
                try:
                    data = [l.split() for l in tuple(open(outfiles[i]))]
                except IOError:
                    print 'Out file', i + 1, 'does not exist'
                    continue
                # no data, move to next file
                if len(data) < 5:
                    continue
                num_data = len(data[4:])
                
                # search for variables within list of all variables
                all_variables = data[2]
                variable_idx = []
                for v in variables:
                    if v not in all_variables:
                        raise Exception('Variable {:s} not in out file {:d}'.format(v, i + 1))
                    else:
                        variable_idx.append(all_variables.index(v))
               
                # remove header, select variables, and convert to numpy array of doubles
                if has_pdate:
                    pdate_idx2 = all_variables.index('planting_date')
                for j in range(num_data):
                    # blank line
                    if not data[4 + j]:
                        continue
                    # number of dates in file exactly matches number of years
                    if num_data == num_years:
                        idx = j
                    else:
                        pyear = int(data[4 + j][pdate_idx2].split('_')[2])
                        idx = dates.index(pyear)
                    array_data = asarray(data[4 + j])[variable_idx]
                    array_data[array_data == '?'] = '-99' # replace '?' with '-99'
                    if has_pdate:
                        # convert pdate from dd_mmm_yyyy to Julian day
                        pdate = array_data[pdate_idx].split('_')
                        pdate = datetime.date(int(pdate[2]), mth2num[pdate[1]], int(pdate[0]))
                        array_data[pdate_idx] = pdate.strftime('%j')
                    var_data[idx, i, :] = array_data.astype(double)
            
            # create pSIMS NetCDF3 file
            root_grp = Dataset(outputfile, 'w', format='NETCDF3_CLASSIC')
            
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
            
            # add data
            for i in range(num_vars):
                var = root_grp.createVariable(variables[i], 'f4', ('time', 'scen', 'lat', 'lon'), zlib=True,
                                              shuffle=False, complevel=9, fill_value=1e20)
                var[:] = var_data[:, :, i]
                var.units = units[i]
                var.long_name = variables[i]
            
            # close file
            root_grp.close()
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

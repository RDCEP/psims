#!/usr/bin/env python

# import modules
from .. import translator
from datetime import datetime, timedelta
from numpy.ma import masked_array
from netCDF4 import Dataset as nc
from netCDF4 import date2num
from numpy import double, zeros, ones
import os
import traceback
import pandas as pd
import numpy as np
import netCDF4

# Return a list of variables to be used per dssat filename
def variables_by_file(df, variables):
    result = {}
    for index,row in df.iterrows():
        if row.variable in variables:
            try:
                result[row.filename].append(row.variable)
            except KeyError:
                result[row.filename] = [row.variable]
    for v in variables:
        if v not in [x for z in result.values() for x in z]:
            print "Warning: Cannot find variable %s, skipping" % v
    return result

class NoOutput2PsimsDaily(translator.Translator):
    def run(self, latidx, lonidx):
        try:
            num_scenarios   = self.config.get('scens', '1')
            num_years       = self.config.get('num_years', '1')
            variables       = self.config.get('variables', '')
            units           = self.config.get('var_units', '')
            delta           = self.config.get('delta', '30')
            ref_year        = self.config.get('ref_year', '1958')
            ref_day         = datetime(ref_year, 1, 1)
            daily_csv       = pd.read_csv('%s%s%s' % (os.path.dirname(__file__), os.sep, 'daily_variables.csv'))
            outputfile      = self.config.get_dict(self.translator_type, 'outputfile', default = '../../outputs/daily_%04d_%04d.psims.nc' % (latidx, lonidx))
            scen_years      = self.config.get('scen_years', num_years)
            start_date      = datetime(ref_year, 1, 1)
            end_date        = datetime(ref_year + num_years - 1, 12, 31)
            runs            = num_scenarios
            num_scenarios   = int(num_scenarios * np.double(scen_years) / num_years)
            latidx          = int(latidx)
            lonidx          = int(lonidx)
            delta           = delta.split(',')
            latdelta        = np.double(delta[0]) / 60.
            londelta        = latdelta if len(delta) == 1 else np.double(delta[1]) / 60.
            scens           = np.arange(num_scenarios)
            variables       = self.config.get('daily_variables').split(',')
            variable_files  = variables_by_file(daily_csv, variables)
            lat             = 90. - latdelta * (latidx - 0.5)
            lon             = -180. + londelta * (lonidx - 0.5)
            fill_value      = netCDF4.default_fillvals['f4']
            data            = {}
            dates           = {}

            # Generate dates
            for year in range(ref_year, ref_year+num_years):
                start_date  = datetime(year, 1, 1)
                stop_date   = start_date + 730
                dates[year] = [start_date + timedelta(days=x) for x in range(0, (stop_date-start_date).days + 1)]

            # Generate empty data
            for filename,varlist in variable_files.iteritems():
                for v in varlist:
                    for year in range(ref_year, ref_year+num_years):
                        try:
                            data[year][v] = np.empty(shape=(len(dates[year]), len(scens), 1, 1), dtype=float)
                            data[year][v].fill(fill_value)
                        except KeyError:
                            data[year] = {}
                            data[year][v] = np.empty(shape=(len(dates[year]), len(scens), 1, 1), dtype=float)
                            data[year][v].fill(fill_value)

            # Save to NetCDF
            for year in data:
                current_outputfile = outputfile.replace('psims.nc', '%04d.psims.nc' % year)
                netcdf_output      = netCDF4.Dataset(current_outputfile, 'w', format='NETCDF4', fill_value=fill_value, zlib=None)
                scen_dim           = netcdf_output.createDimension('scen', len(scens))
                scen_var           = netcdf_output.createVariable('scen', 'i4', ('scen'))
                scen_var.units     = "count"
                scen_var.long_name = "scenario"
                scen_var[:]        = scens[:]
                time_dim           = netcdf_output.createDimension('time', None)
                time_var           = netcdf_output.createVariable('time', 'i4', ('time'))
                time_var.units     = "days since %04d-%02d-%02d 00:00:00" % (ref_day.year, ref_day.month, ref_day.day)
                time_var.calendar  = 'gregorian'
                lat_dim            = netcdf_output.createDimension('lat', 1)
                lat_var            = netcdf_output.createVariable('lat', 'f8', ('lat'))
                lat_var.units      = "degrees_north"
                lat_var.long_name  = "longitude"
                lat_var[:]         = lat
                lon_dim            = netcdf_output.createDimension('lon', 1)
                lon_var            = netcdf_output.createVariable('lon', 'f8', ('lon'))
                lon_var.units      = "degrees_east"
                lon_var.long_name  = "longitude"
                lon_var[:]         = lon
                first_idx          = None
                last_idx           = None
                times              = []

                for v in data[year]:
                    indexes = []
                    for day in dates[year]:
                        indexes.append((day - ref_day).days)
                    time_var[:] = indexes
                    first_idx   = indexes[0]
                    last_idx    = indexes[-1]

                for key,val in data[year].iteritems():
                    var = netcdf_output.createVariable(key, 'f4', ('time', 'scen', 'lat', 'lon'), fill_value=fill_value)
                    var[:] = val[first_idx:last_idx, :, 0, 0]
                    units = daily_csv['units'][daily_csv["variable"] == key].iloc[0]
                    if units:
                        var.units = units
                    long_name = daily_csv['long_name'][daily_csv["variable"] == key].iloc[0]
                    if long_name:
                        var.long_name = long_name

                times = []
                netcdf_output.close()
            return True
        except:
            print "[%s]: (%04d/%04d) %s" % (os.path.basename(__file__), latidx, lonidx, traceback.format_exc())
            return False


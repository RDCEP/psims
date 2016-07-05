#!/usr/bin/env python
import calendar
import netCDF4
import numpy as np
import os
import pandas as pd
import sys
import traceback
from cStringIO import StringIO
from datetime import datetime, timedelta
from .. import translator

# Return int with num days per year
def days_per_year(year):
    if calendar.isleap(year):
        return 366
    return 365

# Return a list of date indexes to be included in a yearly netcdf (limit to 730)
def indexes(year, ref_year):
    dates       = []
    ref_day     = datetime(ref_year, 1, 1)
    first_index = (datetime(year, 1, 1) - ref_day).days
    last_index  = first_index + 730
    return range(first_index, last_index)

# Get index of matching date from list
def get_date_index(dates, dt):
    if len(dates) == 0:
        return None
    first = dates[0]
    index = (dt - first).days
    if index >= 0 and index < len(dates) and dates[index] == dt:
        return index
    else:
        return None

# Parse daily DSSAT output and append to a dictionary of numpy arrays
def read_daily(filename, variables, data, scens, scen_years, runs, num_years, lat, lon, fill_value, ref_year, dates):
    daily_file = open(filename, 'r')
    is_data    = False
    run        = -1
    indexes    = {}
    for line in daily_file:
        line = line.strip()
        if not line: continue
        if line.startswith('*'):
            is_data = False
        elif line.startswith('@'):
            headers = []
            run += 1
            scen_index = int(run * np.double(scen_years) / (num_years))
            line = line.lstrip('@')
            is_data = True
            start_year = ref_year + (run % num_years)
        if is_data:
            line = line.split()
            if len(headers) == 0:
                for i,l in enumerate(line):
                    line[i] = l.replace('%', 'P')
                headers.extend(line)
                for header in headers:
                    indexes[header] = headers.index(header)
            else:
                year = int(line[indexes['YEAR']])
                doy  = int(line[indexes['DOY']])
                dt = datetime(year, 1, 1) + timedelta(days=doy - 1)
                dt_position = get_date_index(dates, dt)
                for v in variables:
                    if dt_position is not None and v in indexes:
                        val = line[indexes[v]]
                        data[start_year][v][dt_position, scen_index, 0, 0] = val
    return data


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


class Out2PsimsDaily(translator.Translator):
    def run(self, latidx, lonidx):
        try:
            num_scenarios   = self.config.get('scens', '1')
            num_years       = self.config.get('num_years', '1')
            variables       = self.config.get('variables', '')
            units           = self.config.get('var_units', '')
            delta           = self.config.get('delta', '30')
            ref_year        = self.config.get('ref_year', '1958')
            daily_csv       = pd.read_csv('%s%s%s' % (os.path.dirname(__file__), os.sep, 'daily_variables.csv'))
            outputfile      = self.config.get_dict(self.translator_type, 'outputfile', default = '../../outputs/daily_%04d_%04d.psims.nc' % (latidx, lonidx))
            scen_years      = self.config.get('scen_years', num_years)
            start_date      = datetime(ref_year, 1, 1)
            end_date        = datetime(ref_year + num_years - 1, 12, 31)
            dates           = [start_date + timedelta(days=x) for x in range(0, (end_date-start_date).days+1)]
            runs            = num_scenarios
            num_scenarios   = int(num_scenarios * np.double(scen_years) / num_years)
            latidx          = int(latidx)
            lonidx          = int(lonidx)
            delta           = delta.split(',')
            latdelta        = np.double(delta[0]) / 60. # convert from arcminutes to degrees
            londelta        = latdelta if len(delta) == 1 else np.double(delta[1]) / 60.
            scens           = np.arange(num_scenarios)
            variables       = self.config.get('daily_variables').split(',')
            variable_files  = variables_by_file(daily_csv, variables)
            lat             = 90. - latdelta * (latidx - 0.5)
            lon             = -180. + londelta * (lonidx - 0.5)
            fill_value      = netCDF4.default_fillvals['f4']
            data            = {}

            # Populate data array
            for filename,varlist in variable_files.iteritems():
                for v in varlist:
                    for start_year in range(ref_year, ref_year+num_years):
                        try:
                            data[start_year][v] = np.empty(shape=(len(dates), len(scens), 1, 1), dtype=float)
                            data[start_year][v].fill(fill_value)
                        except KeyError:
                            data[start_year] = {}
                            data[start_year][v] = np.empty(shape=(len(dates), len(scens), 1, 1), dtype=float)
                            data[start_year][v].fill(fill_value)
                data = read_daily(filename, varlist, data, scens, scen_years, runs, num_years, 0, 0, fill_value, ref_year, dates)

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
                time_var.units     = "days since %04d-%02d-%02d 00:00:00" % (start_date.year, start_date.month, start_date.day)
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
                    times       = indexes(year, ref_year)
                    time_var[:] = times
                    first_idx   = times[0]
                    last_idx    = times[-1]

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
            print "[%s] (%s/%s): %s" % (os.path.basename(__file__), latidx, lonidx, traceback.format_exc())
            return False

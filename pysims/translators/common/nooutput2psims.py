#!/usr/bin/env python

# import modules
from .. import translator
from numpy.ma import masked_array
from netCDF4 import Dataset as nc
from numpy import double, zeros, ones
import os
import traceback
import nooutput2psimsdaily

class NoOutput2Psims(translator.Translator):

    def run(self, latidx, lonidx):
        try:
            outputfile      = self.config.get_dict(self.translator_type, 'outputfile', default = '../../outputs/output_%04d_%04d.psims.nc' % (latidx, lonidx))
            num_years       = self.config.get('num_years')
            scens           = self.config.get('scens')
            ref_year        = self.config.get('ref_year')
            delta           = self.config.get('delta')
            variables       = self.config.get('variables', default = '')
            daily_variables = self.config.get('daily_variables')
            var_units       = self.config.get('var_units', default = '')
            long_names      = self.config.get('long_names', default = '')
            cal_vars        = self.config.get('cal_vars', default = '')
            cal_units       = self.config.get('cal_units', default = '')
            cal_long_names  = self.config.get('cal_long_names', default = '')
            scen_years      = self.config.get('scen_years', num_years)

            # compute number of scenarios
            scens              = int(scens * double(scen_years) / num_years)
            latdelta, londelta = [double(d) / 60 for d in delta.split(',')]
            variables          = variables.split(',')
            var_units          = var_units.split(',')
            long_names         = long_names.split(',')
            cal_vars           = cal_vars.split(',')
            cal_units          = cal_units.split(',')
            cal_long_names     = cal_long_names.split(',')
            latitude           = 90 - latdelta * (latidx - 0.5)
            longitude          = -180 + londelta * (lonidx - 0.5)
   
            # Generate daily output 
            if daily_variables: 
                no2psd = nooutput2psimsdaily.NoOutput2PsimsDaily(self.config, self.translator_type)
                result = no2psd.run(latidx, lonidx) 
                if not result:
                    return result
             
            deft_arr = masked_array(zeros((num_years, scens, 1, 1)), mask = ones((num_years, scens, 1, 1)))
    
            with nc(outputfile, 'w') as f:
                f.createDimension('lat', 1)
                latvar = f.createVariable('lat', 'f8', 'lat')
                latvar[:] = latitude
                latvar.units = 'degrees_north'
                latvar.long_name = 'latitude'
    
                f.createDimension('lon', 1)
                lonvar = f.createVariable('lon', 'f8', 'lon')
                lonvar[:] = longitude
                lonvar.units = 'degrees_east'
                lonvar.long_name = 'longitude'
    
                f.createDimension('time', None) # time is lead dimension
                timevar = f.createVariable('time', 'i4', 'time')
                timevar[:] = range(1, 1 + num_years)
                timevar.units = 'growing seasons since %d-01-01 00:00:00' % ref_year
                timevar.long_name = 'time'
    
                f.createDimension('scen', scens)
                scenvar = f.createVariable('scen', 'i4', 'scen')
                scenvar[:] = range(1, 1 + scens)
                scenvar.units = 'no'
                scenvar.long_name = 'scenario'
    
                for i in range(len(variables)):
                    vvar = f.createVariable(variables[i], 'f4', ('time', 'scen', 'lat', 'lon'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
                    vvar[:] = deft_arr
                    vvar.units = var_units[i]
                    vvar.long_name = long_names[i]
    
                for i in range(len(cal_vars)):
                    if cal_vars[i] != '':
                        vvar = f.createVariable(cal_vars[i], 'f4', ('time', 'scen', 'lat', 'lon'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
                        vvar[:] = deft_arr
                        vvar.units = cal_units[i]
                        vvar.long_name = cal_long_names[i]

                return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

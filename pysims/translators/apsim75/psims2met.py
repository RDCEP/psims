#!/usr/bin/env python

import os, sys, traceback
sys.path.append('../utils')
import warnings
from co2 import CO2
from fillgaps import fill
from dewpoint import dewpoint
import re, stat, datetime
from netCDF4 import Dataset as nc
from optparse import OptionParser
from collections import OrderedDict as od
from numpy import empty, array, concatenate, savetxt, zeros, intersect1d, inf, ones, append, resize, VisibleDeprecationWarning
from .. import translator

# search for patterns in variable list
def isin(var, varlist):
    vararr = array(varlist)
    patt = re.compile(var + '_*')
    matches = array([bool(patt.match(v)) for v in vararr])
    return list(vararr[matches])

class Psims2Met(translator.Translator):

    def run(self, latidx, lonidx):
        try:
    
            inputfile  = self.config.get_dict(self.translator_type, 'inputfile', default='1.clim.nc4')
            variables  = self.config.get_dict(self.translator_type, 'variables').split(',')
            co2file    = self.config.get_dict(self.translator_type, 'co2file')
            outputfile = self.config.get_dict(self.translator_type, 'outputfile')
            tapp       = self.config.get_dict(self.translator_type, 'tapp')
     
            # call translator app if applicable
            istmp = False
            if not tapp is None:
                tmpfile = inputfile + '.shift'
                tapp += ' -i %s -o %s' % (inputfile, tmpfile) # add input and output file options
                ret = os.system(tapp)
                if ret != 0:
                    raise Exception('Application %s failed' % tapp)
                    if os.path.isfile(tmpfile): os.remove(tmpfile)
                    exit(1)
                inputfile = tmpfile
                istmp = True
            
            # open netcdf file
            infile = nc(inputfile)
            
            # get time
            vlist = infile.variables.keys()
            if 'time' in vlist: # make sure time is in file
                time = infile.variables['time'][:]
                time_units = infile.variables['time'].units
            else:
                raise Exception('Missing variable time')
            
            # get reference time
            ts = time_units.split('days since ')[1].split(' ')
            yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
            if len(ts) > 1:
                hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
            else:
                hr0 = min0 = sec0 = 0
            ref = datetime.datetime(yr0, mth0, day0, hr0, min0, sec0)
            
            # get latitude, longitude
            lat, lon  = infile.variables['lat'][0], infile.variables['lon'][0]
            
            # get scenarios
            ns = infile.variables['scen'].size if 'scen' in infile.variables else 1
            
            # get all data
            var_lists = od([('radn', ['solar', 'rad', 'rsds', 'srad']), \
                            ('maxt', ['tmax', 'tasmax']), \
                            ('mint', ['tmin', 'tasmin']), \
                            ('rain', ['precip', 'pr', 'rain']), \
                            ('wind', ['wind', 'windspeed']), \
                            ('dewp', ['dew', 'dewp', 'dewpoint', 'tdew']), \
                            ('hur',  ['rhum', 'hur']), \
                            ('hus',  ['hus']), \
                            ('vp',   ['vap', 'vapr', 'vap']), \
                            ('tas',  ['tas']), \
                            ('ps',   ['ps'])])
            unit_names = array([['mj/m^2', 'mj/m2', 'mjm-2', 'mjm-2day-1', 'mjm-2d-1', 'mj/m^2/day', 'mj/m2/day'], \
                                ['oc', 'degc', 'degreesc', 'c'], ['oc', 'degc', 'degreesc', 'c'], ['mm', 'mm/day'], \
                                ['m/s', 'ms-1'], ['oc', 'degc', 'degreesc', 'c'], \
                                ['%'], ['kgkg-1', 'kg/kg'], ['mb'], ['oc', 'degc', 'c'], ['mb']])
            unit_names2 = array(['MJ/m^2', 'oC', 'oC', 'mm', 'm/s', 'oC', '%', 'kgkg-1', 'mb', 'oC', 'mb'])
            
            var_keys  = var_lists.keys()
            var_names = array(var_keys)
            nt, nv    = len(time), len(var_names)
            alldata   = empty((nv, ns, nt))
            found_var = zeros(nv, dtype = bool)
            
            for i in range(nv):
                var_name = var_names[i]
                var_list = var_lists[var_name]
            
                for v in var_list:
                    matchvar = isin(v, variables)
                    if matchvar == []: continue
            
                    matchvar = matchvar[0] # take first match
                    if not matchvar in vlist: continue
            
                    alldata[i] = infile.variables[matchvar][:].squeeze()
                    alldata[i] = fill(alldata[i], time, ref, var_name)
            
                    if 'units' in infile.variables[matchvar].ncattrs(): 
                        units = infile.variables[matchvar].units
                    else:
                        units = ''
                    units = units.lower().replace(' ', '')
            
                    # convert units, if necessary
                    if var_name == 'radn' and units in ['wm-2', 'w/m^2', 'w/m2']: # solar
                        alldata[i] *= 0.0864
                        units = unit_names[i][0]
                    elif var_name in ['maxt', 'mint', 'tas', 'dewp'] and units in ['k', 'degrees(k)', 'deg(k)']: # temperature
                        alldata[i] -= 273.15
                        units = unit_names[i][0]
                    elif var_name == 'rain' and units in ['kgm-2s-1', 'kg/m^2/s', 'kg/m2/s']: # precip
                        alldata[i] *= 86400
                        units = unit_names[i][0]
                    elif var_name == 'wind': # wind
                        if units in ['kmday-1', 'kmdy-1', 'km/day', 'km/dy']:
                            alldata[i] *= 1000. / 86400
                            units = unit_names[i][0]
                        elif units in ['kmh-1', 'kmhr-1', 'km/h', 'km/hr']:
                            alldata[i] *= 1000. / 3600
                            units = unit_names[i][0]
                        elif units in ['milesh-1', 'mileshr-1', 'miles/h', 'miles/hr']:
                            alldata[i] *= 1609.34 / 3600
                            units = unit_names[i][0]
                    elif var_name in ['vp', 'ps'] and units == 'pa': # vapor pressure
                        alldata[i] /= 100.
                        units = unit_names[i][0]
                    elif var_name == 'hus' and units == 'gkg-1': # specific humdiity
                        alldata[i] /= 1000.
                        units = unit_names[i][0]
                    elif var_name == 'hur' and units in ['', '0-1']: # relative humidity
                        alldata[i] *= 100.
                        units = unit_names[i][0]
            
                    if not units.lower() in unit_names[i]:
                        raise Exception('Unknown units for %s' % var_name)
            
                    found_var[i] = True
                    break
            
                if not found_var[i] and var_name in ['radn', 'maxt', 'mint', 'rain']:
                    raise Exception('Missing necessary variable %s' % var_name)
            
            # calculate dewpoint temperature if possible
            dewp_idx = var_keys.index('dewp')
            hur_idx  = var_keys.index('hur')
            hus_idx  = var_keys.index('hus')
            vap_idx  = var_keys.index('vp')
            tas_idx  = var_keys.index('tas')
            tmin_idx = var_keys.index('mint')
            tmax_idx = var_keys.index('maxt')
            ps_idx   = var_keys.index('ps')
            
            if not found_var[dewp_idx] and intersect1d(var_lists['dewp'], variables).size:
                if found_var[vap_idx]: # use vapor pressure
                    alldata[dewp_idx] = dewpoint(vap = alldata[vap_idx])
                    found_var[dewp_idx] = True
                elif found_var[hur_idx]: # use relative humidity and temperature
                    if found_var[tas_idx]:
                        alldata[dewp_idx] = dewpoint(hur = alldata[hur_idx], tas = alldata[tas_idx])
                    else:
                        alldata[dewp_idx] = dewpoint(hur = alldata[hur_idx], tmax = alldata[tmax_idx], tmin = alldata[tmin_idx])
                    found_var[dewp_idx] = True
                elif found_var[hus_idx] and found_var[ps_idx]: # use specific humidity and surface pressure
                    alldata[dewp_idx] = dewpoint(hus = alldata[hus_idx], ps = alldata[ps_idx])
                    found_var[dewp_idx] = True
                else:
                    raise Exception('Failed to compute dewpoint temperature')
            
            # close input file
            infile.close()
            
            # remove missing nonmandatory variables from array
            warnings.filterwarnings("ignore", category=VisibleDeprecationWarning) 
            alldata     = alldata[: 6]
            found_var   = found_var[: 6]
            nv          = found_var.sum()
            var_names   = var_names[found_var]
            alldata     = alldata[found_var]
            unit_names2 = unit_names2[found_var]
            
            # compute day, month, year for every entry
            datear = array([ref + datetime.timedelta(int(t)) for t in time])
            days   = array([d.timetuple().tm_yday for d in datear]).reshape((nt, 1)) # convert to numpy array
            months = array([d.month for d in datear])
            years  = array([d.year  for d in datear]).reshape((nt, 1))
            
            # compute tav
            tmin, tmax = alldata[tmin_idx], alldata[tmax_idx]
            tav = 0.5 * (tmin.sum(axis = 1) + tmax.sum(axis = 1)) / nt # function of scen
            
            # compute amp
            monmax, monmin = -inf * ones(ns), inf * ones(ns)
            for i in range(1, 13):
                ismonth = months == i
                if ismonth.sum():
                    t = 0.5 * (tmin[:, ismonth].sum(axis = 1) + tmax[:, ismonth].sum(axis = 1)) / ismonth.sum()
                    monmax[t > monmax] = t[t > monmax]
                    monmin[t < monmin] = t[t < monmin]
            amp = monmax - monmin
            
            # add co2 if available
            if not co2file is None:
                cobj = CO2(co2file)
                co2  = cobj.selYears(years[0], years[-1])
                var_names   = append(var_names, 'co2')
                unit_names2 = append(unit_names2, 'ppm')
                alldata     = concatenate((alldata, resize(co2, (1, ns, nt))))
                nv         += 1
            
            # write files
            filenames = [outputfile] if ns == 1 else ['met' + str(i).zfill(5) + '.met' for i in range(ns)]
            for i in range(ns):
                # write header
                head = '[weather.met.weather]\nstationname = Generic\n'
                head += 'latitude = ' + str(lat) + ' (DECIMALDEGREES)\n'
                head += 'longitude = ' + str(lon) + ' (DECIMALDEGREES)\n'
                head += 'tav = ' + str(tav[i]) + ' (oC)\n'
                head += 'amp = ' + str(amp[i]) + ' (oC)\n\n'
                head += 'year   day   ' + '   '.join(var_names) + '\n'
                head += '()     ()    ' + '   '.join(['({:s})'.format(s) for s in unit_names2]) + '\n'
            
                # write body
                with open(filenames[i], 'w') as f:
                    f.write(head)
                    savetxt(f, concatenate((years, days, alldata[:, i].T), axis = 1), fmt = ['%d', '%d'] + ['%.3f'] * nv, delimiter = '   ')
            
                # change permissions
                f = os.open(filenames[i], os.O_RDONLY)
                os.fchmod(f, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
                os.close(f)
            
            # delete temporary file if necessary
            if istmp:
                os.remove(inputfile)
            return True
        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

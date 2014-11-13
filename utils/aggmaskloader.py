from numpy import zeros, ones
from netCDF4 import Dataset as nc
from numpy.ma import masked_array, unique, logical_and

class AggMaskLoader(object):
    def __init__(self, filename, varnames = None, lats = None, lons = None, incl_global = False):
        f = nc(filename) # open file

        if varnames is None: # no variables specified
            varnames = f.variables.keys()
            varnames = [v for v in varnames if not v in ['lat', 'lon']] # remove lat, lon
            if incl_global: varnames += ['global']
        else:
            if not isinstance(varnames, list): # make list
                varnames = [varnames]

        self.lats, self.lons = f.variables['lat'][:], f.variables['lon'][:]

        self.dat = {'names': [], 'units': [], 'longnames': [], 'data': []}

        for v in varnames:
            if v != 'global':
                var = f.variables[v]
                self.dat['names'].append(v)
                self.dat['units'].append(var.units if 'units' in var.ncattrs() else '')
                self.dat['longnames'].append(var.long_name if 'long_name' in var.ncattrs() else '')
                self.dat['data'].append(var[:])
            else:
                nlats = self.lats.size
                nlons = self.lons.size

                self.dat['names'].append('global') # global mask
                self.dat['units'].append('')
                self.dat['longnames'].append('')
                self.dat['data'].append(masked_array(ones((nlats, nlons)), mask = zeros((nlats, nlons))))

        f.close()

        tol = 1e-5
        if not lats is None: # restrict latitude range
            sellat = logical_and(self.lats >= lats.min() - tol, self.lats <= lats.max() + tol)
            self.lats = self.lats[sellat]
            for i in range(len(self.dat['names'])):
                self.dat['data'][i] = self.dat['data'][i][sellat]
        if not lons is None: # restrict longitude range
            sellon = logical_and(self.lons >= lons.min() - tol, self.lons <= lons.max() + tol)
            self.lons = self.lons[sellon]
            for i in range(len(self.dat['names'])):
                self.dat['data'][i] = self.dat['data'][i][:, sellon]

    def names(self):      return self.dat['names']
    
    def units(self):      return self.dat['units']
    
    def longnames(self):  return self.dat['longnames']
    
    def data(self):       return self.dat['data']

    def latitudes(self):  return self.lats

    def longitudes(self): return self.lons

    def udata(self):
        ud = []
        for i in range(len(self.dat['names'])):
            udi = unique(self.dat['data'][i])
            udi = udi[~udi.mask] # remove fill value from list
            ud.append(udi)
        return ud
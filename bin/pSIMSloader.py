from re import compile
from calendar import monthrange
from netCDF4 import Dataset as nc
from datetime import datetime, timedelta
from numpy.ma import masked_where, where
from numpy import zeros, resize, reshape, array, setdiff1d

# common function
def foundvar(variables, variants):
    for i in range(len(variables)):
        for j in range(len(variants)):
            patt = '%s$|%s.*' % (variants[j], variants[j])
            if bool(compile(patt).match(variables[i])):
                return i # return idx
    raise Exception('Variable not found')

class DailyData(object):
    prnames = ['precip', 'pr', 'rain', 'prcp']
    manames = ['tmax', 'tasmax']
    minames = ['tmin', 'tasmin']

    def __init__(self, file, vars = None):
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables, ['latitude', 'longitude', 'time'])

            self.lat, self.lon = f.variables['latitude'][0], f.variables['longitude'][0]

            self.time = f.variables['time'][:]

            tunits = f.variables['time'].units
            ts = tunits.split('days since ')[1].split(' ')
            yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
            if len(ts) > 1:
                hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
            else:
                hr0 = min0 = sec0 = 0
            self.reftime = datetime(yr0, mth0, day0, hr0, min0, sec0)

            nv, nt = len(vars), len(self.time)
            self.data      = zeros((nv, nt))
            self.units     = zeros(nv, dtype = '|S64')
            self.longnames = zeros(nv, dtype = '|S64')
            for i in range(nv):
                var = f.variables[vars[i]]
                self.data[i] = var[:, 0, 0]
                self.units[i] = var.units
                self.longnames[i] = var.long_name

            self.vars = vars # store variable names

            self.pridx = foundvar(vars, self.prnames) # variable indices
            self.maidx = foundvar(vars, self.manames)
            self.miidx = foundvar(vars, self.minames)

    def startYear(self):
        return (self.reftime + timedelta(int(self.time[0]))).year

    def endYear(self):
        return (self.reftime + timedelta(int(self.time[-1]))).year

    def selYears(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        idx0 = self.__getTimeIdx(datetime(syear, 1, 1))
        idx1 = self.__getTimeIdx(datetime(eyear, 12, 31))
        return self.data[:, idx0 : idx1 + 1]

    def selMonths(self, year, smon = None, emon = None):
        if smon is None and emon is None:
            smon, emon = 1, 12 # all months
        elif emon is None:
            emon = smon # one month
        t0 = datetime(year, smon, 1)
        t1 = datetime(year, emon, monthrange(year, emon)[1])
        idx0 = self.__getTimeIdx(t0)
        idx1 = self.__getTimeIdx(t1)
        return self.data[:, idx0 : idx1 + 1]

    def average(self):
        syear, eyear = self.startYear(), self.endYear()
        nyers = eyear - syear + 1
        ave = zeros((len(self.data), nyers, 12))
        idx = 0
        for i in range(nyers):
            for j in range(12):
                ndays = monthrange(syear + i, j + 1)[1]
                ave[:, i, j] = self.data[:, idx : idx + ndays].mean(axis = 1)
                idx += ndays
        return ave

    def __getTimeIdx(self, date):
        return where(self.time == (date - self.reftime).days)[0][0]   

class MonthlyData(object):
    prnames = ['precip', 'pr', 'rain', 'prcp']
    manames = ['tmax', 'tasmax']
    minames = ['tmin', 'tasmin']

    convArr = array([[['wm-2', 'w/m^2', 'w/m2'], ['mj/m^2', 'mj/m2', 'mjm-2', 'mjm-2day-1', 'mjm-2d-1', 'mj/m^2/day', 'mj/m2/day'], 'm', 0.0864], \
                     [['k', 'degrees(k)', 'deg(k)'], ['oc', 'degc', 'c'], 'a', -273.15], \
                     [['kgm-2s-1', 'kg/m^2/s', 'kg/m2/s'], ['mm', 'mm/day'], 'm', 86400.], \
                     [['ms-1', 'm/s'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 86.4], \
                     [['kmh-1', 'km/h', 'kmhr-1', 'km/hr'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 24.], \
                     [['milesh-1', 'miles/h', 'mileshr-1', 'miles/hr'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 38.624256], \
                     [['pa'], ['mb'], 'm', 1 / 100.], \
                     [['gkg-1'], ['kgkg-1', 'kg/kg'], 'm', 1 / 1000.], \
                     [['', '0-1'], ['%'], 'm', 100.]])

    def __init__(self, file, lat, lon, vars = None):
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables, ['lat', 'lon', 'time'])

            lats, lons = f.variables['lat'][:], f.variables['lon'][:]

            mask = f.variables[vars[0]][0].mask # pull mask from first variable, first time

            latd = resize(lats, (len(lons), len(lats))).T - lat
            lond = resize(lons, (len(lats), len(lons))) - lon
            latd = masked_where(mask, latd)
            lond = masked_where(mask, lond)
            totd = latd ** 2 + lond ** 2
            idx = where(totd == totd.min())
            latidx, lonidx = idx[0][0], idx[1][0]

            self.time = f.variables['time'][:]

            tunits = f.variables['time'].units
            ts = tunits.split('months since ')[1].split(' ')
            yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
            if len(ts) > 1:
                hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
            else:
                hr0 = min0 = sec0 = 0
            self.reftime = datetime(yr0, mth0, day0, hr0, min0, sec0)

            nv, nt = len(vars), len(self.time)
            self.data  = zeros((nv, nt))
            self.units = zeros(nv, dtype = '|S32')
            for i in range(nv):
                self.data[i]  = f.variables[vars[i]][:, latidx, lonidx]
                self.units[i] = f.variables[vars[i]].units

            self.vars = vars # store variable names

            self.pridx = foundvar(vars, self.prnames) # variable indices
            self.maidx = foundvar(vars, self.manames)
            self.miidx = foundvar(vars, self.minames)

    def startYear(self):
        return self.reftime.year + int(self.time[0]) / 12

    def endYear(self):
        return self.reftime.year + int(self.time[-1]) / 12

    def selYears(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        ny = eyear - syear + 1
        t0 = datetime(syear, 1, 1)
        t1 = datetime(eyear, 12, 31)
        d0 = self.__diffMonths(t0, self.reftime)
        d1 = self.__diffMonths(t1, self.reftime)
        return reshape(self.data[:, d0 : d1 + 1], (len(self.data), ny, 12))

    def convertUnits(self, units):
        for i in range(len(self.units)):
            fromunits = self.units[i].lower().replace(' ', '')
            tounits   = units[i].lower().replace(' ', '')

            isconv = False
            for j in range(len(self.convArr)):
                u1, u2, op, num = self.convArr[j]
                if fromunits in u1 and tounits in u2:
                    self.data[i] = self.__convert(self.data[i], op, num)
                    isconv = True
                    break
                elif fromunits in u2 and tounits in u1: # reverse conversion
                    if op == 'a':
                        num = -num
                    elif op == 'm':
                        num = 1. / num
                    self.data[i] = self.__convert(self.data[i], op, num)
                    isconv = True
                    break
                elif (fromunits in u1 and tounits in u1) or (fromunits in u2 and tounits in u2): # same units
                    isconv = True
                    break

            if not isconv:
                raise Exception('Unknown unit conversion: %s -> %s' % (fromunits, tounits))

    def __diffMonths(self, date1, date2):
        return (date1.year - date2.year) * 12 + date1.month - date2.month

    def __convert(self, dat, op, num):
        if op == 'm':
            return dat * num
        elif op == 'a':
            return dat + num
        else:
            raise Exception('Unknown operator')
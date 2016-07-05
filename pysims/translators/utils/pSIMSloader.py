from re import compile
from itertools import product
from calendar import monthrange
from netCDF4 import Dataset as nc
from datetime import datetime, timedelta
from numpy.ma import masked_where, where, masked_array, isMaskedArray
from numpy import zeros, ones, resize, reshape, array, setdiff1d, unique, roll, interp, arange

# COMMON FUNCTIONS
def foundVar(variables, var):
    varnames = {'pr':   ['pr', 'precip', 'rain', 'prcp'], \
                'tmax': ['tmax', 'tasmax'], \
                'tmin': ['tmin', 'tasmin'], \
                'rsds': ['rsds', 'srad', 'rad', 'dswsfc'], \
                'wind': ['wind', 'wnd', 'wnd10m', 'windspeed'], \
                'hus':  ['hus'], \
                'ps':   ['ps']}

    idxs = []
    for v, variants in varnames.iteritems():
        if var in variants:
            for i in range(len(variables)):
                for j in range(len(variants)):
                    patt = '%s$|%s.*' % (variants[j], variants[j])
                    if compile(patt).match(variables[i]):
                        idxs.append(i)
                        break

    return idxs

def foundVarSingle(variables, var):
    idx = foundVar(variables, var)

    if len(idx):
        return idx[0]
    else:
        return None

def getTimeIdx(date, time, reftime):
    idx = where(time == (date - reftime).days)[0]
    return idx[0] if idx.size else len(time) - 1

def convertUnits(data, fromunits, tounits):
    def convert(dat, op, num):
        if op == 'm':
            return dat * num
        elif op == 'a':
            return dat + num
        else:
            raise Exception('Unknown operator')

    convArr = array([[['wm-2', 'w/m^2', 'w/m2', 'wm**-2'], ['mj/m^2', 'mj/m2', 'mjm-2', 'mjm-2day-1', 'mjm-2d-1', 'mj/m^2/day', 'mj/m2/day'], 'm', 0.0864], \
                     [['k', 'degrees(k)', 'deg(k)'], ['oc', 'degc', 'degreesc', 'c'], 'a', -273.15], \
                     [['kgm-2s-1', 'kg/m^2/s', 'kg/m2/s', 'kgm**-2s**-1'], ['mm', 'mm/day'], 'm', 86400.], \
                     [['ms-1', 'm/s', 'ms**-1'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 86.4], \
                     [['kmh-1', 'km/h', 'kmhr-1', 'km/hr'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 24.], \
                     [['milesh-1', 'miles/h', 'mileshr-1', 'miles/hr'], ['kmday-1', 'km/day', 'kmdy-1', 'km/dy'], 'm', 38.624256], \
                     [['pa'], ['mb'], 'm', 1 / 100.], \
                     [['gkg-1'], ['kgkg-1', 'kg/kg'], 'm', 1 / 1000.], \
                     [['', '0-1'], ['%'], 'm', 100.], \
                     [['kgkg**-1'], ['kg/kg'], 'm', 1.]])

    cdata = data.copy()
    for i in range(len(fromunits)):
        if fromunits[i] == '': # do not try to convert NULL data
            continue

        funits = fromunits[i].lower().replace(' ', '')
        tunits = tounits[i].lower().replace(' ', '')

        isconv = False
        for j in range(len(convArr)):
            u1, u2, op, num = convArr[j]
            if funits in u1 and tunits in u2:
                cdata[i] = convert(cdata[i], op, num)
                isconv = True
                break
            elif funits in u2 and tunits in u1: # reverse conversion
                if op == 'a':
                    num = -num
                elif op == 'm':
                    num = 1. / num
                cdata[i] = convert(cdata[i], op, num)
                isconv = True
                break
            elif (funits in u1 and tunits in u1) or (funits in u2 and tunits in u2): # same units
                isconv = True
                break

        if not isconv:
            raise Exception('Unknown unit conversion: %s -> %s' % (funits, tunits))

    return cdata
               
class DailyData(object):
    def __init__(self, file, vars = None):
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables.keys(), ['latitude', 'longitude', 'lat', 'lon', 'time', 'cropland']) # don't load cropland as well

            if 'lat' in f.variables:
                latname, lonname = 'lat', 'lon'
            else:
                latname, lonname = 'latitude', 'longitude'

            self.lat, self.lon = f.variables[latname][0], f.variables[lonname][0]

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
            self.data      = masked_array(zeros((nv, nt)), mask = ones((nv, nt)))
            self.units     = zeros(nv, dtype = '|S64')
            self.longnames = zeros(nv, dtype = '|S64')
            for i in range(nv):
                if vars[i] in f.variables:
                    var = f.variables[vars[i]]
                    self.data[i] = var[:, 0, 0]
                    self.units[i] = var.units
                    self.longnames[i] = var.long_name
                else:
                    vidx = foundVarSingle(f.variables.keys(), vars[i])
                    if vidx:
                        var = f.variables[f.variables.keys()[vidx]]
                        self.data[i] = var[:, 0, 0]
                        self.units[i] = var.units
                        self.longnames[i] = var.long_name

            self.vars = vars # store variable names

            self.pridx = foundVarSingle(vars, 'pr') # variable indices
            self.maidx = foundVarSingle(vars, 'tmax')
            self.miidx = foundVarSingle(vars, 'tmin')

    def startYear(self):
        return (self.reftime + timedelta(int(self.time[0]))).year

    def endYear(self):
        return (self.reftime + timedelta(int(self.time[-1]))).year

    def selYears(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        idx0 = getTimeIdx(datetime(syear, 1, 1),   self.time, self.reftime)
        idx1 = getTimeIdx(datetime(eyear, 12, 31), self.time, self.reftime)
        return self.data[:, idx0 : idx1 + 1]

    def selMonths(self, year, smon = None, emon = None):
        if smon is None and emon is None:
            smon, emon = 1, 12 # all months
        elif emon is None:
            emon = smon # one month
        t0 = datetime(year, smon, 1)
        t1 = datetime(year, emon, monthrange(year, emon)[1])
        idx0 = getTimeIdx(t0, self.time, self.reftime)
        idx1 = getTimeIdx(t1, self.time, self.reftime)
        return self.data[:, idx0 : idx1 + 1]

    def selDays(self, years, smon, sday, ndays = 1):
        sh = (len(self.data), len(years), ndays)
        ddata = masked_array(zeros(sh), mask = ones(sh))
        ldate = datetime(self.endYear(), 12, 31)
        for i in range(len(years)):
            t0 = datetime(years[i], smon, sday)
            t1 = t0 + timedelta(min((ldate - t0).days, ndays - 1))
            idx0 = getTimeIdx(t0, self.time, self.reftime)
            idx1 = getTimeIdx(t1, self.time, self.reftime)
            ddata[:, i, : idx1 - idx0 + 1] = self.data[:, idx0 : idx1 + 1]
        return ddata

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

    def convertUnits(self, units):
        self.data = convertUnits(self.data, self.units, units)
        return

class MonthlyData(object):
    def __init__(self, file, lat, lon, vars = None):
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables.keys(), ['lat', 'lon', 'time'])

            lats, lons = f.variables['lat'][:], f.variables['lon'][:]

            if isMaskedArray(f.variables[vars[0]][0]):
                mask = f.variables[vars[0]][0].mask # pull mask from first variable, first time
            else:
                mask = zeros((len(lats), len(lons)))

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
                if vars[i] in f.variables:
                    var = f.variables[vars[i]]
                else:
                    vidx = foundVarSingle(f.variables.keys(), vars[i])
                    var  = f.variables[f.variables.keys()[vidx]]
                self.data[i]  = var[:, latidx, lonidx]
                self.units[i] = var.units

            self.vars = vars # store variable names

            self.pridx = foundVarSingle(vars, 'pr') # variable indices
            self.maidx = foundVarSingle(vars, 'tmax')
            self.miidx = foundVarSingle(vars, 'tmin')

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
        self.data = convertUnits(self.data, self.units, units)
        return

    def __diffMonths(self, date1, date2):
        return (date1.year - date2.year) * 12 + date1.month - date2.month

class CFSData(object):
    def __init__(self, file, vars = None, dates = None): # dates is array of dates to pull
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables.keys(), ['latitude', 'longitude', 'lat', 'lon', 'time', 'ftime', 'scen', 'cropland'])
                newvars = list(vars.copy())
                for v in vars:
                    if compile('missing_*').match(v): # remove missing_* variables
                        newvars.remove(v)
                vars = array(newvars)

            if 'lat' in f.variables:
                latname, lonname = 'lat', 'lon'
            else:
                latname, lonname = 'latitude', 'longitude'

            self.lat, self.lon = f.variables[latname][0], f.variables[lonname][0]

            self.scen  = f.variables['scen'][:]
            self.time  = f.variables['time'][:]
            self.ftime = f.variables['ftime'][:]            

            tunits = f.variables['time'].units
            ts = tunits.split('days since ')[1].split(' ')
            yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
            if len(ts) > 1:
                hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
            else:
                hr0 = min0 = sec0 = 0
            self.reftime = datetime(yr0, mth0, day0, hr0, min0, sec0)

            if dates:
                # indices to specified dates
                tidxs = [0] * len(dates)
                time = zeros(len(dates))
                for i in range(len(dates)):
                    ndays = (dates[i] - self.reftime).days
                    if ndays in self.time:
                        tidxs[i] = where(self.time == ndays)[0][0]
                    else:
                        raise Exception('Cannot find date %s in times' % dates[i])
                    time[i] = ndays
                self.time = time

            nv, ns, nt, nf = len(vars), len(self.scen), len(self.time), len(self.ftime)
            self.data      = masked_array(zeros((nv, ns, nt, nf)), mask = ones((nv, ns, nt, nf)))
            self.missing   = zeros((nv, ns, nt))
            self.units     = zeros(nv, dtype = '|S64')
            self.longnames = zeros(nv, dtype = '|S64')
            for i in range(nv):
                if vars[i] in f.variables:
                    var = f.variables[vars[i]]
                    msg = f.variables['missing_' + vars[i]]
                else:
                    vidx = foundVarSingle(f.variables.keys(), vars[i])
                    var  = f.variables[f.variables.keys()[vidx]]
                    msg  = f.variables['missing_' + f.variables.keys()[vidx]]
                if dates:
                    self.data[i] = var[tidxs, :, :, 0, 0].transpose((2, 0, 1)) # (time, ftime, scen)
                    self.missing[i] = msg[tidxs].transpose((1, 0)) # (time, scen)
                else:
                    self.data[i] = var[:, :, :, 0, 0].transpose((2, 0, 1))
                    self.missing[i] = msg[:].transpose((1, 0))
                self.units[i] = var.units
                self.longnames[i] = var.long_name

            self.vars = vars # store variable names

            self.pridx = foundVarSingle(vars, 'pr') # variable indices
            self.maidx = foundVarSingle(vars, 'tmax')
            self.miidx = foundVarSingle(vars, 'tmin')

        self.__fillMissing()
        self.__fillMissingScenarios()

    def startYear(self):
        return (self.reftime + timedelta(int(self.time[0]))).year

    def endYear(self):
        return (self.reftime + timedelta(int(self.time[-1]))).year

    def getDays(self):
        jday = array([int((self.reftime + timedelta(int(t))).strftime('%m%d')) for t in self.time])
        return unique(jday)

    def selDaily(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        nv, ns, nt, nf = self.data.shape
        nd = len(self.getDays())
        ny = nt / nd
        data = reshape(self.data, (nv, ns, ny, nd, nf))
        return data[:, :, syear - self.startYear() : eyear - self.startYear() + 1, :, : 31]

    def selWeekly(self, syear = None, eyear = None):
        daily = self.selDaily(syear, eyear)
        nv, ns, ny, nd, _ = daily.shape
        weekly = masked_array(zeros((nv, ns, ny, nd, 6)), mask = ones((nv, ns, ny, nd, 6)))
        for i in range(6): # 5-day means
            weekly[:, :, :, :, i] = daily[:, :, :, :, 5 * i + 1 : 5 * (i + 1) + 1].mean(axis = 4)
        return weekly

    def selMonthly(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        nv, ns, nt, nf = self.data.shape
        nd = len(self.getDays())
        ny = nt / nd
        data = reshape(self.data, (nv, ns, ny, nd, nf))
        return data[:, :, syear - self.startYear() : eyear - self.startYear() + 1, :, 31 :]

    def convertUnits(self, units):
        self.data = convertUnits(self.data, self.units, units)
        return

    def __fillMissing(self):
        nv, ns, nt, nf = self.data.shape

        for i in range(nv):
            for j in range(ns):
                for k in range(nt):
                    d = self.data[i, j, k]
                    if d.mask.any() and ~d.mask.all():
                        if i == self.pridx:
                            d[d.mask] = 0
                            self.data[i, j, k] = d
                        else:
                            x = arange(nf)
                            self.data[i, j, k] = interp(x, x[~d.mask], d[~d.mask])

    def __fillMissingScenarios(self):
        nv, _, nt, _ = self.data.shape

        for i in range(nv):
            for j in range(nt):
                badscens  = where(self.data[i, :, j].mask.all(axis = 1))[0]
                goodscens = where(~self.data[i, :, j].mask.all(axis = 1))[0]

                if goodscens.size:
                    for k in range(len(badscens)):
                        idx = where(goodscens <= badscens[k])[0]
                        idx = idx[-1] if idx.size else 0
                        self.data[i, :, j, badscens[k]] = self.data[i, :, j, goodscens[idx]]

    # OLD VERSION OF FILLER
    # def __fillMissing(self):
    #     scens = range(self.missing.shape[1])
    #     scens = roll(scens, len(scens) - 1) # make 00 last
    #     vidx, sidx, tidx = where(self.missing)
    #     for i in range(len(vidx)):
    #         v, s, t = vidx[i], sidx[i], tidx[i]
    #         filled = False
    #         for tnew, snew in product([t, max(t - 1, 0), max(t - 2, 0)], scens):
    #             if not self.missing[v, snew, tnew]:
    #                 self.data[v, s, t] = self.data[v, snew, tnew]
    #                 filled = True
    #                 break
    #         if not filled:
    #             raise Exception('Failed to fill')

class CFS2Data(object):
    def __init__(self, file, vars = None, dates = None): # dates is array of dates to pull
        with nc(file) as f:
            if vars is None:
                vars = setdiff1d(f.variables.keys(), ['latitude', 'longitude', 'lat', 'lon', 'time', 'fday', 'fmonth', 'scen', 'cropland'])

            if 'lat' in f.variables:
                latname, lonname = 'lat', 'lon'
            else:
                latname, lonname = 'latitude', 'longitude'

            self.lat, self.lon = f.variables[latname][0], f.variables[lonname][0]

            self.scen = f.variables['scen'][:]
            self.time = f.variables['time'][:]
            self.fday = f.variables['fday'][:]

            tunits = f.variables['time'].units
            ts = tunits.split('days since ')[1].split(' ')
            yr0, mth0, day0 = [int(t) for t in ts[0].split('-')[0 : 3]]
            if len(ts) > 1:
                hr0, min0, sec0 = [int(t) for t in ts[1].split(':')[0 : 3]]
            else:
                hr0 = min0 = sec0 = 0
            self.reftime = datetime(yr0, mth0, day0, hr0, min0, sec0)

            if dates:
                # indices to specified dates
                tidxs = [0] * len(dates)
                time = zeros(len(dates))
                for i in range(len(dates)):
                    ndays = (dates[i] - self.reftime).days
                    if ndays in self.time:
                        tidxs[i] = where(self.time == ndays)[0][0]
                    else:
                        raise Exception('Cannot find date %s in times' % dates[i])
                    time[i] = ndays
                self.time = time

            nv, ns, nt, nf = len(vars), len(self.scen), len(self.time), len(self.fday)
            self.data      = masked_array(zeros((nv, nt, ns, nf)), mask = ones((nv, nt, ns, nf)))
            self.units     = zeros(nv, dtype = '|S64')
            self.longnames = zeros(nv, dtype = '|S64')
            for i in range(nv):
                if vars[i] in f.variables:
                    var = f.variables[vars[i]]
                    if dates:
                        self.data[i] = var[tidxs, :, :, 0, 0] # select dates
                    else:
                        self.data[i] = var[:, :, :, 0, 0]
                    self.units[i] = var.units
                    self.longnames[i] = var.long_name
                else:
                    vidx = foundVarSingle(f.variables.keys(), vars[i])
                    if vidx:
                        var = f.variables[f.variables.keys()[vidx]]
                        if dates:
                            self.data[i] = var[tidxs, :, :, 0, 0]
                        else:
                            self.data[i] = var[:, :, :, 0, 0]
                        self.units[i] = var.units
                        self.longnames[i] = var.long_name

            self.vars = vars # store variable names

            self.pridx = foundVarSingle(vars, 'pr') # variable indices
            self.maidx = foundVarSingle(vars, 'tmax')
            self.miidx = foundVarSingle(vars, 'tmin')

        self.__fillMissing()
        self.__fillMissingScenarios()

    def convertUnits(self, units):
        self.data = convertUnits(self.data, self.units, units)
        return

    def __fillMissing(self):
        nv, nt, ns, nf = self.data.shape

        for i in range(nv):
            for j in range(nt):
                for k in range(ns):
                    d = self.data[i, j, k]
                    if d.mask.any() and ~d.mask.all():
                        if i == self.pridx:
                            d[d.mask] = 0
                            self.data[i, j, k] = d
                        else:
                            x = arange(nf)
                            self.data[i, j, k] = interp(x, x[~d.mask], d[~d.mask])

    def __fillMissingScenarios(self):
        nv, nt, _, _ = self.data.shape

        for i in range(nv):
            for j in range(nt):
                badscens  = where(self.data[i, j].mask.all(axis = 1))[0]
                goodscens = where(~self.data[i, j].mask.all(axis = 1))[0]

                if goodscens.size:
                    for k in range(len(badscens)):
                        idx = where(goodscens <= badscens[k])[0]
                        idx = idx[-1] if idx.size else 0
                        self.data[i, j, badscens[k]] = self.data[i, j, goodscens[idx]]

class CFSHPRData(CFSData):
    def __init__(self, file, vars = None, dates = None):
        super(CFSHPRData, self).__init__(file, vars = vars, dates = dates)

    def selYears(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.startYear(), self.endYear() # all years
        elif eyear is None:
            eyear = syear # one year
        idx0 = getTimeIdx(datetime(syear, 1, 1),   self.time, self.reftime)
        idx1 = getTimeIdx(datetime(eyear, 12, 31), self.time, self.reftime)
        return self.data[:, :, idx0 : idx1 + 1, :]
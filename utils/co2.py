from csv import reader
from calendar import monthrange, isleap
from datetime import datetime, timedelta
from numpy import double, zeros, array, logical_and

class CO2(object):
    def __init__(self, file):
        data = []
        with open(file) as f:
            for row in reader(f):
                data.append(row)

        years = [int(d[0])    for d in data[2 :]]
        co2   = [double(d[2]) for d in data[2 :]]

        self.yr0, self.yr1 = years[0], years[-1]

        nyers  = self.yr1 - self.yr0 + 1
        ndays  = (datetime(self.yr1 + 1, 1, 1) - datetime(self.yr0, 1, 1)).days
        ntimes = len(data[2 :])

        self.co2 = zeros(ndays)
        if ntimes == nyers * 12: # monthly data
            cnt = day = 0
            for i in range(nyers):
                for j in range(12):
                    nm = monthrange(i + self.yr0, j + 1)[1]
                    self.co2[day : day + nm] = co2[cnt]
                    cnt += 1
                    day += nm
        elif ntimes == nyers: # yearly data
            day = 0
            for i in range(nyers):
                ny = 365 + isleap(i + self.yr0)
                self.co2[day : day + ny] = co2[i]
                day += ny
        else:
            raise Exception('Unsupported number of times')

    def selYears(self, syear = None, eyear = None):
        if syear is None and eyear is None:
            syear, eyear = self.yr0, self.yr1 # all years
        elif eyear is None:
            eyear = syear # one year
        years = array([(datetime(self.yr0, 1, 1) + timedelta(t)).year for t in range(len(self.co2))])
        return self.co2[logical_and(years >= syear, years <= eyear)]
import abc, numpy.ma as ma
from numpy import zeros, ones, where, resize, cos, pi, logical_not, logical_and

class Averager(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def av(self, var, agg, lats, weights = None, calcarea = True): return

    def combine(self, var1, var2, agg, lats, weights1 = None, weights2 = None, calcarea = True, mask1 = None, mask2 = None, numchunks = 1):
        nt, nlats, nlons = var1.shape
        if weights1 is None: weights1 = ones((nlats, nlons)) # weights
        if weights2 is None: weights2 = ones((nlats, nlons))
        if calcarea: # area
            area = self.area(lats, nlats, nlons)
        else:
            area = ones((nlats, nlons))
        av1 = self.av(var1, agg, lats, weights = weights1, calcarea = calcarea, mask = mask1, numchunks = numchunks)
        av2 = self.av(var2, agg, lats, weights = weights2, calcarea = calcarea, mask = mask2, numchunks = numchunks)
        area1 = self.areas(var1, agg, area, weights1, mask = mask1)
        area2 = self.areas(var2, agg, area, weights2, mask = mask2)
        sz = len(av1)
        totarea = area1 + area2
        totarea = ma.masked_where(totarea == 0, totarea)
        totav = ma.masked_array(zeros((sz, nt, 3)), mask = ones((sz, nt, 3)))
        totav[:, :, 0], totav[:, :, 1] = av1, av2
        totav[:, :, 2] = (area1 * av1 + area2 * av2) / totarea
        return totav

    def sum(self, var, agg, area, weights, mask = None, numchunks = 1):
        nt, nlats, nlons = var.shape

        aggvals = self.__uniquevals(agg)
        sz = len(aggvals)

        if mask is None:
            varmask = ones((nt, nlats, nlons)) # no additional mask
        else:
            varmask = mask

        chunksize = sz / numchunks # chunk data to reduce memory usage

        sumv = ma.masked_array(zeros((sz, nt)), mask = ones((sz, nt)))
        
        maxchunksize = max(chunksize, chunksize + sz - chunksize * numchunks)
        
        aselect = ma.zeros((maxchunksize, nlats, nlons), dtype = bool) # preallocate
        vartmp = zeros((maxchunksize, nlats, nlons))
        
        cnt = 0
        for i in range(numchunks):
            startidx = cnt
            if i != numchunks - 1:
                endidx = cnt + chunksize
            else:
                endidx = sz

            aggvalsc = aggvals[startidx : endidx] # work on subset of aggregation values
            szc = len(aggvalsc)

            aselect[:] = 0 # clear
            for j in range(szc): aselect[j] = (agg == aggvalsc[j])
            ridx, latidx, lonidx = where(aselect)
        
            vartmp[:] = 0 # clear
            for t in range(nt):
                vartmp[ridx, latidx, lonidx] = var[t, latidx, lonidx]     * \
                                               varmask[t, latidx, lonidx] * \
                                               weights[latidx, lonidx]    * \
                                               area[latidx, lonidx]       * \
                                               aselect[ridx, latidx, lonidx]
                sumv[startidx : endidx, t] = vartmp.sum(axis = 2).sum(axis = 1)[: szc]

            cnt += chunksize

        return sumv

    def areas(self, var, agg, area, weights, mask = None):
        aggvals = self.__uniquevals(agg)
        varmask = logical_not(var.mask) # use variable mask
        if not mask is None: varmask = logical_and(varmask, mask) # additional mask
        areas = zeros((len(aggvals), len(var)))
        for i in range(len(aggvals)):
            warea = weights * area * (agg == aggvals[i])
            latidx, lonidx = where(warea)
            areas[i] = (warea[latidx, lonidx] * varmask[:, latidx, lonidx]).sum(axis = 1)
        areas = ma.masked_where(areas == 0, areas)
        return areas

    def area(self, lats, nlats, nlons):
        A = 100 * (111.2 / 2) ** 2 * cos(pi * lats / 360)
        A = resize(A, (nlons, nlats)).T
        return A

    def __uniquevals(self, d):
        u = ma.unique(d)
        u = u[~u.mask]
        return u

class SumAverager(Averager):    
    def av(self, var, agg, lats, weights = None, calcarea = True, mask = None, numchunks = 1):
        _, nlats, nlons = var.shape
        if weights is None: weights = ones((nlats, nlons)) # weights
        if calcarea: # area
            area = self.area(lats, nlats, nlons)
        else:
            area = ones((nlats, nlons))
        avv = self.sum(var, agg, area, weights, mask = mask, numchunks = numchunks)
        return avv

class MeanAverager(Averager):
    def av(self, var, agg, lats, weights = None, calcarea = True, mask = None, numchunks = 1):
        nt, nlats, nlons = var.shape
        if weights is None: weights = ones((nlats, nlons)) # weights
        if calcarea: # area
            area = self.area(lats, nlats, nlons)
        else:
            area = ones((nlats, nlons))
        avv = self.sum(var, agg, area, weights, mask = mask, numchunks = numchunks)
        areas = self.areas(var, agg, area, weights, mask = mask)
        return avv / areas
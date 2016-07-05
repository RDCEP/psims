import os
import traceback
from nco import Nco
from os import remove
from .. import checker
from re import compile
from netCDF4 import Dataset as nc
from numpy.ma import isMaskedArray
from numpy import double, array, diff

def apply_prefix(filename, prefix):
    return os.path.join(prefix, filename)

class SimpleChecker(checker.Checker):

    def verify_params(self, latidx, lonidx):
        tname = type(self).__name__
        simgfile = self.config.get_dict(self.checker_type, 'simgfile', default = '../../simgrid.nc4')
        if not os.path.exists(simgfile):
            return (False, "%s checker simgfile %s does not exist!" % (tname, simgfile))
        try:
            simg_nc4 = nc(simgfile, 'r')
            if 'mask' not in simg_nc4.variables:
                return (False, "%s checker simgfile %s does not contain mask variable!" % (tname, simgfile))
        except:
            return (False, "%s checker error opening %s as a NetCDF file" % (tname, simgfile))
        return (True, "%s checker likes the parameters" % tname)

    def run(self, latidx, lonidx):
        try:
            inputfile_dir      = self.config.get_dict(self.checker_type, 'inputfile_dir', default = os.path.join('..', '..'))
            climfiles          = self.config.get_dict(self.checker_type, 'climfile', default = '1.clim.tile.nc4')
            soilfiles          = self.config.get_dict(self.checker_type, 'soilfile', default = '1.soil.tile.nc4')
            simgfile           = self.config.get_dict(self.checker_type, 'simgfile', default = 'simgrid.nc4')
            latdelta, londelta = [double(d) / 60 for d in self.config.get('delta').split(',')] # convert to degrees

            if not isinstance(climfiles, list):
                climfiles = [climfiles]
            if not isinstance(soilfiles, list):
                soilfiles = [soilfiles]

            # get sim grid deltas
            with nc(simgfile) as f:
                lats, lons = f.variables['lat'][:], f.variables['lon'][:]
                simglatdelta, simglondelta = abs(diff(lats)[0]), abs(diff(lons)[0])
            minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, simglatdelta, simglondelta)

            # check simgrid file
            nco = Nco()
            options = '-h -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
            nco.ncks(input = simgfile, output = 'tmp.nc4', options = options)

            with nc('tmp.nc4') as f:
                notmasked = f.variables['mask'][:].any()
            remove('tmp.nc4')

            if not notmasked:
                return False

            # check weather file(s)
            for i in range(len(climfiles)):
                climfile = apply_prefix(climfiles[i], inputfile_dir)
                if not self.__check_weather(climfile, latidx, lonidx, latdelta, londelta):
                    return False

            # check soil file(s)
            for i in range(len(soilfiles)):
                soilfile = apply_prefix(soilfiles[i], inputfile_dir)
                if not self.__check_soil(soilfile, latidx, lonidx, latdelta, londelta):
                    return False

            return True

        except Exception:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

    def __get_range(self, latidx, lonidx, latdelta, londelta, glatdelta, glondelta):
        # get latitude, longitude limits
        if latdelta <= glatdelta:
            minlat = 90 - latdelta * (latidx - 0.5)
            maxlat = minlat
        else:
            minlat = 90 - latdelta * latidx
            maxlat = minlat + latdelta

        if londelta <= glondelta:
            minlon = -180 + londelta * (lonidx - 0.5)
            maxlon = minlon
        else:
            minlon = -180 + londelta * (lonidx - 1)
            maxlon = minlon + londelta

        return minlat, maxlat, minlon, maxlon

    def __check_weather(self, filename, latidx, lonidx, latdelta, londelta):
        with nc(filename) as f:
            lats, lons = f.variables['lat'][:], f.variables['lon'][:]
            glatdelta, glondelta = abs(diff(lats)[0]), abs(diff(lons)[0])
        minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, glatdelta, glondelta)

        nco = Nco()
        options = '-h -d time,0 -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon) # select first time
        nco.ncks(input = filename, output = 'tmp.nc4', options = options)

        with nc('tmp.nc4') as f:
            varnames = f.variables.keys()

            prvars = ['pr', 'prcp', 'pre', 'precip']
            found = False
            for i in range(len(prvars)):
                patt = '%s$|%s.*' % (prvars[i], prvars[i])
                for j in range(len(varnames)):
                    if compile(patt).match(varnames[j]):
                        pr = f.variables[varnames[j]][:]
                        found = True
                        break
                if found:
                    break
            if not found:
                pr = array([])
            hasweather = pr.size and (not isMaskedArray(pr) or not pr.mask.all())

        remove('tmp.nc4')

        return hasweather

    def __check_soil(self, filename, latidx, lonidx, latdelta, londelta):
        with nc(filename) as f:
            lats, lons = f.variables['lat'][:], f.variables['lon'][:]
            glatdelta, glondelta = abs(diff(lats)[0]), abs(diff(lons)[0])
        minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, glatdelta, glondelta)

        nco = Nco()
        options = '-h -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
        nco.ncks(input = filename, output = 'tmp.nc4', options = options)

        with nc('tmp.nc4') as f:
            slsi = f.variables['slsi'][:]
            hassoil = slsi.size and (not isMaskedArray(slsi) or not slsi.mask.all())

        remove('tmp.nc4')

        return hassoil
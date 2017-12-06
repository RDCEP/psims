import os
import traceback
from nco import Nco
from os import remove
from .. import checker
from re import compile
from netCDF4 import Dataset
from numpy.ma import isMaskedArray
from numpy import array, diff


class SimpleChecker(checker.Checker):

    def verify_params(self, latidx, lonidx):
        harvested_area = self.config.get('harvested_area')
        simgfile = self.config.get_dict(self.checker_type, 'simgfile')
        simgfile_var = "mask"
        tname = type(self).__name__

        if not simgfile and harvested_area:
            simgfile = harvested_area
            simgfile_var = "area"

        try:
            nc = Dataset(simgfile)
            if simgfile_var not in nc.variables:
                return False, "%s checker simgfile %s does not contain mask variable!" % (tname, simgfile)
        except IOError:
            return False, "%s checker error opening %s as a NetCDF file" % (tname, simgfile)
        return True, "%s checker likes the parameters" % tname

    def run(self, latidx, lonidx):
        try:
            climfiles = self.config.get_dict(self.checker_type, 'climfile', default='1.clim.tile.nc4')
            harvested_area = self.config.get('harvested_area')
            inputfile_dir = self.config.get_dict(self.checker_type, 'inputfile_dir', default=os.path.join('..', '..'))
            latdelta = self.config.get('latdelta') / 60
            londelta = self.config.get('londelta') / 60
            simgfile = self.config.get_dict(self.checker_type, 'simgfile', default='simgrid.nc4')
            simgfile_var = "mask"
            soilfiles = self.config.get_dict(self.checker_type, 'soilfile', default='1.soil.tile.nc4')
            threshold = self.config.get_dict(self.checker_type, 'threshold', default=0)

            if not os.path.exists(simgfile) and harvested_area:
                simgfile = harvested_area
                simgfile_var = "area"

            if not isinstance(climfiles, list):
                climfiles = [climfiles]
            if not isinstance(soilfiles, list):
                soilfiles = [soilfiles]

            # get sim grid deltas
            with Dataset(simgfile) as f:
                lats = f.variables['lat'][:]
                lons = f.variables['lon'][:]
                simglatdelta = abs(diff(lats)[0])
                simglondelta = abs(diff(lons)[0])
            minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, simglatdelta,
                                                              simglondelta)

            # check simgrid file
            nco = Nco()
            options = '-h -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
            tmpfile = "checker.tmp.nc4"
            nco.ncks(input=simgfile, output=tmpfile, options=options)

            with Dataset(tmpfile) as f:
                simgdata = f.variables[simgfile_var][:]
                notmasked = simgdata[simgdata > threshold].any()
            remove(tmpfile)

            if not notmasked:
                return False

            # check weather file(s)
            for i in range(len(climfiles)):
                climfile = os.path.join(inputfile_dir, climfiles[i])
                if not self.__check_weather(climfile, latidx, lonidx, latdelta, londelta):
                    return False

            # check soil file(s)
            for i in range(len(soilfiles)):
                soilfile = os.path.join(inputfile_dir, soilfiles[i])
                if not self.__check_soil(soilfile, latidx, lonidx, latdelta, londelta):
                    return False

            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

    @staticmethod
    def __get_range(latidx, lonidx, latdelta, londelta, glatdelta, glondelta):

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
        with Dataset(filename) as f:
            lats = f.variables['lat'][:]
            lons = f.variables['lon'][:]
            glatdelta = abs(diff(lats)[0])
            glondelta = abs(diff(lons)[0])
        minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, glatdelta, glondelta)

        # select first time
        nco = Nco()
        options = '-h -d time,0 -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
        tmpfile = "checker.wth.nc4"
        nco.ncks(input=filename, output=tmpfile, options=options)

        with Dataset(tmpfile) as f:
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
        remove(tmpfile)
        return hasweather

    def __check_soil(self, filename, latidx, lonidx, latdelta, londelta):
        with Dataset(filename) as f:
            lats = f.variables['lat'][:]
            lons = f.variables['lon'][:]
            glatdelta = abs(diff(lats)[0])
            glondelta = abs(diff(lons)[0])
        minlat, maxlat, minlon, maxlon = self.__get_range(latidx, lonidx, latdelta, londelta, glatdelta, glondelta)

        nco = Nco()
        options = '-h -d lat,%f,%f -d lon,%f,%f' % (minlat, maxlat, minlon, maxlon)
        tmpfile = "checker.soil.nc4"
        nco.ncks(input=filename, output=tmpfile, options=options)

        with Dataset(tmpfile) as f:
            slsi = f.variables['slsi'][:]
            hassoil = slsi.size and (not isMaskedArray(slsi) or not slsi.mask.all())

        remove(tmpfile)
        return hassoil


#!/usr/bin/env python
import glob
import os
import shutil
import traceback
from .. import translator

class StageInputsSharedFS(translator.Translator):

    def copy_directory(self, src, dest):
        src_files = os.listdir(src)
        for file_name in src_files:
            full_file_name = os.path.join(src, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, dest)

    # Staging per point
    def run(self, latidx, lonidx):
        try:
            # Ref data
            refdata_files = glob.glob('../../inputs/refdata/*')
            for refdata_file in refdata_files:
                shutil.copy(refdata_file, os.getcwd())

            # Campaign data
            campaign_files = glob.glob('../../inputs/campaign/*')
            for campaign_file in campaign_files:
                basename = os.path.basename(campaign_file)
                if os.path.isfile(basename):
                    os.remove(basename)
                shutil.copy(campaign_file, os.getcwd())
            return True
        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

    # Staging per tile
    def run_tile(self, tlatidx, tlonidx):
        try:
            campaign        = self.config.get_dict(self.translator_type, 'campaign')
            refdata         = self.config.get_dict(self.translator_type, 'refdata')
            soils           = self.config.get_dict(self.translator_type, 'soils')
            soils_outputs   = self.config.get_dict(self.translator_type, 'soils_outputs')
            weather         = self.config.get_dict(self.translator_type, 'weather')
            weather_outputs = self.config.get_dict(self.translator_type, 'weather_outputs')

            if not campaign:
                campaign = self.config.get('campaign')

            if not refdata:
                refdata = self.config.get('refdata')

            if not soils:
                soils = self.config.get('soils').split(',')

            if not weather:
                weather = self.config.get('weather').split(',')

            cwd             = os.getcwd()
            input_directory = cwd + os.sep + "inputs" + os.sep
            params          = self.config.get('params')
            tlatidx         = "%04d" % tlatidx
            tlonidx         = "%04d" % tlonidx

            # Campaign
            campaign_directory = input_directory + "campaign"
            if not os.path.exists(campaign_directory):
                os.makedirs(campaign_directory)
            self.copy_directory(campaign, campaign_directory)

            # Refdata
            refdata_directory = input_directory + "refdata"
            if not os.path.exists(refdata_directory):
                os.makedirs(refdata_directory)
            self.copy_directory(refdata, refdata_directory)

            # Params
            shutil.copy(params, cwd)

            # Soil tile
            for soil_index,soil_tile in enumerate(soils):
                soil_tile = os.path.join(soil_tile, tlatidx, 'soil_%s_%s.tile.nc4' % (tlatidx, tlonidx))
                if soils_outputs and soils_outputs[soil_index]:
                    output_name = soils_outputs[soil_index]
                else:
                    output_name = os.path.join(cwd, '%d.soil.tile.nc4' % (soil_index+1))
                shutil.copy(soil_tile, output_name)

            # Clim tile
            for clim_index,clim_tile in enumerate(weather):
                clim_tile = os.path.join(clim_tile, tlatidx, 'clim_%s_%s.tile.nc4' % (tlatidx, tlonidx))
                if weather_outputs and weather_outputs[clim_index]:
                    output_name = weather_outputs[clim_index]
                else:
                    output_name = os.path.join(cwd, '%d.clim.tile.nc4' % (clim_index+1))
                shutil.copy(clim_tile, output_name)
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

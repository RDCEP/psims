import common.camp2json
import common.noop
import common.nooutput2psims
import common.nooutput2psimsdaily
import common.stage_inputs_sharedfs
import common.stage_outputs_sharedfs
import common.tile_translator
import common.tile_translator_soil

import apsim75.psims2met
import apsim75.jsons2apsim
import apsim75.out2psims

import apsim79.psims2met
import apsim79.jsons2apsim
import apsim79.out2psims

import dssat45.jsons2dssat
import dssat45.out2psims
import dssat45.psims2wth
import dssat45.jsons2dssatlong

import dssat46.jsons2dssat
import dssat46.out2psims
import dssat46.out2psimsdaily
import dssat46.psims2wth
import dssat46.jsons2dssatlong

import dssat.jsons2dssat
import dssat.out2psims
import dssat.out2psimsdaily
import dssat.psims2wth
import dssat.jsons2dssatlong

import logging

class TranslatorFactory(object):
    """
        TranslatorFactory: A class to instantiate translator objects
    """

    def __init__(self):
        self.translator_objects = {
            'apsim75.psims2met'      : apsim75.psims2met.Psims2Met,
            'apsim75.jsons2apsim'    : apsim75.jsons2apsim.Jsons2Apsim,
            'apsim75.out2psims'      : apsim75.out2psims.Out2Psims,
            'apsim79.psims2met'      : apsim79.psims2met.Psims2Met,
            'apsim79.jsons2apsim'    : apsim79.jsons2apsim.Jsons2Apsim,
            'apsim79.out2psims'      : apsim79.out2psims.Out2Psims,
            'camp2json'              : common.camp2json.Camp2Json,
            'dssat45.jsons2dssat'    : dssat45.jsons2dssat.Jsons2Dssat,
            'dssat45.jsons2dssatlong': dssat45.jsons2dssatlong.Jsons2DssatLong,
            'dssat45.out2psims'      : dssat45.out2psims.Out2Psims,
            'dssat45.psims2wth'      : dssat45.psims2wth.Psims2Wth,
            'dssat46.jsons2dssat'    : dssat46.jsons2dssat.Jsons2Dssat,
            'dssat46.jsons2dssatlong': dssat46.jsons2dssatlong.Jsons2DssatLong,
            'dssat46.out2psims'      : dssat46.out2psims.Out2Psims,
            'dssat46.out2psimsdaily' : dssat46.out2psimsdaily.Out2PsimsDaily,
            'dssat46.psims2wth'      : dssat46.psims2wth.Psims2Wth,
            'dssat.jsons2dssat'      : dssat.jsons2dssat.Jsons2Dssat,
            'dssat.jsons2dssatlong'  : dssat.jsons2dssatlong.Jsons2DssatLong,
            'dssat.out2psims'        : dssat.out2psims.Out2Psims,
            'dssat.out2psimsdaily'   : dssat.out2psimsdaily.Out2PsimsDaily,
            'dssat.psims2wth'        : dssat.psims2wth.Psims2Wth,
            'noop'                   : common.noop.Noop,
            'nooutput2psims'         : common.nooutput2psims.NoOutput2Psims,
            'nooutput2psimsdaily'    : common.nooutput2psimsdaily.NoOutput2PsimsDaily,
            'stage_inputs_sharedfs'  : common.stage_inputs_sharedfs.StageInputsSharedFS,
            'stage_outputs_sharedfs' : common.stage_outputs_sharedfs.StageOutputsSharedFS,
            'tile_translator'        : common.tile_translator.TileTranslator,
            'tile_translator_soil'   : common.tile_translator_soil.SoilTileTranslator,
        }

    def create_translator(self, config, translator_type, **kwargs):
        if config.get(translator_type) == None:
            if translator_type == 'stageinputs':
                return self.translator_objects['stage_inputs_sharedfs'](config, translator_type)
            elif translator_type == 'stageoutputs':
                return self.translator_objects['stage_outputs_sharedfs'](config, translator_type)
            else:
                return self.translator_objects['noop'](config, translator_type)
        try:
            t = self.translator_objects[config.get(translator_type)['class']](config, translator_type, **kwargs)
        except KeyError:
            print "Invalid %s translator specified. Valid translators are %s\n" % (translator_type, ', '.join([k for k in self.translator_objects.keys()]))
            raise
        return t

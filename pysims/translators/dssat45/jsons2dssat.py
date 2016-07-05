#!/usr/bin/env python

# import modules
import json
import warnings
import datetime
import sys
import traceback
from numpy import double, log
from optparse import OptionParser
from .. import translator
import os

# GENERAL PURPOSE FUNCTIONS
def for_str(vstr, nleading, vtype, vwidth, jtfy = 'r', ndec = 0, zero_pad = False):
    # vtype can be 'c' (character) or 'r' (real)
    # jfty can be 'r' (right) or 'l' (left)
    if vtype == 'c':
        if len(vstr) > vwidth:
            var = vstr[: vwidth]
        else:
            var = vstr
    elif vtype == 'r':
        var = ('{:.' + str(ndec) + 'f}').format(double(vstr))
        if len(var) > vwidth:
            #warnings.warn('Real number is too long')
            var = var[: vwidth]
    else:
        raise Exception('Unknown variable type')
    if jtfy == 'r':
        var = var.zfill(vwidth) if zero_pad else var.rjust(vwidth)
    elif jtfy == 'l':
        var = var + '0' * (vwidth - len(var)) if zero_pad else var.ljust(vwidth) 
    else:
        raise Exception('Unknown jtfy method')   
    return nleading * ' ' + var

def for_field(dic, key, dft, nleading, vtype, vwidth, jtfy = 'r', ndec = 0):
    if key in dic:
        vstr = dic[key]
    else:
        vstr = dft
    return for_str(vstr, nleading, vtype, vwidth, jtfy, ndec)

def ptransfer(slcly, slsil, sloc, slcf):
    slclyf = double(slcly) / 100
    slsilf = double(slsil) / 100
    slsndf = 1. - slclyf - slsilf
    slcff  = double(slcf) / 100
    slocf  = double(sloc)

    F18 = slsndf
    G18 = slclyf
    H18 = slocf
    J18 = slcff
    I18 = 1. # density factor

    # slll
    W18 = -0.024*F18+0.487*G18+0.006*H18+0.005*F18*H18-0.013*G18*H18+0.068*F18*G18+0.031
    X18 = W18+0.14*W18-0.02
    slll = X18

    # sldul
    Y18 = -0.251*F18+0.195*G18+0.011*H18+0.006*F18*H18-0.027*G18*H18+0.452*F18*G18+0.299
    AA18 = 0.278*F18+0.034*G18+0.022*H18-0.018*F18*H18-0.027*G18*H18-0.584*F18*G18+0.078
    Z18 = Y18+(1.283*Y18*Y18-0.374*Y18-0.015)
    AB18 = AA18+(0.636*AA18-0.107)
    AC18 = AB18+Z18
    AD18 = -0.097*F18+0.043
    AE18 = AC18+AD18
    AF18 = (1-AE18)*2.65
    AG18 = AF18*(I18)
    AI18 = (1-AG18/2.65)-(1-AF18/2.65)
    AJ18 = Z18+0.2*AI18
    sldul = AJ18

    # slsat
    AH18 = 1-(AG18/2.65)
    slsat = AH18

    # sksat
    R18 = AG18
    AL18 = (log(AJ18)-log(X18))/(log(1500)-log(33))
    AM18 = (1-J18)/(1-J18*(1-1.5*(R18/2.65)))
    AK18 = AH18-AJ18
    AN18 = 1930*(AK18)**(3-AL18)*AM18
    sksat = AN18 / 10.

    # slbdm
    T18 = ((R18/2.65)*J18)/(1-J18*(1-R18/2.65))
    U18 = T18*2.65+(1-T18)*R18
    slbdm = U18

    if sldul < slll: sldul = slll + 0.01 # required by dssat!

    return slll, sldul, slsat, sksat, slbdm

# Modify variables related to soil water content
def swc_adjustments(sldul, slll, slsat, swc_delta):
    # If slll < slll_min, do nothing
    slll_min = 0.04
    if slll <= slll_min:
        return (sldul, slll, slsat)

    # Calculate ideal slll_delta
    swc = sldul - slll
    target_swc = swc + swc_delta
    slll_delta = 0.5 * (slll + target_swc - sldul)

    # Adjust delta based on slll_min constraint
    if slll - slll_delta < slll_min:
        slll_delta = slll - slll_min
    sldul = sldul + slll_delta
    slll = slll - slll_delta

    # Adjust slsat
    slsat_sldul_min_offset = 0.05
    if slsat - sldul < slsat_sldul_min_offset:
        slsat = sldul + slsat_sldul_min_offset

    return (str(sldul), str(slll), str(slsat))

class DSSATXFileOutput:
    # member variables
    def_val_R = '-99'
    def_val_C = '-99'
    def_val_I = '-99'
    def_val_D = '-99'
    def_val_blank = ''

    # cultivar parameters
    cul_params = {'MZ': ['p1', 'p2', 'p5', 'g2', 'g3', 'phint', 'eco'], \
                  'SB': ['csdl', 'ppsen', 'em-fl', 'fl-sh', 'fl-sd', 'sd-pm', \
                         'fl-lf', 'lfmax', 'slavr', 'sizlf', 'xfrt', 'wtpsd', \
                         'sfdur', 'sdpdv', 'podur', 'thrsh', 'sdpro', 'sdlip', 'eco'], \
                  'WH': ['p1v', 'p1d', 'p5', 'g1', 'g2', 'g3', 'phint', 'eco'], \
                  'RI': ['p1', 'p2r', 'p5', 'p2o', 'g1', 'g2', 'g3', 'g4', 'eco'], \
                  'SG': ['p1', 'p2', 'p2o', 'p2r', 'panth', 'p3', 'p4', 'p5', 'phint', \
                         'g1', 'g2', 'pbase', 'psat', 'eco'], \
                  'ML': ['p1', 'p20', 'p2r', 'p5', 'g1', 'g4', 'phint', 'eco']}
    cul_decs = {'MZ': [1, 3, 1, 1, 2, 2, 0], \
                'SB': [2, 3, 1, 1, 1, 2, 2, 3, 0, 1, 2, 2, 1, 2, 1, 1, 3, 3, 0], \
                'WH': [0, 0, 0, 0, 0, 2, 0, 0], \
                'RI': [1, 1, 1, 1, 1, 3, 2, 2, 0], \
                'SG': [1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 0], \
                'ML': [1, 2, 1, 1, 2, 2, 2, 0]}

    def __init__(self, exp_file, soil_file, cul_file, use_ptransfer = True): # need soil file for initial soil conditions
        exp_data = json.load(open(exp_file))
        self.exps = exp_data['experiments']
        if not len(self.exps):
            raise Exception('No experiment data')

        soil_data = json.load(open(soil_file))['soils']
        if not len(soil_data):
            raise Exception('No soil data')
        soil_ids = [s['soil_id'] for s in soil_data]
        
        self.soil_ic = {} # get initial soil conditions
        soil_profiles = []     
        for i in range(len(self.exps)):

            if 'soil_id' in self.exps[i]:
                soil_id = self.exps[i]['soil_id']
                if len(soil_id) > 10 and soil_id.find('_') != -1:
                    idx = soil_id.find('_')
                    soil_id = soil_id[: idx]
            else:
                soil_id = 'XY01234567'

            if 'delta_cly' in self.exps[i]:
                delta_cly = self.exps[i]['delta_cly']
            else:
                delta_cly = '0'
       
            if 'delta_swc' in self.exps[i]:
                delta_swc = self.exps[i]['delta_swc']
            else:
                delta_swc = self.def_val_R

            soil_profile = [soil_id, delta_cly, delta_swc]

            element_found = False
            for j in range(len(soil_profiles)):
                if soil_profiles[j] == soil_profile: element_found = True

            if not element_found:
                soil_profiles.append(soil_profile)

                soil_id_composite = 'SL' + str(len(soil_profiles)).zfill(8)
                soil_idx = soil_ids.index(soil_id)

                soil_layers = soil_data[soil_idx]['soilLayer']
                soil_layers_arr = [0] * len(soil_layers)

                for j in range(len(soil_layers)):
                    soil_layer_dic = {}
                    slcly = soil_layers[j]['slcly'] if 'slcly' in soil_layers[j] else self.def_val_R
                    slsil = soil_layers[j]['slsil'] if 'slsil' in soil_layers[j] else self.def_val_R
                    sloc  = soil_layers[j]['sloc']  if 'sloc'  in soil_layers[j] else self.def_val_R
                    slcf  = soil_layers[j]['slcf']  if 'slcf'  in soil_layers[j] else self.def_val_R                    
                    if use_ptransfer and slcly != self.def_val_R and slsil != self.def_val_R and \
                       sloc != self.def_val_R and slcf != self.def_val_R:
                        # use pedotransfer functions
                        slsnd = max(100. - double(slcly) - double(slsil), 0.)
                        slcly = max(double(slcly) + double(delta_cly), 0.)
                        slsil = max(100. - slsnd - slcly, 0.)
                        slcly = str(slcly)
                        slsil = str(slsil)
                        sldul = ptransfer(slcly, slsil, sloc, slcf)[1]
                    else:
                        # use value in file
                        sldul = soil_layers[j]['sldul'] if 'sldul' in soil_layers[j] else self.def_val_R
                    
                    soil_layer_dic['icbl']  = soil_layers[j]['sllb'] if 'sllb' in soil_layers[j] else self.def_val_R
                    soil_layer_dic['icno3'] = soil_layers[j]['sloc'] if 'sloc' in soil_layers[j] else self.def_val_R
                    soil_layer_dic['ich2o'] = str(sldul)
                    soil_layers_arr[j] = soil_layer_dic

                self.soil_ic[soil_id_composite] = soil_layers_arr

        self.cul_file = cul_file        

    def toXFile(self):
        if self.exps is None or self.exps == []:
            return
        
        # get defaults
        dR = self.def_val_R
        dC = self.def_val_C
        dI = self.def_val_I
        dD = self.def_val_D
        dblank = self.def_val_blank

        # pull meta data from first experiment
        exp0 = self.exps[0]
        exname = exp0['exname_o']
        locname = self.__get_obj(exp0, 'local_name', dblank)
        people = self.__get_obj(exp0, 'person_notes', dblank)
        address = self.__get_obj(exp0, 'institution', dblank)
        site = self.__get_obj(exp0, 'site_name', dblank)
        notes = self.__get_obj(exp0, 'tr_notes', dblank)

        # EXP.DETAILS section
        x_str = '*EXP.DETAILS: {:10s} {:60s}\n\n'.format(exname, locname)
        
        # GENERAL section
        x_str += '*GENERAL\n'
        # people
        if people != '':
            x_str += '@PEOPLE\n {:75s}\n'.format(people)
        # address
        if address != '':
            x_str += '@ADDRESS\n {:75s}\n'.format(address)
        # site
        if site != '':
            x_str += '@SITE\n {:75s}\n\n'.format(site)
        # plot information
        plot_ids = ['plta', 'pltr#', 'pltln', 'pldr', 'pltsp', 'pllay', \
                    'pltha', 'plth#', 'plthl', 'plthm']
        has_plot = False
        for p in plot_ids:
            if self.__get_obj(exp0, p, '') != '':
                has_plot = True
                break
        if has_plot:
            x_str += '@ PAREA  PRNO  PLEN  PLDR  PLSP  PLAY HAREA  HRNO  HLEN  HARM.........\n'
            x_str += for_field(exp0, 'plta', dR, 3, 'r', 6, ndec = 1) + \
                     for_field(exp0, 'pltr#', dI, 1, 'r', 5) + \
                     for_field(exp0, 'pltln', dR, 1, 'r', 5, ndec = 1) + \
                     for_field(exp0, 'pldr', dI, 1, 'r', 5) + \
                     for_field(exp0, 'pltsp', dI, 1, 'r', 5) + \
                     for_field(exp0, 'pllay', dC, 1, 'c', 5) + \
                     for_field(exp0, 'pltha', dR, 1, 'r', 5, ndec = 1) + \
                     for_field(exp0, 'plth#', dI, 1, 'r', 5) + \
                     for_field(exp0, 'plthl', dR, 1, 'r', 5, ndec = 1) + \
                     for_field(exp0, 'plthm', dC, 1, 'c', 15) + '\n'
        # notes
        if notes != '':
            x_str += '@NOTES\n {:75s}\n\n'.format(notes)
        
        # TREATMENTS section
        x_str += '*TREATMENTS                        -------------FACTOR LEVELS------------\n'
        x_str += '@N R O C TNAME.................... CU FL SA IC MP MI MF MR MC MT ME MH SM\n'
        nexp = len(self.exps)
        
        cu_arr = []; fl_arr  = []; sa_arr = []
        ic_arr = []; mp_arr  = []; mi_arr = []
        mf_arr = []; mr_arr  = []; mc_arr = []
        mt_arr = []; me_arr  = []; mh_arr = []
        sm_arr = []; fl_arr2 = [] # tracks unique soil_id/delta_cly combinations
        cu_arr2 = [] # tracks cultivar parameters

        for i in range(nexp):            
            sq_arr = self.__get_list(self.exps[i], 'dssat_sequence', 'data')
            evt_arr = self.__get_list(self.exps[i], 'management', 'events')
            root_arr = self.__get_obj(self.exps[i], 'dssat_root', [])
            me_org_arr = self.__get_list(self.exps[i], 'dssat_environment_modification', 'data')
            sm_org_arr = self.__get_list(self.exps[i], 'dssat_simulation_control', 'data')
            soil_arr = self.__read_sw_data(self.exps[i], 'soil')

            for j in range(len(sq_arr)):
                sq_data = sq_arr[j]
                
                seq_id = self.__get_obj(sq_data, 'seqid', dblank)  
                em = self.__get_obj(sq_data, 'em', dblank)
                sm = self.__get_obj(sq_data, 'sm', dblank)
            
                cu_data = {}; fl_data = {}; mp_data = {}; sm_data = {}; fl_data2 = {}; cu_data2 = {}
                mi_sub_arr = []; mf_sub_arr = []; mr_sub_arr = []
                mc_sub_arr = []; mt_sub_arr = []; me_sub_arr = []
                mh_sub_arr = []
                
                if j < len(soil_arr):
                    soil_data = soil_arr[j]
                elif soil_arr == []:
                    soil_data = {}
                else:
                    soil_data = soil_arr[0]
                if soil_data is None:
                    soil_data = {}
                
                if j < len(root_arr):
                    root_data = root_arr[j]
                else:
                    root_data = self.exps[i]
                
                if not 'delta_cly' in root_data: root_data['delta_cly'] = '0' # set default delta_cly
                
                # set field info
                self.__copy_item(fl_data, root_data, 'id_field')
                fl_data['wst_id'] = root_data['wst_id']
                self.__copy_item(fl_data, root_data, 'flsl')
                self.__copy_item(fl_data, root_data, 'flob')
                self.__copy_item(fl_data, root_data, 'fl_drntype')
                self.__copy_item(fl_data, root_data, 'fldrd')
                self.__copy_item(fl_data, root_data, 'fldrs')
                self.__copy_item(fl_data, root_data, 'flst')
                if 'sltx' in soil_data:
                    self.__copy_item(fl_data, soil_data, 'sltx')
                else:
                    self.__copy_item(fl_data, root_data, 'sltx')
                self.__copy_item(fl_data, soil_data, 'sldp')
                self.__copy_item(fl_data, root_data, 'soil_id')
                self.__copy_item(fl_data, root_data, 'fl_name')
                self.__copy_item(fl_data, root_data, 'fl_lat')
                self.__copy_item(fl_data, root_data, 'fl_long')
                self.__copy_item(fl_data, root_data, 'flele')
                self.__copy_item(fl_data, root_data, 'farea')
                self.__copy_item(fl_data, root_data, 'fllwr')
                self.__copy_item(fl_data, root_data, 'flsla')
                self.__copy_item(fl_data, self.__get_obj(root_data, 'dssat_info', {}), 'flhst')
                self.__copy_item(fl_data, self.__get_obj(root_data, 'dssat_info', {}), 'fhdur')
                soil_id = self.__get_obj(fl_data, 'soil_id', '')
                if len(soil_id) > 10 and soil_id.find('_') != -1:
                    idx = soil_id.find('_')
                    fl_data['soil_id'] = soil_id[: idx]
                
                fl_data2['soil_id'] = fl_data['soil_id']
                self.__copy_item(fl_data2, root_data, 'delta_cly') # JPC: ADDED DELTA_CLY 06/12/14
                self.__copy_item(fl_data2, root_data, 'delta_swc') 
                fl_num2 = self.__set_sec_data(fl_data2, fl_arr2)
                
                fl_data['soil_id_composite'] = 'SL' + str(fl_num2).zfill(8) # new composite soil id
                fl_num = self.__set_sec_data(fl_data, fl_arr)
                # set initial condition info
                ic_data = self.__get_obj(root_data, 'initial_conditions', {})
                ic_data['soil_id_composite'] = self.__get_obj(fl_data, 'soil_id_composite', dC) # add composite soil id to ic data
                ic_num = self.__set_sec_data(ic_data, ic_arr)
                
                # set environment modification info
                for k in range(len(me_org_arr)):
                    if me_org_arr[k]['em'] == em:
                        tmp = {}
                        tmp.update(me_org_arr[k])
                        tmp.pop('em')
                        me_sub_arr.append(tmp)
                        
                # set soil analysis info
                soil_layers = self.__get_obj(soil_data, 'soilLayer', [])
                has_soil_analysis = False
                for k in range(len(soil_layers)):
                    if self.__get_obj(soil_layers[k], 'slsc', '') != '':
                        has_soil_analysis = True
                        break
                if has_soil_analysis:
                    sa_data = {}
                    sa_sub_arr = []
                    for k in range(len(soil_layers)):
                        sa_sub_data = {}
                        self.__copy_item(sa_sub_data, soil_layers[k], 'sabl', 'sllb')
                        self.__copy_item(sa_sub_data, soil_layers[k], 'sasc', 'slsc')
                        sa_sub_arr.append(sa_sub_data)
                    self.__copy_item(sa_data, soil_data, 'sadat')
                    sa_data['soilLayer'] = sa_sub_arr
                    sa_num = self.__set_sec_data(sa_data, sa_arr)
                else:
                    sa_num = 0
                    
                # set simulation control info
                for k in range(len(sm_org_arr)):
                    if sm_org_arr[k]['sm'] == sm:
                        sm_data.update(sm_org_arr[k])
                        sm_data.pop('sm')
                        break
                        
                self.__copy_item(sm_data, root_data, 'sdat')
                
                # loop through all events
                for k in range(len(evt_arr)):
                    evt_data = {}
                    evt_data.update(evt_arr[k])
                    
                    if self.__get_obj(evt_data, 'seqid', dblank) == seq_id:
                        evt_data.pop('seqid')
                        
                        if self.__get_obj(evt_data, 'event', dblank) == 'planting':
                            # planting
                            cpar = self.cul_params[evt_data['crid']]
                            if evt_data.viewkeys() >= set(cpar): # contains all parameters
                                for c in cpar:
                                    self.__copy_item(cu_data2, evt_data, c)
                                self.__copy_item(cu_data2, evt_data, 'crid')
                                cu_num2 = self.__set_sec_data(cu_data2, cu_arr2)
                                cu_data['cul_id'] = 'CC' + str(cu_num2 - 1).zfill(4)
                            else:
                                self.__copy_item(cu_data, evt_data, 'cul_id')
                                self.__copy_item(cu_data, evt_data, 'dssat_cul_id')
                            self.__copy_item(cu_data, evt_data, 'cul_name')
                            self.__copy_item(cu_data, evt_data, 'crid')
                            self.__copy_item(cu_data, evt_data, 'rm')
                            self.__copy_item(cu_data, evt_data, 'cul_notes')
                            # TODO: Translate CRID?
                            mp_data.update(evt_data)
                            mp_data.pop('cul_name')
                            mp_data.pop('cul_id')
                            mp_data.pop('crid')
                            for c in cpar: # remove from planting section
                                if c in mp_data: mp_data.pop(c)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'irrigation':
                            # irrigation
                            mi_sub_arr.append(evt_data)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'fertilizer':
                            # fertilizer
                            mf_sub_arr.append(evt_data)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'organic_matter':
                           # organic matter
                            mr_sub_arr.append(evt_data)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'chemical':
                            # chemical
                            mc_sub_arr.append(evt_data)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'tillage':
                            # tillage
                            mt_sub_arr.append(evt_data)
                        elif self.__get_obj(evt_data, 'event', dblank) == 'harvest':
                            mh_sub_arr.append(evt_data)
                            if self.__get_obj(evt_data, 'date', '').strip() != '':
                                sm_data['hadat_valid'] = 'Y'
                                
                cu_num = self.__set_sec_data(cu_data, cu_arr)
                mp_num = self.__set_sec_data(mp_data, mp_arr)
                mi_num = self.__set_sec_data(mi_sub_arr, mi_arr)
                mf_num = self.__set_sec_data(mf_sub_arr, mf_arr)
                mr_num = self.__set_sec_data(mr_sub_arr, mr_arr)
                mc_num = self.__set_sec_data(mc_sub_arr, mc_arr)
                mt_num = self.__set_sec_data(mt_sub_arr, mt_arr)
                me_num = self.__set_sec_data(me_sub_arr, me_arr)
                mh_num = self.__set_sec_data(mh_sub_arr, mh_arr)
                sm_num = self.__set_sec_data(sm_data, sm_arr)
                if not sm_num:
                    sm_num = 1
                
                x_str += for_field(sq_data, 'trno', '1', 0, 'r', 2) + \
                         for_field(sq_data, 'sq', '1', 1, 'r', 1) + \
                         for_field(sq_data, 'op', '1', 1, 'r', 1) + \
                         for_field(sq_data, 'co', '0', 1, 'r', 1) + \
                         for_field(sq_data, 'trt_name', '', 1, 'c', 25, jtfy = 'l') + \
                         for_str(str(cu_num), 1, 'r', 2) + \
                         for_str(str(fl_num), 1, 'r', 2) + \
                         for_str(str(sa_num), 1, 'r', 2) + \
                         for_str(str(ic_num), 1, 'r', 2) + \
                         for_str(str(mp_num), 1, 'r', 2) + \
                         for_str(str(mi_num), 1, 'r', 2) + \
                         for_str(str(mf_num), 1, 'r', 2) + \
                         for_str(str(mr_num), 1, 'r', 2) + \
                         for_str(str(mc_num), 1, 'r', 2) + \
                         for_str(str(mt_num), 1, 'r', 2) + \
                         for_str(str(me_num), 1, 'r', 2) + \
                         for_str(str(mh_num), 1, 'r', 2) + \
                         for_str(str(sm_num), 1, 'r', 2) + '\n'
        
        x_str += '\n'
        
        # CULTIVARS section
        if cu_arr != []:
            x_str += '*CULTIVARS\n'
            x_str += '@C CR INGENO CNAME\n'
            for i in range(len(cu_arr)):
                sec_data = cu_arr[i]
                crid = self.__get_obj(sec_data, 'crid', '')
                if crid == '':
                    warnings.warn('Cultivar CRID is missing')
                # MAY NEED THIS LATER!
                # def_cul_id = self.__get_obj(sec_data, 'cul_id', dC)
                # for_field(sec_data, 'dssat_cul_id', def_cul_id, 1, 'c', 6)
                x_str += for_str(str(i + 1), 0, 'r', 2) + \
                         for_field(sec_data, 'crid', dblank, 1, 'c', 2) + \
                         for_field(sec_data, 'cul_id', dC, 1, 'c', 6) + \
                         for_field(sec_data, 'cul_name', dC, 1, 'c', 16, jtfy = 'l') + '\n'
                if self.__get_obj(sec_data, 'rm', '') != '' or self.__get_obj(sec_data, 'cul_notes', '') != '':
                    # SKIP CULTIVAR NOTES FOR NOW
                    pass

            x_str += '\n'  
        else:
            warnings.warn('Cultivar information is missing')
            
        # FIELDS section
        if fl_arr != []:
            x_str += '*FIELDS\n'
            x_str += '@L ID_FIELD WSTA....  FLSA  FLOB  FLDT  FLDD  FLDS  FLST SLTX  SLDP  ID_SOIL    FLNAME\n'
            event_part2 = '@L ...........XCRD ...........YCRD .....ELEV .............AREA .SLEN .FLWR .SLAS FLHST FHDUR\n'
        else:
            warnings.warn('Field information is missing')
        for i in range(len(fl_arr)):
            sec_data = fl_arr[i]
            if self.__get_obj(sec_data, 'wst_id', '') == '':
                warnings.warn('Field WST_ID is missing')
            soil_id = self.__get_obj(sec_data, 'soil_id_composite', dC)
            if soil_id == '':
                warnings.warn('Field SOIL_ID is missing')
            elif len(soil_id) > 10:
                warnings.warn('Oversized field SOIL_ID')
            x_str += for_str(str(i + 1), 0, 'r', 2) + \
                     for_field(sec_data, 'id_field', dC, 1, 'c', 8, jtfy = 'l') + \
                     for_field(sec_data, 'wst_id', dC, 1, 'c', 8, jtfy = 'l') + \
                     for_field(sec_data, 'flsl', dD, 1, 'c', 5) + \
                     for_field(sec_data, 'flob', dR, 1, 'r', 5) + \
                     for_field(sec_data, 'fl_drntype', dC, 1, 'c', 5, jtfy = 'l') + \
                     for_field(sec_data, 'fldrd', dR, 1, 'r', 5) + \
                     for_field(sec_data, 'fldrs', dR, 1, 'r', 5) + \
                     for_field(sec_data, 'flst', dC, 1, 'c', 5, jtfy = 'l') + \
                     for_field(sec_data, 'sltx', dD, 1, 'c', 5, jtfy = 'l') + \
                     for_field(sec_data, 'sldp', dR, 1, 'r', 5) + \
                     for_str(str(soil_id), 1, 'c', 10, jtfy = 'l') + \
                     ' ' + self.__get_obj(sec_data, 'fl_name', dC) + '\n'
            event_part2 += for_str(str(i + 1), 0, 'r', 2) + \
                           for_field(sec_data, 'fl_long', dR, 1, 'r', 15, ndec = 2) + \
                           for_field(sec_data, 'fl_lat', dR, 1, 'r', 15, ndec = 2) + \
                           for_field(sec_data, 'flele', dR, 1, 'r', 9) + \
                           for_field(sec_data, 'farea', dR, 1, 'r', 17) + \
                           ' -99  ' + \
                           for_field(sec_data, 'fllwr', dD, 1, 'r', 5) + \
                           for_field(sec_data, 'flsla', dD, 1, 'r', 5) + \
                           for_field(sec_data, 'flhst', dD, 1, 'c', 5) + \
                           for_field(sec_data, 'fhdur', dD, 1, 'r', 5) + '\n'
        if fl_arr != []:
            x_str += event_part2 + '\n'
            
        # SOIL ANALYSIS section
        if sa_arr != []:
            x_str += '*SOIL ANALYSIS\n'
            for i in range(len(sa_arr)):
                sec_data = sa_arr[i]
                x_str += '@A SADAT  SMHB  SMPX  SMKE  SANAME\n'
                x_str += for_str(str(i + 1), 0, 'r', 2) + \
                         for_field(sec_data, 'sadat', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'samhb', dC, 1, 'c', 5) + \
                         for_field(sec_data, 'sampx', dC, 1, 'c', 5) + \
                         for_field(sec_data, 'samke', dC, 1, 'c', 5) + \
                         ' ' + self.__get_obj(sec_data, 'sa_name', dC)
                sub_data_arr = self.__get_obj(sec_data, 'soilLayer', [])
                if sub_data_arr != []:
                    x_str += '@A  SABL  SADM  SAOC  SANI SAPHW SAPHB  SAPX  SAKE  SASC\n'
                for j in range(len(sub_data_arr)):
                    sub_data = sub_data_arr[j]
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_field(sub_data, 'sabl', dR, 1, 'r', 5) + \
                             for_field(sub_data, 'sabdm', dR, 1, 'r', 5, ndec = 1) + \
                             for_field(sub_data, 'saoc', dR, 1, 'r', 5, ndec = 2) + \
                             for_field(sub_data, 'sani', dR, 1, 'r', 5, ndec = 2) + \
                             for_field(sub_data, 'saphw', dR, 1, 'r', 5, ndec = 1) + \
                             for_field(sub_data, 'saphb', dR, 1, 'r', 5, ndec = 1) + \
                             for_field(sub_data, 'sapx', dR, 1, 'r', 5, ndec = 1) + \
                             for_field(sub_data, 'sake', dR, 1, 'r', 5, ndec = 1) + \
                             for_field(sub_data, 'sasc', dR, 1, 'r', 5) + '\n'
        
        # INITIAL CONDITIONS section
        if ic_arr != []:
            x_str += '*INITIAL CONDITIONS\n'
            for i in range(len(ic_arr)):
                sec_data = ic_arr[i]
                icdat = self.__translate_date_str(self.__get_obj(sec_data, 'icdat', dD))
                x_str += '@C   PCR ICDAT  ICRT  ICND  ICRN  ICRE  ICWD ICRES ICREN ICREP ICRIP ICRID ICNAME\n'
                x_str += for_str(str(i + 1), 0, 'r', 2) + \
                         for_field(sec_data, 'icpcr', dC, 1, 'c', 5) + \
                         for_str(icdat, 1, 'c', 5) + \
                         for_field(sec_data, 'icrt', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icnd', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icrz#', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icrze', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icwt', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icrag', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icrn', dR, 1, 'r', 5, ndec = 2) + \
                         for_field(sec_data, 'icrp', dR, 1, 'r', 5, ndec = 2) + \
                         for_field(sec_data, 'icrip', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'icrdp', dR, 1, 'r', 5) + \
                         ' ' + self.__get_obj(sec_data, 'ic_name', dR) + '\n'
                sub_data_arr = self.__get_obj(self.soil_ic, self.__get_obj(sec_data, 'soil_id_composite', dC), [])
                if not 'icnh4' in sec_data:
                    layers = self.__get_obj(sec_data, 'soilLayer', [])
                    icnh4 = self.__get_obj(layers[0], 'icnh4', dR) if layers != [] else dR
                else:
                    icnh4 = sec_data['icnh4']
                frac_full = self.__get_obj(sec_data, 'frac_full', '0.5')
                if sub_data_arr != []:
                    x_str += '@C  ICBL  SH2O  SNH4  SNO3\n'                
                for j in range(len(sub_data_arr)):
                    sub_data = sub_data_arr[j]
                    ich2o = double(frac_full) * double(self.__get_obj(sub_data, 'ich2o', dR))
                    ich2o = min(ich2o, 0.75) # maximum value of 1.75
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_field(sub_data, 'icbl', dR, 1, 'r', 5) + \
                             for_str(ich2o, 1, 'r', 5, ndec = 3) + \
                             for_str(icnh4, 1, 'c', 5) + \
                             for_field(sub_data, 'icno3', dR, 1, 'r', 5, ndec = 1) + '\n'
            x_str += '\n'

        # PLANTING DETAILS section
        if mp_arr != []:
            x_str += '*PLANTING DETAILS\n'
            x_str += '@P PDATE EDATE  PPOP  PPOE  PLME  PLDS  PLRS  PLRD  PLDP  PLWT  PAGE  PENV  PLPH  SPRL                        PLNAME\n'
            for i in range(len(mp_arr)):
                sec_data = mp_arr[i]
                pdate = self.__get_obj(sec_data, 'date', '')
                if pdate == '':
                    warnings.warn('Planting PDATE is missing')
                if self.__get_obj(sec_data, 'plpoe', '') == '':
                    warnings.warn('Planting PLPOE is missing')
                if self.__get_obj(sec_data, 'plrs', '') == '':
                    warnings.warn('Planting PLRS is missing')
                # convert from mm to cm
                pldp = self.__get_obj(sec_data, 'pldp', '')
                if pldp != '':
                    sec_data['pldp'] = str(double(pldp) / 10.)
                date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                pldae = self.__translate_date_str(self.__get_obj(sec_data, 'pldae', dD))
                plpoe = self.__get_obj(sec_data, 'plpoe', dR)
                plpop = self.__get_obj(sec_data, 'plpop', dR)
                if double(plpoe) != double(plpop): plpoe = plpop # ensure equality
                x_str += for_str(str(i + 1), 0, 'r', 2) + \
                         for_str(date, 1, 'c', 5) + \
                         for_str(pldae, 1, 'c', 5) + \
                         for_str(plpop, 1, 'r', 5, ndec = 1) + \
                         for_str(plpoe, 1, 'r', 5, ndec = 1) + \
                         for_field(sec_data, 'plma', dC, 5, 'c', 1, jtfy = 'l') + \
                         for_field(sec_data, 'plds', dC, 5, 'c', 1, jtfy = 'l') + \
                         for_field(sec_data, 'plrs', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'plrd', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'pldp', dR, 1, 'r', 5, ndec = 1) + \
                         for_field(sec_data, 'plmwt', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'page', dR, 1, 'r', 5) + \
                         for_field(sec_data, 'plenv', dR, 1, 'r', 5, ndec = 1) + \
                         for_field(sec_data, 'plph', dR, 1, 'r', 5, ndec = 1) + \
                         for_field(sec_data, 'plspl', dR, 1, 'r', 5) + \
                         ' ' * 24 + self.__get_obj(sec_data, 'pl_name', dC) + '\n'
            x_str += '\n'
        else:
            warnings.warn('Planting information is missing')
            
        # IRRIGATION AND WATER MANAGEMENT section
        if mi_arr != []:
            x_str += '*IRRIGATION AND WATER MANAGEMENT\n'
            for i in range(len(mi_arr)):
                sub_data_arr = mi_arr[i]
                if sub_data_arr != []:
                    sub_data = sub_data_arr[0]
                else:
                    sub_data = {}
                x_str += '@I  EFIR  IDEP  ITHR  IEPT  IOFF  IAME  IAMT IRNAME\n'
                x_str += for_str(str(i + 1), 0, 'r', 2) + \
                         for_field(sub_data, 'ireff', dR, 1, 'r', 5, ndec = 2) + \
                         for_field(sub_data, 'irmdp', dR, 1, 'r', 5) + \
                         for_field(sub_data, 'irthr', dR, 1, 'r', 5) + \
                         for_field(sub_data, 'irept', dR, 1, 'r', 5) + \
                         for_field(sub_data, 'irstg', dR, 1, 'c', 5) + \
                         for_field(sub_data, 'iame', dR, 1, 'c', 5) + \
                         for_field(sub_data, 'iamt', dR, 1, 'r', 5) + \
                         ' ' + self.__get_obj(sub_data, 'ir_name', dC) + '\n'
                if sub_data_arr != []:
                    x_str += '@I IDATE  IROP IRVAL\n'
                for j in range(len(sub_data_arr)):
                    sub_data = sub_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sub_data, 'date', dC))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sub_data, 'irop', dC, 1, 'c', 5) + \
                             for_field(sub_data, 'irval', dR, 1, 'r', 5) + '\n'
            x_str += '\n'
            
        # FERTILIZERS section
        if mf_arr != []:
            x_str += '*FERTILIZERS (INORGANIC)\n'
            x_str += '@F FDATE  FMCD  FACD  FDEP  FAMN  FAMP  FAMK  FAMC  FAMO  FOCD FERNAME\n'
            for i in range(len(mf_arr)):
                sec_data_arr = mf_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sec_data, 'fecd', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'feacd', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'fedep', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feamn', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feamp', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feamk', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feamc', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feamo', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'feocd', dR, 1, 'c', 5) + \
                             ' ' + self.__get_obj(sec_data, 'fe_name', dC) + '\n'
            x_str += '\n'
            
        # RESIDUES AND ORGANIC FERTILIZER section
        if mr_arr != []:
            x_str += '*RESIDUES AND ORGANIC FERTILIZER\n'
            x_str += '@R RDATE  RCOD  RAMT  RESN  RESP  RESK  RINP  RDEP  RMET RENAME\n'
            for i in range(len(mr_arr)):
                sec_data_arr = mr_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sec_data, 'omcd', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'omamt', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'omn%', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'omp%', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'omk%', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'ominp', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'omdep', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'omacd', dR, 1, 'r', 5) + \
                             ' ' + self.__get_obj(sec_data, 'on_name', dC) + '\n'
            x_str += '\n'
        
        # CHEMICAL APPLICATIONS section
        if mc_arr != []:
            x_str += '*CHEMICAL APPLICATIONS\n'
            x_str += '@C CDATE CHCOD CHAMT  CHME CHDEP   CHT..CHNAME\n'
            for i in range(len(mc_arr)):
                sec_data_arr = mc_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sec_data, 'chcd', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'chamt', dR, 1, 'r', 5) + \
                             for_field(sec_data, 'chacd', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'chdep', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'ch_targets', dC, 1, 'c', 5) + \
                             '  ' + self.__get_obj(sec_data, 'ch_name', dC) + '\n'
            x_str += '\n'
        
        # TILLAGE section
        if mt_arr != []:
            x_str += '*TILLAGE AND ROTATIONS\n'
            x_str += '@T TDATE TIMPL  TDEP TNAME\n'
            for i in range(len(mt_arr)):
                sec_data_arr = mt_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sec_data, 'tiimp', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'tidep', dR, 1, 'c', 5) + \
                             ' ' + self.__get_obj(sec_data, 'ti_name', dC) + '\n'
            x_str += '\n'
        
        # ENVIRONMENT MODIFICATIONS section
        if me_arr != []:
            x_str += '*ENVIRONMENT MODIFICATIONS\n'
            x_str += '@E ODATE EDAY  ERAD  EMAX  EMIN  ERAIN ECO2  EDEW  EWIND ENVNAME\n'
            for i in range(len(me_arr)):
                sec_data_arr = me_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]['data']
                    odyer = self.__get_obj(sec_data, 'odyer', dC).split('.')[0] # remove decimal part
                    odyer = for_str(odyer, 1, 'c', 2, zero_pad = True)
                    odday = self.__get_obj(sec_data, 'odday', dC).split('.')[0]
                    odday = for_str(odday, 0, 'c', 3, zero_pad = True)
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             odyer + odday + \
                             for_field(sec_data, 'eday', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'erad', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'emax', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'emin', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'erain', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'eco2', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'edew', dC, 1, 'c', 5) + \
                             for_field(sec_data, 'ewind', dC, 1, 'c', 5) + \
                             ' ' + self.__get_obj(sec_data, 'envnam', dC) + '\n'                             
            x_str += '\n'
            
        # HARVEST DETAILS section
        if mh_arr != []:
            x_str += '*HARVEST DETAILS\n'
            x_str += '@H HDATE  HSTG  HCOM HSIZE   HPC  HBPC HNAME\n'
            for i in range(len(mh_arr)):
                sec_data_arr = mh_arr[i]
                for j in range(len(sec_data_arr)):
                    sec_data = sec_data_arr[j]
                    date = self.__translate_date_str(self.__get_obj(sec_data, 'date', dD))
                    x_str += for_str(str(i + 1), 0, 'r', 2) + \
                             for_str(date, 1, 'c', 5) + \
                             for_field(sec_data, 'hastg', dC, 1, 'c', 5, jtfy = 'l') + \
                             for_field(sec_data, 'hacom', dC, 1, 'c', 5, jtfy = 'l') + \
                             for_field(sec_data, 'hasiz', dC, 1, 'c', 5, jtfy = 'l') + \
                             for_field(sec_data, 'hap%', dR, 1, 'c', 5) + \
                             for_field(sec_data, 'hab%', dR, 1, 'c', 5) + \
                             ' ' + self.__get_obj(sec_data, 'ha_name', dC) + '\n'
            x_str += '\n'
            
        # SIMULATION CONTROLS and AUTOMATIC MANAGEMENT section
        if sm_arr != []:
            x_str += '*SIMULATION CONTROLS\n'
            for i in range(len(sm_arr)):
                sec_data = sm_arr[i]
                x_str += self.__create_SMMA_str(i + 1, sec_data)
                if i != len(sm_arr) - 1:
                    x_str += '\n\n'
        else:
            x_str += '*SIMULATION CONTROLS\n'
            x_str += self.__create_SMMA_str(1, {})
        
        c_str = self.__write_cul_file(cu_arr2)

        return x_str, c_str
        
    def __read_sw_data(self, data, key):
        ret = []
        d = data[key]
        if not d is None:
            if isinstance(d, list):
                ret = d
            else:
                ret = []
                ret.append(d)
        else:
            ret = []
        return ret

    def __get_obj(self, dic, key, dft):
        # gets actual object, NOT copy
        if key in dic:
            return dic[key]
        else:
            return dft
    
    def __get_list(self, data, block_name, list_name):
        block = self.__get_obj(data, block_name, {})
        return self.__get_obj(block, list_name, [])
    
    def __copy_item(self, to, frm, to_key, frm_key = None, delete_flg = False):
        if frm_key is None:
            frm_key = to_key
        if frm_key in frm and not frm[frm_key] is None:
            if delete_flg:
                to[to_key] = frm.pop(frm_key)
            else:
                to[to_key] = frm[frm_key]
    
    def __set_sec_data(self, m, arr):
        if m != {} and m != []:
            for j in range(len(arr)):
                if arr[j] == m:
                    return j + 1
            arr.append(m)
            return len(arr)
        else:
            return 0
            
    def __translate_date_str(self, date_str):
        # convert from yyyymmdd to yyddd
        if len(date_str) < 8:
            return date_str
        year = int(date_str[: 4])
        month = int(date_str[4 : 6])
        day = int(date_str[6 : 8])
        year += (year < 1900) * 100 # needed because strftime doesn't work for year < 1900
        return datetime.date(year, month, day).strftime('%y%j')
        
    def __create_SMMA_str(self, smid, tr_data):
        # get default
        dC = self.def_val_C
                        
        nitro = 'Y'
        water = 'Y'
        co2 = 'M'
        har_opt = 'M'
        sm = '{:2d}'.format(smid)
        
        co2y = self.__get_obj(tr_data, 'co2y', '').strip()
        if co2y != '' and not co2y.startswith('-'):
            co2 = 'W'
        
        sdate = self.__get_obj(tr_data, 'sdat', '')
        if sdate == '':
            sub_data = self.__get_obj(tr_data, 'planting', {})
            sdate = self.__get_obj(sub_data, 'date', self.def_val_D)
        sdate = self.__translate_date_str(sdate)
        sdate = '{:5s}'.format(sdate)
        
        if self.__get_obj(tr_data, 'hadat_valid', '').strip() != '':
            har_opt = 'R'   
        
        # GENERAL
        sb = '@N GENERAL     NYERS NREPS START SDATE RSEED SNAME.................... SMODEL\n'
        sm_str = self.__get_obj(tr_data, 'general', {})
        if sm_str != {}:
            if sdate.strip() != '-99' and sdate.strip() != '':
                sm_str['sdyer'] = sdate[: 2]
                sm_str['sdday'] = sdate[2 : 5]
            sdyer = self.__get_obj(sm_str, 'sdyer', dC).split('.')[0] # remove decimal part
            sdyer = for_str(sdyer, 1, 'c', 2, zero_pad = True)
            sdday = self.__get_obj(sm_str, 'sdday', dC).split('.')[0]
            sdday = for_str(sdday, 0, 'c', 3, zero_pad = True)            
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('GE', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'nyers', dC, 3, 'c', 3) + \
                  for_field(sm_str, 'nreps', dC, 4, 'c', 2) + \
                  for_field(sm_str, 'start', dC, 5, 'c', 1) + \
                  sdyer + sdday + \
                  for_field(sm_str, 'rseed', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'sname', dC, 1, 'c', 25, jtfy = 'l') + \
                  ' ' + self.__get_obj(sm_str, 'smodel', dC) + '\n'
        else:
            sb += sm + ' GE              1     1     S ' + sdate + '  2150 DEFAULT SIMULATION CONTROL\n'
        
        # OPTIONS
        sb += '@N OPTIONS     WATER NITRO SYMBI PHOSP POTAS DISES  CHEM  TILL   CO2\n'
        sm_str = self.__get_obj(tr_data, 'options', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('OP', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'water', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'nitro', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'symbi', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'phosp', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'potas', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'dises', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'chem', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'till', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'co2', dC, 5, 'c', 1) + '\n'
        else:
            sb += sm + ' OP              ' + water + '     ' + nitro + '     Y     N     N     N     N     Y     ' + co2 + '\n'
        
        # METHODS
        sb += '@N METHODS     WTHER INCON LIGHT EVAPO INFIL PHOTO HYDRO NSWIT MESOM MESEV MESOL\n'
        sm_str = self.__get_obj(tr_data, 'methods', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('ME', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'wther', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'incon', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'light', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'evapo', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'infil', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'photo', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'hydro', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'nswit', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'mesom', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'mesev', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'mesol', dC, 5, 'c', 1) + '\n'
        else:
            sb += sm + ' ME              M     M     E     R     S     L     R     1     P     S     2\n'
        
        # MANAGEMENT
        sb += '@N MANAGEMENT  PLANT IRRIG FERTI RESID HARVS\n'
        sm_str = self.__get_obj(tr_data, 'management', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('MA', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'plant', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'irrig', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'ferti', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'resid', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'harvs', dC, 5, 'c', 1) + '\n'
        else:
            sb = sm + ' MA              R     R     R     R     ' + har_opt + '\n'
        
        # OUTPUTS
        sb += '@N OUTPUTS     FNAME OVVEW SUMRY FROPT GROUT CAOUT WAOUT NIOUT MIOUT DIOUT VBOSE CHOUT OPOUT\n'
        sm_str = self.__get_obj(tr_data, 'outputs', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('OU', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'fname', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'ovvew', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'sumry', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'fropt', dC, 4, 'c', 2) + \
                  for_field(sm_str, 'grout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'caout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'waout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'niout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'miout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'diout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'vbose', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'chout', dC, 5, 'c', 1) + \
                  for_field(sm_str, 'opout', dC, 5, 'c', 1) + '\n\n'
        else:
            sb += sm + ' OU              N     Y     Y     1     Y     Y     N     N     N     N     N     N     N\n\n'
        
        # PLANTING
        sb += '@  AUTOMATIC MANAGEMENT\n'
        sb += '@N PLANTING    PFRST PLAST PH2OL PH2OU PH2OD PSTMX PSTMN\n'
        sm_str = self.__get_obj(tr_data, 'planting', {})
        if sm_str != {}:
            pfyer = self.__get_obj(sm_str, 'pfyer', dC).split('.')[0] # remove decimal part
            pfyer = for_str(pfyer, 1, 'c', 2, zero_pad = True)
            pfday = self.__get_obj(sm_str, 'pfday', dC).split('.')[0]
            pfday = for_str(pfday, 0, 'c', 3, zero_pad = True)
            plyer = self.__get_obj(sm_str, 'plyer', dC).split('.')[0]
            plyer = for_str(plyer, 1, 'c', 2, zero_pad = True)
            plday = self.__get_obj(sm_str, 'plday', dC).split('.')[0]
            plday = for_str(plday, 0, 'c', 3, zero_pad = True)
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('PL', 1, 'c', 11, jtfy = 'l') + \
                  pfyer + pfday + \
                  plyer + plday + \
                  for_field(sm_str, 'ph2ol', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ph2ou', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ph2od', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'pstmx', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'pstmn', dC, 1, 'c', 5) + '\n'
        else:
            sb += sm + ' PL          82050 82064    40   100    30    40    10\n'
        
        # IRRIGATION
        sb += '@N IRRIGATION  IMDEP ITHRL ITHRU IROFF IMETH IRAMT IREFF\n'
        sm_str = self.__get_obj(tr_data, 'irrigation', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('IR', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'imdep', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ithrl', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ithru', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'iroff', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'imeth', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'iramt', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ireff', dC, 1, 'r', 5, ndec = 2) + '\n'
        else:
            sb += sm + ' IR             30    50   100 GS000 IR001    10  1.00\n'
        
        # NITROGEN
        sb += '@N NITROGEN    NMDEP NMTHR NAMNT NCODE NAOFF\n'
        sm_str = self.__get_obj(tr_data, 'nitrogen', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('NI', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'nmdep', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'nmthr', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'namnt', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ncode', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'naoff', dC, 1, 'c', 5) + '\n'
        else:
            sb += sm + ' NI             30    50    25 FE001 GS000\n'
        
        # RESIDUES
        sb += '@N RESIDUES    RIPCN RTIME RIDEP\n'
        sm_str = self.__get_obj(tr_data, 'residues', {})
        if sm_str != {}:
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('RE', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'ripcn', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'rtime', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'ridep', dC, 1, 'c', 5) + '\n'
        else:
            sb += sm + ' RE            100     1    20\n'
        
        # HARVEST
        sb += '@N HARVEST     HFRST HLAST HPCNP HPCNR\n'
        sm_str = self.__get_obj(tr_data, 'harvests', {})
        if sm_str != {}:
            hlyer = self.__get_obj(sm_str, 'hlyer', dC).split('.')[0] # remove decimal part
            hlyer = for_str(hlyer, 1, 'c', 2, zero_pad = True)
            hlday = self.__get_obj(sm_str, 'hlday', dC).split('.')[0]
            hlday = for_str(hlday, 0, 'c', 3, zero_pad = True)
            sb += for_str(sm, 0, 'c', 2) + \
                  for_str('HA', 1, 'c', 11, jtfy = 'l') + \
                  for_field(sm_str, 'hfrst', dC, 1, 'c', 5) + \
                  hlyer + hlday + \
                  for_field(sm_str, 'hpcnp', dC, 1, 'c', 5) + \
                  for_field(sm_str, 'hpcnr', dC, 1, 'c', 5)
        else:
            sb += sm + ' HA              0 83057   100     0'
        
        return sb

    def __write_cul_file(self, cu_arr):
        if cu_arr == []:
            return ''

        crid2name = {'MZ': 'MAIZE', 'SB': 'SOYBEAN', 'WH': 'WHEAT', 'RI': 'RICE', \
                     'SC': 'SUGARCANE', 'SG': 'SORGHUM', 'ML': 'MILLET'}

        crid = cu_arr[0]['crid']
        vars = self.cul_params[crid][: -1] # remove eco
        decs = self.cul_decs[crid][: -1]

        header_vars = ''.join(['%06s' % s.upper() for s in vars])

        c_str = '*%s CULTIVAR COEFFICIENTS: %s MODEL\n\n' % (crid2name[crid], self.cul_file.strip('.CUL'))
        c_str += '@VAR#  VRNAME.......... EXPNO   ECO#%s\n' % header_vars
        for i in range(len(cu_arr)):
            culid = 'CC' + str(i).zfill(4)
            varname = 'Generic' + str(i).zfill(4)
            c_str += culid + ' ' + varname + '          . ' + cu_arr[i]['eco']
            for j in range(len(vars)):
                c_str += for_str(cu_arr[i][vars[j]], 0, 'r', 6, 'r', decs[j])
                if j == len(vars) - 1: c_str += '\n'

        return c_str

class SOLFileOutput:  
    # member variables
    def_val = '-99'

    def __init__(self, soil_file, exp_file, use_ptransfer = True): # need experiment file to know which soil profiles to write 
        soil_data = json.load(open(soil_file))
        self.soils = soil_data['soils']
        if not len(self.soils):
            raise Exception('No soil data')
        soil_ids = [s['soil_id'] for s in self.soils]

        exp_data = json.load(open(exp_file))
        self.exps = exp_data['experiments']
        if not len(self.exps):
            raise Exception('No experiment data')
        self.soil_profiles = []        
        for i in range(len(self.exps)):

            if 'soil_id' in self.exps[i]:
                soil_id = self.exps[i]['soil_id']
                if len(soil_id) > 10 and soil_id.find('_') != -1:
                    idx = soil_id.find('_')
                    soil_id = soil_id[: idx]
            else:
                soil_id = 'XY01234567'

            if 'delta_cly' in self.exps[i]:
                delta_cly = self.exps[i]['delta_cly']
            else:
                delta_cly = '0'

            if 'delta_swc' in self.exps[i]:
                delta_swc = self.exps[i]['delta_swc']
            else:
                delta_swc = self.def_val

            soil_idx = soil_ids.index(soil_id)
            soil_profile = {'soil_id': soil_id, 'delta_cly': delta_cly, 'soil_idx': soil_idx, 'delta_swc': delta_swc}
            element_found = False
            for j in range(len(self.soil_profiles)):
                if self.soil_profiles[j] == soil_profile: element_found = True
            if not element_found: 
                self.soil_profiles.append(soil_profile)

        self.use_ptransfer = use_ptransfer

    def toSOLFile(self):
        soils = self.soils
        def_val = self.def_val

        # iterate over all profiles
        s_str = ''
        for i in range(len(self.soil_profiles)):
            soil_idx  = self.soil_profiles[i]['soil_idx']
            delta_cly = self.soil_profiles[i]['delta_cly']
            delta_swc = self.soil_profiles[i]['delta_swc']

            # get and format variables            
            soil_id = for_str('SL' + str(i + 1).zfill(8), 0, 'c', 10, jtfy = 'l')
            sl_source = for_field(soils[soil_idx], 'sl_source', def_val, 2, 'c', 11, jtfy = 'l')
            sltx = for_field(soils[soil_idx], 'sltx', def_val, 1, 'c', 5, jtfy = 'l')
            sldp = for_field(soils[soil_idx], 'sldp', def_val, 1, 'r', 5, jtfy = 'r', ndec = 0)
            soil_name = for_field(soils[soil_idx], 'soil_name', def_val, 1, 'c', 50, jtfy = 'l')
            
            sl_loc_3 = for_field(soils[soil_idx], 'sl_loc_3', def_val, 1, 'c', 11, jtfy = 'l')
            sl_loc_1 = for_field(soils[soil_idx], 'sl_loc_1', def_val, 1, 'c', 11, jtfy = 'l')
            soil_lat = for_field(soils[soil_idx], 'soil_lat', def_val, 1, 'r', 8, jtfy = 'r', ndec = 3)
            soil_long = for_field(soils[soil_idx], 'soil_long', def_val, 1, 'r', 8, jtfy = 'r', ndec = 3)
            classification = for_field(soils[soil_idx], 'classification', def_val, 1, 'c', 50, jtfy = 'l')
            
            sscol = for_field(soils[soil_idx], 'sscol', def_val, 1, 'c', 5, jtfy = 'r')
            salb  = for_field(soils[soil_idx], 'salb', def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
            slu1  = for_field(soils[soil_idx], 'slu1', def_val, 1, 'r', 5, jtfy = 'r', ndec = 0)
            sldr  = for_field(soils[soil_idx], 'sldr', def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
            slro  = for_field(soils[soil_idx], 'slro', def_val, 1, 'r', 5, jtfy = 'r', ndec = 0)
            slnf  = for_field(soils[soil_idx], 'slnf', def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
            slpf  = for_field(soils[soil_idx], 'slpf', def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
            smhb  = for_field(soils[soil_idx], 'smhb', def_val, 1, 'c', 5, jtfy = 'l')
            smpx  = for_field(soils[soil_idx], 'smpx', def_val, 1, 'c', 5, jtfy = 'l')
            smke  = for_field(soils[soil_idx], 'smke', def_val, 1, 'c', 5, jtfy = 'l')
            
            # write header
            s_str += '*' + soil_id + sl_source + sltx + sldp + soil_name + '\n'
            s_str += '@SITE        COUNTRY          LAT     LONG SCS FAMILY\n'
            s_str += sl_loc_3 + sl_loc_1 + soil_lat + soil_long + classification + '\n'
            s_str += '@ SCOM  SALB  SLU1  SLDR  SLRO  SLNF  SLPF  SMHB  SMPX  SMKE\n'
            s_str += sscol + salb + slu1 + sldr + slro + slnf + slpf + smhb + smpx + smke + '\n'
            
            soilLayer = soils[soil_idx]['soilLayer']
            
            # iterate over soil depths
            s_str += '@  SLB  SLMH  SLLL  SDUL  SSAT  SRGF  SSKS  SBDM  SLOC  SLCL  SLSI  SLCF  SLNI  SLHW  SLHB  SCEC  SADC\n'
            for j in range(len(soilLayer)):
                slcly = soilLayer[j]['slcly'] if 'slcly' in soilLayer[j] else self.def_val
                slsil = soilLayer[j]['slsil'] if 'slsil' in soilLayer[j] else self.def_val
                sloc  = soilLayer[j]['sloc']  if 'sloc'  in soilLayer[j] else self.def_val
                slcf  = soilLayer[j]['slcf']  if 'slcf'  in soilLayer[j] else self.def_val                    

                if self.use_ptransfer and slcly != self.def_val and slsil != self.def_val and \
                   sloc != self.def_val and slcf != self.def_val:
                    # use pedotransfer functions
                    slsnd = max(100. - double(slcly) - double(slsil), 0.)
                    slcly = max(double(slcly) + double(delta_cly), 0.)
                    slsil = max(100. - slsnd - slcly, 0.)
                    slcly = str(slcly)
                    slsil = str(slsil)
                    slll, sldul, slsat, sksat, slbdm = ptransfer(slcly, slsil, sloc, slcf)
                else:
                    # use values in file
                    slll  = soilLayer[j]['slll']  if 'slll'  in soilLayer[j] else self.def_val
                    sldul = soilLayer[j]['sldul'] if 'sldul' in soilLayer[j] else self.def_val
                    slsat = soilLayer[j]['slsat'] if 'slsat' in soilLayer[j] else self.def_val
                    sksat = soilLayer[j]['sksat'] if 'sksat' in soilLayer[j] else self.def_val
                    slbdm = soilLayer[j]['slbdm'] if 'slbdm' in soilLayer[j] else self.def_val
                
                # swc_adjustments
                if delta_swc != self.def_val:
                    (sldul, slll, slsat) = swc_adjustments(float(sldul), float(slll), float(slsat), float(delta_swc))

                # get and format variables
                slcly = for_str(slcly, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slsil = for_str(slsil, 1, 'r', 5, jtfy = 'r', ndec = 1)
                sloc  = for_str(sloc,  1, 'r', 5, jtfy = 'r', ndec = 2)
                slcf  = for_str(slcf,  1, 'r', 5, jtfy = 'r', ndec = 1)
                slll  = for_str(slll,  1, 'r', 5, jtfy = 'r', ndec = 3) # derived values
                sldul = for_str(sldul, 1, 'r', 5, jtfy = 'r', ndec = 3)
                slsat = for_str(slsat, 1, 'r', 5, jtfy = 'r', ndec = 3)
                sksat = for_str(sksat, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slbdm = for_str(slbdm, 1, 'r', 5, jtfy = 'r', ndec = 2)
                sllb  = for_field(soilLayer[j], 'sllb',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 0)
                slmh  = for_field(soilLayer[j], 'slmh',  def_val, 1, 'c', 5, jtfy = 'l')
                slrgf = for_field(soilLayer[j], 'slrgf', def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
                slni  = for_field(soilLayer[j], 'slni',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 2)
                slphw = for_field(soilLayer[j], 'slphw', def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slphb = for_field(soilLayer[j], 'slphb', def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slcec = for_field(soilLayer[j], 'slcec', def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                sladc = for_field(soilLayer[j], 'sladc', def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                
                
                # write first row of soil data
                s_str += sllb + slmh + slll + sldul + slsat + slrgf + sksat + slbdm + \
                    sloc + slcly + slsil + slcf + slni + slphw + slphb + slcec + sladc + '\n'
            
            s_str += '@  SLB  SLPX  SLPT  SLPO CACO3  SLAL  SLFE  SLMN  SLBS  SLPA  SLPB  SLKE  SLMG  SLNA  SLSU  SLEC  SLCA\n'
            for j in range(len(soilLayer)):
                # get and extract variables
                sllb  = for_field(soilLayer[j], 'sllb',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 0)
                slpx  = for_field(soilLayer[j], 'slpx',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slpt  = for_field(soilLayer[j], 'slpt',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slpo  = for_field(soilLayer[j], 'slpo',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                caco3 = for_field(soilLayer[j], 'caco3', def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slal  = for_field(soilLayer[j], 'slal',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slfe  = for_field(soilLayer[j], 'slfe',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)       
                slmn  = for_field(soilLayer[j], 'slmn',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slbs  = for_field(soilLayer[j], 'slbs',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slpa  = for_field(soilLayer[j], 'slpa',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slpb  = for_field(soilLayer[j], 'slpb',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slke  = for_field(soilLayer[j], 'slke',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slmg  = for_field(soilLayer[j], 'slmg',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slna  = for_field(soilLayer[j], 'slna',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slsu  = for_field(soilLayer[j], 'slsu',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)      
                slec  = for_field(soilLayer[j], 'slec',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)
                slca  = for_field(soilLayer[j], 'slca',  def_val, 1, 'r', 5, jtfy = 'r', ndec = 1)

                # write second row of soil data
                s_str += sllb + slpx + slpt + slpo + caco3 + slal + slfe + slmn + slbs + \
                         slpa + slpb + slke + slmg + slna + slsu + slec + slca

                if j != len(soilLayer) - 1: s_str += '\n'
            
            if i != len(self.soil_profiles) - 1: s_str += '\n\n'
            
        return s_str

class Jsons2Dssat(translator.Translator):
    def run(self, latidx, lonidx):
        try:
            self.log.info('Running jsons2dssat translator')
            efile   =  self.config.get_dict(self.translator_type, 'efile', default='exp.json')
            sfile   =  self.config.get_dict(self.translator_type, 'sfile', default='soil.json')
            Xfile   =  self.config.get_dict(self.translator_type, 'Xfile', default='exp.X')
            SOLfile =  self.config.get_dict(self.translator_type, 'SOLfile', default='soil.SOL')
            CULfile =  self.config.get_dict(self.translator_type, 'CULfile', default='MZCER045.CUL')
            pfcn    =  self.config.get_dict(self.translator_type, 'pfcn', default=False)
     
            # parse experiment JSON file and write out X file
            xfileoutput = DSSATXFileOutput(efile, sfile, CULfile, use_ptransfer = pfcn)
            xstr, cstr = xfileoutput.toXFile()
            open(Xfile, 'w').write(xstr)
            if cstr != '': open(CULfile, 'w').write(cstr)
            
            # parse soil JSON file and write out SOL file
            sfileoutput = SOLFileOutput(sfile, efile, use_ptransfer = pfcn)
            open(SOLfile, 'w').write(sfileoutput.toSOLFile())
            self.log.info('jsons2dssat complete')

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

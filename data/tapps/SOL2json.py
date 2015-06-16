#!/usr/bin/env python

# import modules
import json
from optparse import OptionParser

# helper functions
def findVarIdx(var_dic, line_list):
    idx_dic = {}
    for i in range(len(var_dic)): 
        key = var_dic.keys()[i]
        if key in line_list: idx_dic[key] = line_list.index(key) - 1
        # if not key in line_list:
        #     print 'SOLtojson.findVarIdx: Variable', key, 'missing . . . Filling value . . .'
        #     idx_dic[key] = -1 # variable not found
        # else:
        #     idx_dic[key] = line_list.index(key) - 1
    return idx_dic
def makeJSONDic(var_dic, idx_dic, line_list, fill_value):
    # if len(var_dic) != len(idx_dic):
    #     raise Exception('SOLtojson.makeJSONDic: Variable and index dictionaries must be same size')
    out_dic = {}
    for i in range(len(idx_dic)):
        in_var = idx_dic.keys()[i]
        out_var = var_dic[in_var]
        idx = idx_dic[in_var]
        if line_list[idx] != fill_value: out_dic[out_var] = line_list[idx] # variable exists
        # if idx != -1:
        #     out_dic[out_var] = line_list[idx] # variable exists
        # else:
        #     out_dic[out_var] = fill_value # fill value
    return out_dic

# parse inputs
parser = OptionParser()
parser.add_option("-i", "--input", dest = "inputfile", default = "Generic.SOL", type = "string",
                  help = "SOL file to parse", metavar = "FILE")
parser.add_option("-o", "--output", dest = "outputfile", default = "Generic.json", type = "string",
                  help = "JSON file to create", metavar = "FILE")
(options, args) = parser.parse_args()

# mapping between DSSAT variables and json variables
header_var_map = {'SCOM': 'sscol', 'SALB': 'salb', 'SLU1': 'slu1', 'SLDR': 'sldr', \
    'SLRO': 'slro', 'SLNF': 'slnf', 'SLPF': 'slpf', 'SMHB': 'smhb', 'SMPX': 'smpx', \
    'SMKE': 'smke'}    
row1_var_map = {'SLB': 'sllb', 'SLMH': 'slmh', 'SLLL': 'slll', 'SDUL': 'sldul', \
    'SSAT': 'slsat', 'SRGF': 'slrgf', 'SSKS': 'sksat', 'SBDM': 'slbdm', 'SLOC': 'sloc', \
    'SLCL': 'slcly', 'SLSI': 'slsil', 'SLCF': 'slcf', 'SLNI': 'slni', 'SLHW': 'slphw', \
    'SLHB': 'slphb', 'SCEC': 'slcec', 'SADC': 'sladc'}
row2_var_map = {'SLPX': 'slpx', 'SLPT': 'slpt', 'SLPO': 'slpo', 'CACO3': 'caco3', \
    'SLAL': 'slal', 'SLFE': 'slfe', 'SLMN': 'slmn', 'SLBS': 'slbs', 'SLPA': 'slpa', \
    'SLPB': 'slpb', 'SLKE': 'slke', 'SLMG': 'slmg', 'SLNA': 'slna', 'SLSU': 'slsu', \
    'SLEC': 'slec', 'SLCA': 'slca'}

# value to fill with if datum is missing
fill_value = '-99.0'

# open SOL file
lines = [l.split() for l in tuple(open(options.inputfile, 'r'))]

header_var_idx = findVarIdx(header_var_map, lines[3]) # hardcoded for 4th line
row1_var_idx = findVarIdx(row1_var_map, lines[5]) # hardcoded for 6th line
        
# calculuate number of layers and if data are stacked
num_layers = 0
stacked = False
for i in range(len(lines[6 :])):
    l = lines[6 + i]
    if not l[0] == '@': # key off first column
        num_layers += 1
    else:
        stacked = True
        row2_var_idx = findVarIdx(row2_var_map, l)
        break

# make dictionary to store data

# write preliminary
data_dic = {}
# read 1st line
data_dic['soil_id'] = lines[0][0].replace('*', '') # remove asterisk from soil id
data_dic['sl_source'] = lines[0][1]
data_dic['sltx'] = lines[0][2]
data_dic['sldp'] = lines[0][3]
# read 3rd line
data_dic['soil_name'] = ' '.join(lines[0][4 :])
data_dic['sl_loc_3'] = lines[2][0]
data_dic['sl_loc_1'] = lines[2][1]
data_dic['soil_lat'] = lines[2][2]
data_dic['soil_long'] = lines[2][3]
data_dic['classification'] = ' '.join(lines[2][4 :])

# write header variables
header_dic = makeJSONDic(header_var_map, header_var_idx, lines[4], fill_value)
data_dic.update(header_dic)

# write specific soil parameters for each layer
data_dic['soilLayer'] = [0] * num_layers
for i in range(num_layers):
    line = lines[6 + i]
    data_dic['soilLayer'][i] = makeJSONDic(row1_var_map, row1_var_idx, line, fill_value)
    if stacked:
        line2 = lines[7 + num_layers + i]
        print line2
        stacked_dic = makeJSONDic(row2_var_map, row2_var_idx, line2, fill_value)
        data_dic['soilLayer'][i].update(stacked_dic)

# save into bigger dictionary
all_data = {'soils': [data_dic]}

# save json file
json.dump(all_data, open(options.outputfile, 'w'), indent = 2, separators=(',', ': '))
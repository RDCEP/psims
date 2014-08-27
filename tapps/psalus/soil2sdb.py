#!/usr/bin/python

import json
from optparse import OptionParser

def generateHospitality(depth):
    depth = int(depth)
    shf = float(300-depth)/300
    if shf < 0:
       shf = 0
    return shf

def getValue(soil_object, element):
    try:
       return "\"" + soil_object[element] + "\""
    except KeyError:
       return "\"\""

def writeLayers(soil_out, soil_dictionary):
   for layer in soil_dict['soils'][0]['soilLayer']:
      soil_out.write("<Layer ZLYR=" + getValue(layer, 'sllb') +
                     " MH="         + getValue(layer, 'slmh') + 
                     " LL="         + getValue(layer, 'slll') + 
                     " DUL="        + getValue(layer, 'sldul') +
                     " SAT="        + getValue(layer, 'slsat') +
                     " SHF=\""      + str(generateHospitality(layer['sllb'])) + "\"" +
                     " SWCN="       + getValue(layer, 'sksat') +
                     " BD="         + getValue(layer, 'slbdm') +
                     " OC="         + getValue(layer, 'sloc') +
                     " Clay="       + getValue(layer, 'slcly') +
                     " Silt="       + getValue(layer, 'slsil') +
                     " Stones="     + getValue(layer, 'flst') +
                     " TotN="       + getValue(layer, 'slni') + 
                     " pH="         + getValue(layer, 'slphw') +
                     " pHKcl="      + getValue(layer, 'saphb') +  
                     " CEC="        + getValue(layer, 'slcec') +
                     " CaCo="       + getValue(layer, 'caco3') +
                     " KsMtrx="     + getValue(layer, 'ksmtrx') +
                     " SBioDepF="   + getValue(layer, 'sbiodepf') +
                     " TotP="       + getValue(layer, 'slpt') +
                     " P_ActIno="   + getValue(layer, 'p_actino') +
                     " P_SloIno="   + getValue(layer, 'p_sloino') +
                     " P_Labile="   + getValue(layer, 'p_labile') +
                     "/>\n"
                    )

def writeSoilInfo(soil_out, soil_dictionary):
    soil_object = soil_dictionary['soils'][0]
    soil_out.write("<Soil SoilID="  + getValue(soil_object, 'soil_id') + 
                   " SlDesc="       + getValue(soil_object, 'classification') +
		   " Slsour="       + getValue(soil_object, 'sl_source') + 
		   " Sltx="         + getValue(soil_object, 'classification') +
		   " Sldp="         + getValue(soil_object, 'sldp') +
                   " SSite="        + getValue(soil_object, 'sl_loc_3') +
		   " SCount="       + getValue(soil_object, 'sl_loc_1') + 
		   " SLat="         + getValue(soil_object, 'soil_lat') +
                   " SLong="        + getValue(soil_object, 'soil_long') +
		   " Tacon="        + getValue(soil_object, 'talcon') + 
                   " Scom="         + getValue(soil_object, 'slcom') + 
                   " Salb="         + getValue(soil_object, 'salb') + 
		   " U="            + getValue(soil_object, 'slu1') +
		   " SWCON="        + getValue(soil_object, 'sldr') + 
		   " CN2="          + getValue(soil_object, 'saro') +
                   " Slnf="         + getValue(soil_object, 'slnf') +
                   " Slpf="         + getValue(soil_object, 'slpf') +
                   " Smhb="         + getValue(soil_object, 'smhb') + 
                   " Smpx="         + getValue(soil_object, 'smpx') +
                   " Smke="         + getValue(soil_object, 'smke') +
                   " PondMax="      + getValue(soil_object, 'pondmax') +
                   ">\n"
                  )

def writeHeader(soil_out):
    soil_out.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n");
    soil_out.write("<SDB>\n");
    soil_out.write("<Soils>\n");


def writeFooter(soil_out):
    soil_out.write("</Soil>\n" +
                   "</Soils>\n" +
                   "<Version_Control>\n" +
                   "<Version Number=\"1\">\n" +
                   "<ReleaseDate>11/26/1999 0:00:00</ReleaseDate>\n" +
                   "<Notes>Initial Rel., beta v.</Notes>\n" +
                   "</Version>\n" +
                   "<Version Number=\"1.1\">\n" +
                   "<ReleaseDate>11/27/1999 0:00:00</ReleaseDate>\n" +
                   "<Notes>Testing</Notes>\n" +
                   "</Version>\n" +
                   "</Version_Control>\n" +
                   "</SDB>\n"
                  )

# Parse command line
parser = OptionParser()
parser.add_option("-i", "--input", dest="inputfile", default="soil.json", type="string",
                  help="JSON soil input", metavar="FILE")
parser.add_option("-o", "--output", dest="outputfile", default="soil.sdb.xml", type="string",
                  help="Salus sdb xml output", metavar="FILE")
(options, args) = parser.parse_args()

# Read soil info into dictionary
soil_json_file = open(options.inputfile)
soil_dict = json.load(soil_json_file)

# Write output
soil_output_file = open(options.outputfile, 'w')
writeHeader(soil_output_file)
writeSoilInfo(soil_output_file, soil_dict)
writeLayers(soil_output_file, soil_dict)
writeFooter(soil_output_file)
soil_output_file.close()

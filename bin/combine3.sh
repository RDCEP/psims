#!/bin/bash

: '
The usage is:

  ./combine3.sh [var] [input_dir] [params]

where the input arguments are as follows:

var:       Variable name
input_dir: Directory where the files are located
params:    pSIMS params file

The params file should contain:

out_file: Output file pattern

Example:
  ./combine3.sh HWAM /path/to/input params.psims
'

var=$1
input_dir=$2
params=$3

# load parameter file options
source $params

# replace colons with underscores in the variable name
var=$(echo $var | sed s/:/'_'/g)

echo Appending $var . . .

var_file=$input_dir/$out_file.$var.nc4 # write to run directory directly
agg_file=$input_dir/$out_file.$var.agg.nc4

# concatenate files
var_files=($(ls $input_dir/$out_file.$var*.nc4))
ncrcat -h ${var_files[@]} $var_file
if ls $input_dir/$out_file.$var*.agg &>/dev/null; then
  agg_files=($(ls $input_dir/$out_file.$var*.agg))
  ncrcat -h ${agg_files[@]} $agg_file
fi

# remove intermediate files
if [ -f $var_file ]; then
  rm ${var_files[@]}
fi
if [ -f $agg_file ]; then
  rm ${agg_files[@]}
fi

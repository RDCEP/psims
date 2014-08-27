#!/bin/bash

# Define the categories for params
numVariables="delta lat_zero lon_zero num_lats num_lons num_years ref_year scens"
stringVariables="long_names model out_file outtypes var_units variables"
executableVariables="executable tappcmp tappinp tappwth postprocess"
fileVariables="tar_inputs weight_file agg_file"
dirVariables="soils refdata weather work_directory"

# Read in param file
paramfile=$1
source $paramfile

# crash: Report a problem and exit
crash()
{
    MSG=$1
    echo ${MSG}  >&2
    exit 1
}

# Can be int or float
is_number() {
   re='^[-|0-9]+([.][0-9]+)?$'
   if [[ "$1" =~ $re ]] ; then
      return 1
   else
      return 0
   fi
}

# Test if file exists
is_file() {
   if [ -f "$1" ]; then
      return 1
   else
      return 0
   fi
}

# Test if directory
is_directory() {
   if [ -d "$1" ]; then
      return 1
   else
      return 0
   fi
}

# Test if executable exists
is_executable() {
   # APSIM executables get extracted at runtime, give them a pass
   if [[ $1 == *Apsim* ]]; then
      return 1
   fi

   command -v $1 >/dev/null 
   if [ "$?" == "0" ]; then
      return 1
   else
      return 0
   fi
}

# Test if empty
is_empty() {
   if [ -n "$1" ]; then
      return 1
   else
      return 0
   fi
}

# Check numeric variables
for nv in $numVariables
do
   if [ -z "${!nv}" ]; then
      continue
   fi
   is_number ${!nv}
   if [ "$?" == "0" ]; then
      crash "Parameter $nv (${!nv}) is not a number"
   fi
done

# Check string variables
for sv in $stringVariables
do
   if [ -z "${!sv}" ]; then
      continue
   fi
   is_empty ${!sv}
   if [ "$?" == "0" ]; then
      crash "Parameter $sv is undefined"
   fi
done

# Check executable variables
for ev in $executableVariables
do
   if [ -z "${!ev}" ]; then
      continue
   fi
   is_executable ${!ev}
   if [ "$?" == "0" ]; then
      crash "Unable to find executable defined in \"$ev\" parameter (${!ev}). Please verify it is avaiable in PATH"
   fi
done

# Check file variables
for fv in $fileVariables
do
   if [ -z "${!fv}" ]; then
      continue
   fi
   is_file ${!fv}
   if [ "$?" == "0" ]; then
      crash "The \"$fv\" parameter points to a non-existant file (${!fv})"
   fi
done

# Check directory variables
for dv in $directoryVariables
do
   if [ -z "${!dv}" ]; then
      continue
   fi
   is_directory ${!dv}
   if [ "$?" == "0" ]; then
      crash "Parameter \"$fv\" points to a non-existant directory (${!fv})"
   fi
done



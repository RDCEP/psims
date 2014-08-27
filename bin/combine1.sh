#!/bin/bash

: '
The usage is:

  ./combine1.sh [lat] [var] [in_dir] [out_dir] [params]

where the input arguments are as follows:

lat: Latitude band to process
var: Variable to process
in_dir: Directory where part files are located
out_dir: Directory to save output
params: Script containing the following variables:
  num_lons: Number of longitude points in spatial raster
  delta: Distance between each longitude grid cell in arcminutes
  lon_zero: Longitude of grid origin
  num_years: Number of years in netcdf files

Example:
  ./combine1.sh 047 PDAT parts var_files 720 30 31 8 -180
'

# ==============
# APPEND MISSING
# ==============
append_missing() {
  local lon1=$1
  local lon2=$2

  for ((k = $lon1; k <= $lon2; k++)); do
    if [ $k -eq $num_lons ]; then
      echo -n $blank_pt >> $out_file # no comma, no newline
    else
      echo $blank_pt", " >> $out_file # comma, newline
    fi
  done
}

# crash: report a problem and exit
crash()
{
  MSG=$1
  echo ${MSG}  >&2
  exit 1
}

# read inputs from command line
lat=$1
var=$2
in_dir=$3
out_dir=$4
params=$5

# replace colons with underscores in the variable name
var=$(echo $var | sed s/:/'_'/g)

# initialize output directories
if [ ! -d "$out_dir" ]; then
   mkdir -p $out_dir || crash "Unable to mkdir $out_dir"
fi

if [ ! -f "$params" ]; then
   crash "Unable to found params file $params"
fi

# load parameter file options
source $params

# calculate lon0 offset of grid into global grid
lon0_off=$(echo "60*($lon_zero+180)/$delta" | bc)

# create file for variable
out_file=$out_dir/$var"_"$lat".txt"
touch $out_file

# find all files in directory
files=(`find $in_dir/$lat -name \*.psims.nc | grep '[0-9]/[0-9]' | sort -V`)

# read number of scenarios from first file
num_scenarios=$(ncdump -h ${files[0]} | sed -n 's/scenario = \([0-9]\+\).*/\1/p')

# blank point
blank_pt=""
for ((i = 0; i < $(($num_years*$num_scenarios)); i++)); do
  blank_pt=$blank_pt"1e20, "
done
blank_pt=${blank_pt%??} # remove extra comma and space

# iterate over files, filling in gaps
next_lon=1
for f in ${files[@]}; do
  # get longitude index
  lon=$( basename $f | egrep -o [0-9]+ )
  lon=`echo $lon | sed 's/^0*//'` # remove leading zeros
  lon=$(($lon-$lon0_off))
  echo Processing file $f, lon $lon

  # insert missing longitudes, if necessary
  append_missing $next_lon $((lon-1))

  # dump variable
  var_dump=`ncdump -v $var $f`
  # strip header and footer
  v=`echo $var_dump | sed "s/.*$var = \(.*\); }/\1/"`
  v=${v%?} # remove extra space

  # add to file
  if [ $lon -eq $num_lons ]; then
    echo -n $v >> $out_file # no comma, no newline
  else
    echo $v", " >> $out_file # comma, newline
  fi

  # increment longitude index
  next_lon=$(($lon+1))
done

# insert missing longitudes, if necessary
append_missing $next_lon $num_lons

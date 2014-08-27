#!/bin/bash

: '
The usage is:

  ./combine2.sh [varidx] [chunk] [file_dir] [output_dir] [params]

where the input arguments are as follows:

varidx:     One-based variable index
chunk:      Chunk of data to save
file_dir:   Directory where variable ASCII files are saved
output_dir: Directory where the output will be saved
params:     pSIMS params file

The params file should contain:

var_names:   List of variable names extracted from netcdf files
long_names:  List of long descriptive names corresponding to var_names
units:       List of units corresponding to var_names
num_lons:    Number of longitude points in spatial raster
num_lats:    Number of latitude points in spatial raster
delta:       Distance(s) between each latitude/longitude grid cell in arcminutes
num_years:   Number of years in netcdf files
ref_year:    Reference year for times in netcdf files
lat_zero:    Latitude of grid origin
lon_zero:    Longitude of grid origin
out_file:    Name of output file
irr_flag:    Indicates whether scenarios are ordered in alternating order of ir, rf or rf, ir (OPTIONAL)
irr_1st:     Indicates whether ir comes first in scenario ordering (OPTIONAL)
num_chunks:  Number of chunks in scenario dimension (chunks time dimension if num_chunks > number of scenarios) (OPTIONAL)
agg:         Indicates whether to aggregate (OPTIONAL)
weight_file: Weight file for aggregation (only used if agg = true) (OPTIONAL)
agg_file:    Mask file for aggregation (only used if agg = true) (OPTIONAL)

Example:
  ./combine2.sh 1 1 /path/to/input /path/to/output params.psims
'

# ================
# CREATE BLANK CDL
# ================
create_blank_cdl() {
  local sub_var_arr=(${1})
  local sub_long_arr=(${2})
  local sub_units_arr=(${3})
  local cdl_file=$4

  # latitutde
  local num_lats=${#lat[@]}
  lat_str=$(printf ",%s" "${lat[@]}")
  lat_str=${lat_str:1}

  # longitude
  local num_lons=${#lon[@]}
  lon_str=$(printf ",%s" "${lon[@]}")
  lon_str=${lon_str:1}

  # time
  local time=($(seq $start_year $end_year))
  time=$(printf ",%s" "${time[@]}")
  time=${time:1}

  # scenario
  local scenario=($(seq $start_scen $end_scen))
  scenario=$(printf ",%s" "${scenario[@]}")
  scenario=${scenario:1}

  # variables
  local vars=""
  local i
  if [ $irr_flag = true ]; then
    dim_list="(lat, lon, time, scen, irr)"
  else
    dim_list="(lat, lon, time, scen)"
  fi
  for ((i = 0; i < ${#sub_var_arr[@]}; i++)); do
    vars=$vars"\tfloat "${sub_var_arr[i]}$dim_list" ;\n" 
    vars=$vars"\t\t"${sub_var_arr[i]}":units = "\"${sub_units_arr[i]}\"" ;\n"
    vars=$vars"\t\t"${sub_var_arr[i]}":long_name = "\"${sub_long_arr[i]}\"" ;\n"
    vars=$vars"\t\t"${sub_var_arr[i]}":_FillValue = 1.e+20f ;\n"
    vars=$vars"\t\t"${sub_var_arr[i]}":_DeflateLevel = 5 ;\n"
  done

  # data
  local data="data:\n"
  data=$data" lat = $lat_str ;\n"
  data=$data" lon = $lon_str ;\n"
  data=$data" time = $time ;\n"
  data=$data" scen = $scenario ;"
  if [ $irr_flag = true ]; then
    data=$data"\n irr = 1, 2 ;"
  fi

  # write file
  echo -e "netcdf blank {\ndimensions:" > $cdl_file
  echo -e "\tlat = UNLIMITED ;" >> $cdl_file
  echo -e "\tlon = $num_lons ;" >> $cdl_file
  echo -e "\ttime = $num_years ;" >> $cdl_file
  echo -e "\tscen = $scens ;" >> $cdl_file
  if [ $irr_flag = true ]; then
    echo -e "\tirr = 2 ;" >> $cdl_file
  fi
  echo -e "variables:" >> $cdl_file
  echo -e "\tfloat lat(lat) ;" >> $cdl_file
  echo -e "\t\tlat:units = \"degrees_north\" ;" >> $cdl_file
  echo -e "\t\tlat:long_name = \"latitude\" ;" >> $cdl_file
  echo -e "\tfloat lon(lon) ;" >> $cdl_file
  echo -e "\t\tlon:units = \"degrees_east\" ;" >> $cdl_file
  echo -e "\t\tlon:long_name = \"longitude\" ;" >> $cdl_file
  echo -e "\tint time(time) ;" >> $cdl_file
  echo -e "\t\ttime:units = \"growing seasons since "$ref_year"-01-01 00:00:00\" ;" >> $cdl_file
  echo -e "\t\ttime:long_name = \"time\" ;" >> $cdl_file
  echo -e "\tint scen(scen) ;" >> $cdl_file
  echo -e "\t\tscen:units = \"no\" ;" >> $cdl_file
  echo -e "\t\tscen:long_name = \"scenario\" ;" >> $cdl_file
  if [ $irr_flag = true ]; then
    echo -e "\tint irr(irr) ;" >> $cdl_file
    echo -e "\t\tirr:units = \"mapping\" ;" >> $cdl_file
    if [ $irr_1st == true ]; then
      echo -e "\t\tirr:long_name = \"ir, rf\" ;" >> $cdl_file 
    else
      echo -e "\t\tirr:long_name = \"rf, ir\" ;" >> $cdl_file
    fi
  fi
  echo -e "$vars" >> $cdl_file
  echo -e "$data" >> $cdl_file
}

# ==============
# APPEND MISSING
# ==============
append_missing() {
  local lat1=$1
  local lat2=$2
  for ((k = $lat1; k <= $lat2; k++)); do
    cat $blank_lat_file >> $temp_cdl_file
    if [ $k != $num_lats ]; then
      echo ", " >> $temp_cdl_file # add comma and newline
    fi
  done
}

# ================
# RANGE TO PROCESS
# ================
range2process() {
  local chunk=$1
  local num_jobs=$2
  local num_chunks=$3

  job_size=$(perl -w -e "use POSIX; print ceil($num_jobs/$num_chunks), qq{\n}") # ceiling
  si=$(echo "$job_size*($chunk-1)+1" | bc)
  if [ $chunk = $num_chunks ]; then
    ei=$num_jobs
  else
    ei=$(($si+$job_size-1))
    if (( $ei > $num_jobs )); then # check for end index out of bounds
      ei=$num_jobs
    fi
  fi

  arr=($si $ei)
  echo ${arr[@]}
}

# ===============
# EXTRACT COLUMNS
# ===============
extract_columns() {
  local in_file=$1
  local out_file=$2
  local start_idx=$3
  local end_idx=$4
  local split_dim=$5

  if [ $split_dim = time ]; then
    col1=$(($tot_scens*($start_idx-1)+1))
    col2=$(($tot_scens*$end_idx))
    colrange=($(seq $col1 $col2))
  elif [ $split_dim = scen ]; then
    colrange=()
    for ((y = 1; y <= $num_years; y++)); do
      if [ $irr_flag = true ]; then
        col1=$(($tot_scens*($y-1)+2*$start_idx-1))
        col2=$(($tot_scens*($y-1)+2*$end_idx))
      else
        col1=$(($tot_scens*($y-1)+$start_idx))
        col2=$(($tot_scens*($y-1)+$end_idx))
      fi
      colrange+=($(seq $col1 $col2))
    done
  else
    echo Unrecognized dimension to split along
    exit 0
  fi

  colrange=("${colrange[@]/#/$}") # prepend $
  colrange=$(printf "%s," "${colrange[@]}") # separate by commas
  awk "{print ${colrange%?}}" $in_file | sed '$s/,$//' >> $out_file # remove extra comma at end
}

# read inputs from command line
varidx=$1
chunk=$2
file_dir=$3
output_dir=$4
params=$5

# load parameter file options
source $params
if [ -z $irr_flag ]; then # if unset
  irr_flag=false
fi
if [ -z $irr_1st ]; then
  irr_1st=true
fi
if [ -z $num_chunks ]; then
  num_chunks=1
fi
if [ -z $agg ]; then
  agg=false
fi

# replace colons with underscores in the variable names
variables=$(echo $variables | sed s/:/'_'/g)

if [ ! -d "$output_dir" ]; then
   mkdir -p $output_dir
fi

# parse variables into array
OLD_IFS=$IFS
IFS=',' # change file separator
var_names_arr=($variables)
delta_arr=($delta)
long_names_arr=($long_names)
units_arr=($var_units)
IFS=$OLD_IFS # reset file separator

# get latitude and longitude deltas
if [[ ${#delta_arr[@]} -lt 1 || ${#delta_arr[@]} -gt 2 ]]; then
  echo Wrong number of delta values. Exiting . . .
  exit 0
fi
latdelta=${delta_arr[0]}
if [ ${#delta_arr[@]} -eq 1 ]; then
  londelta=$latdelta
else
  londelta=${delta_arr[1]}
fi

# calculate longitudes
for ((i = 1; i <= $num_lons; i++)); do
  lon[$(($i-1))]=$(echo "scale=15;$lon_zero+$londelta/60*($i-0.5)" | bc)
done

# calculate latitudes
for ((i = 1; i <= $num_lats; i++)); do
  lat[$(($i-1))]=$(echo "scale=15;$lat_zero-$latdelta/60*($i-0.5)" | bc)
done

# calculate lat0 offset of grid into global grid
lat0_off=$(echo "60*(90-$lat_zero)/$latdelta" | bc)

# calculate number of scenarios from first file
first_file=$(ls $file_dir/* | sort -n | head -1)
size_block=$(head -1 $first_file | grep -o , | wc -l)
tot_scens=$(($size_block/$num_years))

# divide number of scenarios by two if necessary
if [ $irr_flag = true ]; then
  scens=$(($tot_scens/2))
else
  scens=$tot_scens
fi

# split along dimension
if (( $num_chunks > $scens )) || [ $num_chunks = 1 ]; then
  # split along time
  jidx=($(range2process $chunk $num_years $num_chunks))
  num_years=$((${jidx[1]}-${jidx[0]}+1))
  start_scen=1; end_scen=$scens
  start_year=${jidx[0]}; end_year=${jidx[1]}
  split_dim=time
else
  # split along scenario
  jidx=($(range2process $chunk $scens $num_chunks))
  scens=$((${jidx[1]}-${jidx[0]}+1))
  start_scen=${jidx[0]}; end_scen=${jidx[1]}
  start_year=1; end_year=$num_years
  split_dim=scen
fi

# create blank point (time, scenario) grid
blank_pt=""
if [ $irr_flag = true ]; then
  num_blank_pt=$((2*$num_years*scens))
else
  num_blank_pt=$(($num_years*scens))
fi
for ((i = 0; i < $num_blank_pt; i++)); do
  blank_pt=$blank_pt"_, "
done
blank_pt=${blank_pt%??} # remove extra comma and space

# create blank latitude band file
blank_lat_file=blank_lat_file_$chunk.txt
if [ -f $blank_lat_file ]; then
  rm $blank_lat_file
fi
touch $blank_lat_file
for ((i = 1; i <= $num_lons; i++)); do
  if [ $i = $num_lons ]; then
    echo -n $blank_pt >> $blank_lat_file # no comma, no newline
  else
    echo $blank_pt", " >> $blank_lat_file # comma, newline
  fi
done

# select variable
varidx=$(($varidx-1))
var_name=${var_names_arr[$varidx]}
var_long_name=${long_names_arr[$varidx]}
var_units=${units_arr[$varidx]}
echo $var_name, $var_long_name, $var_units

# temporary cdl filename
temp_cdl_file=temp_file_$chunk.cdl

# create temporary file
create_blank_cdl $var_name $var_long_name $var_units $temp_cdl_file

# append variable
echo Appending variable $var_name . . .
echo -n " "$var_name" = " >> $temp_cdl_file

# find all files belonging to variable
files=(`ls $file_dir/* | egrep "$var_name"_[0-9]`) # match variable followed by _number

# iterate over files, filling in gaps
next_lat=1
for f in ${files[@]}; do
  # get latitude index
  grid1=`echo $f | sed "s/.*_\(.*\).txt/\1/"`
  grid1=`echo $grid1 | sed 's/^0*//'` # remove leading zeros
  grid1=$(($grid1-$lat0_off))
  echo Grid1 is $grid1

  # insert missing latitudes, if necessary
  append_missing $next_lat $((grid1-1))

  # append file
  if [ $num_chunks = 1 ]; then
    cat $f >> $temp_cdl_file
  else
    extract_columns $f $temp_cdl_file ${jidx[0]} ${jidx[1]} $split_dim
  fi
  if [ $grid1 != $num_lats ]; then
    echo ", " >> $temp_cdl_file # add comma and newline
  fi

  # increment latitude index
  next_lat=$(($grid1+1))
done

# insert missing latitudes, if necessary
append_missing $next_lat $num_lats

# add semicolon and end bracket
echo -e " ;\n}" >> $temp_cdl_file

# convert to netcdf
chunk=$(printf %03d $chunk) # pad with zeros
fn=$output_dir/$out_file.$var_name.$chunk.nc4
echo Writing output to $fn . . .
time ncgen -k4 -o $fn $temp_cdl_file

# permute dimensions to
# (scen, time, lat, lon, [irr]) if scen is split dimension or
# (time, scen, lat, lon, [irr]) if time is split dimension
ncpdq -O -h -a $split_dim,lat $fn $fn
if [ $split_dim = time ]; then
  ncpdq -O -h -a scen,lon $fn $fn
else
  ncpdq -O -h -a time,lon $fn $fn
  ncpdq -O -h -a lat,lon $fn $fn
fi

# aggregate if necessary
if [ $agg = true ]; then
  afn=$output_dir/$out_file.$var_name.$chunk.nc4.agg
  if [ $irr_flag = true ]; then
    agg.out.py -i $fn:$var_name -w $weight_file -a $agg_file -o $afn -n 4 -l $split_dim
  else
    agg.out.noirr.py -i $fn:$var_name -w $weight_file -a $agg_file -o $afn -n 4 -l $split_dim
  fi
fi

echo Done!

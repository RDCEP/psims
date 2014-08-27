#!/bin/bash

: '
The usage is:

  ./RunDSSAT.sh [cpg_dir] [lat_idx] [lon_idx]

where
  cpg_dir: Campaign directory containing Campaign.nc4, exp_template.json, and params
  lat_idx: One-based global latitude index
  lon_idx: One-based global longitude index
'

cpg_dir=$1
lat_idx=$2
lon_idx=$3

# add path to DSSAT executable
export PATH=/project/joshuaelliott/psims/bin:$PATH

# make temp directory
tmp_dir=$(mktemp -d)

# get current directory
cur_dir=$PWD

# move to temp directory
cd $tmp_dir

# copy campaign files
cp $cpg_dir/* .

# load parameters
sed -e '/^[[:space:]]*\(#.*\)*$/d' -e 's/#.*//' -e 's/  */=/' -e 's/^/export /' params > params.psims
source params.psims

# copy common files
cp $refdata/* .

# copy soil json
cp $soils/$lat_idx/$lon_idx/soil.json .

# run weather translator
echo Running weather translator . . .
time eval "$tappwth -i $weather/$lat_idx/$lon_idx/$lat_idx\_$lon_idx.psims.nc"

# run campaign translator
echo Running campaign translator . . .
time eval "$tappcamp --latidx $lat_idx --lonidx $lon_idx --ref_year $ref_year --delta $delta --nyers $scen_years --nscens $scens"

# run input translator
echo Running input translator . . .
time eval "$tappinp --latidx $lat_idx --lonidx $lon_idx --delta $delta"

# run DSSAT
echo Running DSSAT . . .
executable=$(echo $executable | sed s/:/' '/g)
time eval $executable

# move back to original directory
mv Summary.OUT $cur_dir
cd $cur_dir

# delete temp directory
rm -r $tmp_dir

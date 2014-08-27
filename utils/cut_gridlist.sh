#!/bin/bash

gridListIn=$1
gridListOut=$2
lat0=$3
lat1=$4
lon0=$5
lon1=$6
delta=$7 # arcminutes

touch $gridListOut # create file

for i in `cat $gridListIn`; do
  grid1=$(echo $i | awk -F'/' '{print $1}')
  grid2=$(echo $i | awk -F'/' '{print $2}')
  
  lat=$(echo "scale=10;90-$delta/60*($grid1-0.5)" | bc)
  if [ `echo $lat'>='$lat0 | bc` == 1 ] && [ `echo $lat'<='$lat1 | bc` == 1 ]; then
    lon=$(echo "scale=10;-180+$delta/60*($grid2-0.5)" | bc)
    if [ `echo $lon'>='$lon0 | bc` == 1 ] && [ `echo $lon'<='$lon1 | bc` == 1 ]; then
      echo $i >> $gridListOut
    fi
  fi
done

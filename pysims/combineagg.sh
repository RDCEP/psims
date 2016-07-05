#!/bin/bash

params=$1

# get parameters
out_file=$(grep ^out_file: $params | awk '{print $2}')
variables=$(grep ^variables: $params | awk '{print $2}')
cal_vars=$(grep ^cal_vars: $params | awk '{print $2}')

out_file=$out_file.agg.nc4
variables=(${variables//,/ })
cal_vars=(${cal_vars//,/ })
variables=("${variables[@]}" "${cal_vars[@]}")

file_exists=false
for var in ${variables[@]}; do 
    if ls *agg.$var* 1> /dev/null 2>&1; then
	ncrcat -h *agg.$var* tmp.nc4
        if [ $file_exists = false ]; then
            cp tmp.nc4 $out_file
            file_exists=true
        else
            ncks -h -A tmp.nc4 $out_file
        fi
        rm tmp.nc4 *agg.$var*
    fi
done

nccopy -d9 -k4 $out_file $out_file.2
mv $out_file.2 $out_file

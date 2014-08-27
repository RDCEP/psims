#!/bin/bash

: '
The usage is:

  ./timecat.sh [run_dir] [vars] [run_nos] [times_per_run] [yr0] [cat_file]
'

run_dir=$1
vars=$2
run_nos=$3
times_per_run=$4
yr0=$5
cat_file=$6

OLD_IFS=$IFS
IFS=',' # change file separator
vars_arr=($vars)
run_nos_arr=($run_nos)
IFS=$OLD_IFS # reset file separator

for i in ${run_nos_arr[@]}; do
  rn=$(printf %03d $i)
  source $run_dir/run$rn/params.psims

  nyears=$(($times_per_run*$(($i-1))))

  temp_file=run$rn.nc4
  for v in ${vars_arr[@]}; do
    var_file=$run_dir/run$rn/$out_file.$v.agg.nc4
    if [ $v = ${vars_arr[0]} ]; then
      cp $var_file $temp_file
    else
      ncks -h -A $var_file $temp_file # append
    fi
  done

  ncap2 -O -h -s "time=time+$nyears" $temp_file $temp_file
  ncatted -O -h -a units,time,m,c,"growing seasons since $yr0-01-01 00:00:00" $temp_file $temp_file
  ncpdq -O -h -a time,scen $temp_file $temp_file
  ncks -O -h --mk_rec_dim time $temp_file $temp_file

  if [ $i = ${run_nos_arr[0]} ]; then
    cp $temp_file $cat_file
  else
    ncrcat -O -h $cat_file $temp_file $cat_file # concatenate
  fi
  rm $temp_file
done

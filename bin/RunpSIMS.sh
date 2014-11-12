#!/bin/bash

if [ -z "$HOSTNAME" ]; then
   export HOSTNAME=$(hostname)
fi
echo Ran on node $HOSTNAME in working directory $PWD

# Report problem and exit
crash() {
   echo "$@" >&2
   exit 1
}

# Link file
link() {
   file=$1
   dest=$(basename $file)
   if [ ! -f $dest ]; then
      if [[ $file == *CUL ]]; then
         run_command dd if=$file of=$dest bs=1G
      else
         ln -s $file
      fi
   fi
}

# Verify a given command is available in $PATH
verify_command_in_path() {
   export COMMAND=$(echo "$@" | cut -d' ' -f1)
   command -v $COMMAND >/dev/null 2>&1
   if [ "$?" != "0" ]; then
      crash "Command $COMMAND is not available in PATH. Please add location to params file"
   fi
}

# Print timestamp before and after run
run_command() {
   command="$@"
   verify_command_in_path $command
   echo Running \"$command\" at $(date +"%T")
   START=$SECONDS
   eval $command 2>&1
   result=$?
   STOP=$SECONDS
   execution_time=$((STOP - START))
   if [ "$result" -ne 0 ]; then
      copy_failed_data
      crash "Command \"$command\" failed with an exit code of $result"
   else
      echo "Command \"$command\" succeeded at $(date +"%T"). It took $execution_time second(s)"
   fi
   if [[ "$plots" == "true" ]]; then
      command=$( echo $command | awk '{print $1}' )
      echo $execution_time >> $rundir/plots/scripts/RunpSIMS/${command}.times
   fi
   echo 
}

# Similar to run_command but redirect command output to file
run_command_redirect() {
   output=$1
   shift
   command="$@"
   verify_command_in_path $command
   echo Running \"$command\" at $(date +"%T") - redirecting the output to $output
   START=$SECONDS
   eval $command > $output 2>&1
   STOP=$SECONDS
   execution_time=$((STOP - START))
   echo "Command \"$command\" succeeded at $(date +"%T"). It took $((STOP - START)) second(s)"
   if [[ "$plots" == "true" ]]; then
      command=$( echo $command | awk '{print $1}' )
      echo $execution_time >> $rundir/plots/scripts/RunpSIMS/${command}.times
   fi
   echo
}

# Copy working directory data back to run directory
copy_failed_data() {
   if [ ! -d "$rundir" ]; then
      crash "Run directory $rundir does not exist, copy_failed_data has failed"
   fi

   failure_root="$rundir/failures"
   if [ ! -d "$failure_root" ]; then
      mkdir $failure_root || crash "Unable to create directory $failure_root"
   fi

   # We only want 10 failing data points, so use a little mutex here in case many apps are failing in parallel
   lock_dir="$failure_root/lock"
   while true; do
      if mkdir "$lock_dir"; then
         fail_count=$(find $failure_root -mindepth 2 -maxdepth 2 -type d | wc -l)
         if [ "$fail_count" -lt 10 ]; then
            fail_dir="$failure_root/$latidx/$lonidx"
            mkdir -p $fail_dir
            cp -rL * $fail_dir
         fi
         rm -rf $lock_dir
         break
      else
         sleep 1
      fi
   done
}

# Run model
run_model() {
   model=$1
   executable=$2
   rundir=$3

   if [ $model = dssat45 ] ; then # DSSAT
      run_command_redirect RESULT.OUT "$executable"
   elif [ $model = apsim75 ]; then # APSIM
      run_command tar -xzvf $rundir/../bin/Apsim75.exe.tar.gz  # expand exe & files needed to run (have correct permissions)
      mv *.xml Model/                                          # if user adds custom [crop].xml file, overwrites the default
      mv ./Model/Apsim.xml ./
      source ./paths.sh                                        # set boost and mono and ld_lib paths for the worker node
      run_command mono Model/ApsimToSim.exe Generic.apsim
      for file in *.sim; do
         run_command_redirect RESULT.out "$executable $file"
      done
   elif [ $model = cenw ]; then # CenW
      nCL=$(ls CenW[0-9+]*.CL! | wc -l)
      nPJ=$(ls CenW[0-9+]*.PJ! | wc -l)
      for cl in $(eval echo CenW{1..$nCL}.CL\!); do
         cp $cl CenW.CL!
         for pj in $(eval echo CenW{1..$nPJ}.PJ\!); do
            cp $pj CenW.PJ!
            run_command_redirect RESULT-T.OUT "$executable"
            echo "$pj with $cl" >> RESULT.OUT
            cat RESULT-T.OUT >> RESULT.OUT
            rm RESULT-T.OUT
            if [ "$cl" == "CenW1.CL!" -a "$pj" == "CenW1.PJ!" ] ; then
               head -4 CenW.DT! > CenWAll.DT!
            fi
            tail -51 CenW.DT! | head -50 >> CenWAll.DT!
            rm CenW.DT!
         done
      done
   else
      crash "Trying to run unsupported impact model"
   fi
}

latidx=$1
lonidx=$2
tar_out=$3
part_out=$4
shift 4

# Copy and link input data to Swift work directory
for file_array in "$@"; do
   for file in $file_array; do
      link /$( echo $file | sed s@^__root__/@@g )
   done
done

source params.psims
plots=${plots:-"true"}

# Set defaults
scen_years=${scen_years:-$num_years}
lon_delta=${lon_delta:-$delta}
tappopt=${tappopt:-"no_optimizer.py -e experiment.json"}

# Compute campaign scenarios as scens * num_years / scen_years
cscens=$(($scens*$scen_years/$num_years))

# Break weather directories, reference data, and deltas along commas
OLDIFS=$IFS
IFS=,
lat_delta=($delta)
lon_delta=($lon_delta)
weather=($weather)
refdata=($refdata)
IFS=$OLDIFS

# Copy weather psims files
sim_lat_delta=${lat_delta[0]}
sim_lon_delta=${lon_delta[0]}
for ((i = 0; i < ${#weather[@]}; i++)); do
   wdir=${weather[$i]}
   latd=${lat_delta[$i]}
   lond=${lon_delta[$i]}
   grid=$(trans_gidx.py $latidx $lonidx $sim_lat_delta,$sim_lon_delta $latd,$lond $wdir)
   if [ $? != 0 ]; then
      crash "Failed to translate grid indices for directory $wdir with resolution $latd, $lond"
   fi
   if [ `ls $wdir/$grid | wc -l` -gt 1 ]; then
      crash "Weather directory $wdir/$grid contains more than one pSIMS file"
   fi
   ln -s $wdir/$grid/$(ls $wdir/$grid) $(($i+1)).psims.nc
done

# Copy reference data
for data in ${refdata[@]}; do
   if [ -d $data ]; then
      for file in `ls $data`; do
         link $data/$file
      done
   elif [ -f $data ]; then
      link $data
   else
      crash "Reference data neither directory nor file"
   fi
done

# Generate experiment file from campaign file
if [ $model = cenw ] ; then
   run_command "$tappcamp --latidx $latidx --lonidx $lonidx --ref_year $ref_year \
                          --delta $sim_lat_delta,$sim_lon_delta --nyers $scen_years"
else
   run_command "$tappcamp --latidx $latidx --lonidx $lonidx --ref_year $ref_year \
                          --delta $sim_lat_delta,$sim_lon_delta --nyers $scen_years --nscens $scens"
fi

# Generate input weather file from psims file
run_command "$tappwth -i 1.psims.nc"

# Create parts directory
mkdir -p $(dirname $part_out)

term=false
while [ $term = false ]; do
   # Generate input file(s) from experiment json file
   run_command "$tappinp --latidx $latidx --lonidx $lonidx --delta $sim_lat_delta,$sim_lon_delta"

   # Run impact model
   run_model "$model" "$executable" "$rundir"

   # Extract data from output files into psims file with all variables
   run_command "$postprocess --latidx $latidx --lonidx $lonidx --ref_year $ref_year --delta $sim_lat_delta,$sim_lon_delta \
                             -y $num_years -s $cscens -v $variables -u $var_units --output $part_out"

   # Run optimizer
   run_command_redirect OPT.OUT "$tappopt -p $part_out"
   term=$(cat OPT.OUT)
done

# Tar and compress output
mkdir -p output
for file in $(ls $(echo $outtypes | sed s/,/' *'/g) 2> /dev/null); do
   ln -s $PWD/$file output/
done
run_command tar czhf output.tar.gz output
mkdir -p $(dirname $tar_out)
run_command dd if=output.tar.gz of=$tar_out bs=1G

# Throw error if debugging
shopt -s nocasematch
if [ $debug = true ]; then
   run_command /bin/false
fi

exit 0

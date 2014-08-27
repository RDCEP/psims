#!/bin/bash

echo Ran on node $( hostname ) in working directory $PWD

latidx=$1
lonidx=$2
tar_out=$3
shift 3

# Copy and link input data to Swift work directory
OLDIFS=$IFS
for file_array in "$@"; do
   for file in $file_array; do
      file=/$file
      if [[ $file == *CUL ]]; then
         dd if=$file of=$( basename $file ) bs=16M
      else
         ln -s $file
      fi
   done
done

source params.psims

# Default scen_years to num_years if scen_years is unset
if [ -z $scen_years ]; then
   scen_years=$num_years
fi

# Compute campaign scenarios as scens * num_years / scen_years
cscens=$(($scens*$scen_years/$num_years))

# Verify a given command is available in $PATH
verify_command_in_path() {
   export COMMAND=$( echo "$@" | cut -d' ' -f1 )
   command -v $COMMAND >/dev/null 2>&1 
   if [ "$?" != "0" ]; then 
      echo Command $COMMAND is not available in PATH. Please add location to params file.
      exit 1
   fi
}

# run_command - print time stamp before and after run
# Could also use 'time' here, but this is better in
# in situations where a program can hang
run_command() {
   command="$@"
   verify_command_in_path $command
   echo Running \"$command\" at $( date +"%T" )
   START=$SECONDS
   eval $command 2>&1
   result=$?
   STOP=$SECONDS
   if [ "$result" -ne 0 ]; then
      echo "Command \"$command\" failed with an exit code of $result"
      copy_failed_data
      exit 1
   else
      echo "Command succeeded at $( date +"%T" ). It tooks $((STOP - START)) second(s)"
   fi
   echo
}

# Similar to run_command, but redirect command output to a file
run_command_redirect() {
   output=$1
   shift
   command="$@"
   verify_command_in_path $command
   echo Running \"$command\" at $( date +"%T" ) - redirecting the output to $1
   START=$SECONDS
   eval $command > $output 2>&1
   STOP=$SECONDS
   echo "Completed at $( date +"%T" ). It tooks $((STOP - START)) second(s)"
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
         fail_count=$( find $failure_root -mindepth 2 -maxdepth 2 -type d | wc -l )
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

##################################################################################
# Run tappcamp application to generate the experiment file from the campaign file.
# Input campaign file called something like campaign.nc; defines the spatial experiment. 
# This file is a single netcdf file that contains arbitary number of variables 
# that must be changed spatially in the experiment files. The experiment 
# file is model agnostic and always called experiment.json. 
if [ "$model" == "cenw" ] ; then
   tappcamp="$tappcamp --latidx $latidx --lonidx $lonidx --ref_year $ref_year --delta $delta --nyers $scen_years"
else
   tappcamp="$tappcamp --latidx $latidx --lonidx $lonidx --ref_year $ref_year --delta $delta --nyers $scen_years --nscens $scens" 
fi
run_command $tappcamp

###############################################################################
# Run tappinp application to generate the input files (.XXX and .SOL for DSSAT 
# and .apsim for APSIM) from the experiment.json file
if [ "$model" == "dssat45" ] ; then suff=".SOL .MZX .RIX .WHX .SBX" ; fi
if [ "$model" == "apsim75" ] ; then suff=".apsim" ; fi
if [ "$model" == "cenw" ]    ; then suff=".PJ!" ; fi

tappinp="$tappinp --latidx $latidx --lonidx $lonidx --delta $delta"
run_command $tappinp                

###############################################################################
# Run tappwth application to generate the weather file from the .psims file
# input files usually of form latidx_lonidx.psims.nc and outputs files with 
# generic names like GENERIC.WTH (for DSSAT) and Generic.met (for APSIM). 
if [ "$model" == "dssat45" ] ; then suff=".WTH" ; fi
if [ "$model" == "apsim75" ] ; then suff=".met" ; fi
if [ "$model" == "cenw" ]    ; then suff=".CL!" ; fi
ls -l *$suff 1>&2

for file in *.psims.nc; do 
   tappwth="$tappwth -i $file" 
   run_command $tappwth                         
done

#########################################################
################# Run the impact model ##################

   ###########
   # DSSAT45 #
if [ "$model" == "dssat45" ] ; then 
   commandToRun="$executable"
   run_command_redirect RESULT.OUT $commandToRun
fi 

   ###########
   # APSIM75 #
if [ "$model" == "apsim75" ] ; then
   run_command tar -xzvf $rundir/../bin/Apsim75.exe.tar.gz  # expand exe & files needed to run (have correct permissions)
   mv *.xml Model/               # If user adds custom [crop].xml file, overwrites the default
   mv ./Model/Apsim.xml ./
   source ./paths.sh                    # Sets boost and mono and ld_lib paths for the worker node
   run_command mono Model/ApsimToSim.exe Generic.apsim
   for file in *.sim; do
      commandToRun="$executable $file"
      run_command_redirect RESULT.out $commandToRun
   done
fi

   ##########
   # CENW40 #
if [ "$model" == "cenw" ]; then
   commandToRun="$executable"
   nCL=$(ls CenW[0-9+]*.CL! | wc -l)
   nPJ=$(ls CenW[0-9+]*.PJ! | wc -l) 
   for cl in $(eval echo CenW{1..$nCL}.CL\!); do
      cp $cl CenW.CL!
      for pj in $(eval echo CenW{1..$nPJ}.PJ\!); do   
         cp $pj CenW.PJ!
         run_command_redirect RESULT-T.OUT $commandToRun
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
fi

# Tar and compress output
mkdir -p output
for file in $( ls $( echo $outtypes | sed s/,/' *'/g ) 2>/dev/null); do 
   ln -s $PWD/$file output/
done
run_command tar czhf output.tar.gz output
dd if=output.tar.gz of=$tar_out bs=16777216

#################################################################################
# Extract data from output files into a single 'psims.nc' file with all variables
if [ -n "$postprocess" ]; then
   mkdir -p parts
   mkdir -p parts/$latidx
   postprocessToRun="$postprocess --latidx $latidx --lonidx $lonidx --ref_year $ref_year --delta $delta -y $num_years -s $cscens -v $variables -u $var_units --output parts/$latidx/$lonidx.psims.nc"
   run_command $postprocessToRun
   exit_status=$?
fi

exit 0

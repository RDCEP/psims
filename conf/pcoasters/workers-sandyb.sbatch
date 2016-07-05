#!/bin/bash

#SBATCH --job-name=pcoasters
#SBATCH --nodes=1
#SBATCH --account=pi-joshuaelliott
#SBATCH --partition=sandyb
#SBATCH --time=35:49:00
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --exclusive
#SBATCH --array=0-48

export WORKER_LOGGING_LEVEL=NONE
RUNCOMMAND=$( command -v ibrun || command -v srun )
$RUNCOMMAND $WORKER $WORKERURL $( hostname ) NOLOGGING

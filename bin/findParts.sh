#!/bin/bash

workdir=$1

if [ -z "$workdir" ]; then
   echo "Usage: $0 <workdir>"
   exit 1
fi

if [ ! -d "$workdir" ]; then
   echo "Directory $workdir does not exist!"
   exit 1
fi

cd $workdir
find parts -mindepth 1 -maxdepth 1 -type d | cut -d'/' -f2

pSIMS
=====
pSIMS is a suite of tools, data, and models developed to facilitate access to
high-resolution climate impact modeling. This system largely automates the 
labor-intensive processes of creating and running data ingest and 
transformation pipelines and allows researchers to use high-performance 
computing to run simulations that extend over large spatial extents, run for 
many growing seasons, or evaluate many alternative management practices or 
other input configurations. In so doing, pSIMS dramatically reduces the time 
and technical skills required to investigate global change vulnerability, 
impacts and potential adaptations. pSIMS is designed to support integration 
and high-resolution application of any site-based climate impact model that 
can be compiled in a Unix environment (with a focus on primary production: 
agriculture, livestock, and forestry). 

For more information about pSIMS, please see the following paper:

Elliott, J., D. Kelly, J. Chryssanthacopoulos, M. Glotter, Kanika Jhunjhnuwala, N. Best, M. Wilde, and I. Foster, (2014). The Parallel System for Integrating Impact Models and Sectors (pSIMS). Environmental Modeling and Software: Special Issue on Agricultural systems modeling & software. Available online, May 22, 2014. http://dx.doi.org/10.1016/j.envsoft.2014.04.008

Dependencies
============
You need these packages installed to run pSIMS:

Package                  | Location                                       | Type 
-------                  | --------                                       | ----
APSIM                    | http://www.apsim.info/                         | Crop model
Boost                    | http://www.boost.org                           | Required to run APSIM
CenW                     | http://www.kirschbaum.id.au/Welcome\_Page.htm  | Generic forestry model
DSSAT                    | http://dssat.net                               | Crop model
Mono                     | http://www.mono-project.com                    | Required to run APSIM
nco                      | http://nco.sourceforge.net                     | Required for postprocessing 
netcdf4                  | http://www.unidata.ucar.edu/software/netcdf    | Required 
netcdf4 python libraries | http://code.google.com/p/netcdf4-python        | Required
Oracle Java 7            | http://www.oracle.com/us/downloads/index.html  | Required
Swift 0.95               | http://swiftlang.org                           | Required

Compiling the DSSAT Model
=========================
The source code for the DSSAT model is hosted in a private github repository.
To obtain access, you may request to join the DSSAT github group at 
https://github.com/DSSAT.

When you have downloaded the source code, there are a few changes that need
to be applied in order for it to compile on Linux. In the root of the DSSAT
source tree, run the following command to apply these changes:

$ patch -p1 < /psimsroot/models/pdssat/dssat46.patch (adjust path to psims as needed)

Next, compile DSSAT by running 'make'. This step requires the Intel fortran
compiler.

When compilation is completed, you will see DSSAT available as an executable 
called DSCSM046.EXE.

Compiling the APSIM model
=========================
Compiling APSIM requires the following packages be installed on your system:

* g++
* gfortran
* mono-devel
* mono-vbnc
* libboost-all-dev
* libxml2-dev
* tcl8.5-dev
* r-recommended

To obtain the source code for APSIM 7.6, run the following command:

$ svn co http://apsrunet.apsim.info/svn/apsim/tags/Apsim76

There are a few changes required in order to get APSIM compiled cleanly. To apply
these changes, run:

$ patch -p0 -i /psimsroot/models/papsim/apsim76.patch (adjust path to psims as needed)

Then finally, to compile:

$ cd Model/Build
$ ./MakeAll.sh

This will create two executables that pSIMS will use:
* Model/Apsim.exe
* Model/ApsimModel.exe

How to Run
==========
The "psims" script is used to start a pSIMS run. The options you pass to 
this script will determine which pSIMS runs will be done (including which models) 
and where they will run.

Usage: `./psims -s <sitename> -p <paramfile> -c <campaign> -g <gridlist> [ -t test_result_directory ]`

The sitename option determines where a run will take place. Currently, valid 
options are "midway" and "local". The "midway" site is the Midway cluster at 
the University of Chicago. The "local" site assumes a fairly powerful 12 core 
machine (like swift.rcc.uchicago.edu). Please do not run with local on a shared 
head node as it will completely saturate the system.

The params file defines the path to inputs, outputs, the type of model to run, and
what post processing steps need to happen.

The campaign option defines a directory that contains campaign inputs.

The gridlist is a set of latitudes and longitudes that should be processed.

The -t switch allows you to compare the results of the current run to an existing,
verified result. This is optional.

Params File Format
==================
The params file contains a set of keys and values defining the parameters of a psims
run. It defines things like the number of years to look at, the path name to climate
input files, and how to name the ouputs. Below is a list of all valid parameters and
a description of what it does.

Parameter      | Description                                                                           | Example
---------      |-----------                                                                            |-------
agg            | Indicates whether to aggregate                                                        | agg true
agg\_file      | Mask file for aggregation (only used if agg = true)                                   | agg\_file /project/joshuaelliott/psims/data/masks/agg/fips/USA\_adm\_all\_fips.nc4
debug          | Force task failure and creation of failures directory                                 | debug true
delta          | Gridcell spacing in arcminutes                                                        | delta 30
executable     | Name of executable and arguments to run for each grid                                 | executable "DSCSM045.EXE A X1234567.WHX"
lat\_zero      | Top edge of the North most grid cell in the campaign                                  | lat\_zero 90
lon\_zero      | Left edge of the West most grid cell in the campaign                                  | lon\_zero -180
long\_names    | Long names for variables, in same order that variables are listed                     | long\_names "PlantDate,AnthesisDate"
model          | Defines the type of model to run. Valid options are dssat45, apsim75, and cenw        | model dssat45
num\_lats      | Number of latitudes to be included in final nc4 file (starting with lat\_zero)        | num\_lats 360
num\_lons      | Number of longitudes to be included in final nc4 file (starting with lon\_zero)       | num\_lons 720
num\_years     | Number of years to simulate?                                                          | num\_years 31
out\_file      | Defines the prefix of the final nc4 filename (eg, $out\_file.nc4)                     | out\_file out.psims.dssat45.agmerra.wheat.demo
outtypes       | File extensions of files to include in output tar file                                | outtypes .WTH,.WHX,.SOL,.OUT,.json,.txt
PATH           | Defines the bash $PATH that will be used for run (only psims bin/ added by default)   | PATH /project/joshuaelliott/psims/tapps/pdssat:$PATH
plots          | Determines if plots will be generated after run. If undefined, defaults to true       | plots false
refdata        | Directory containing reference data. Will be copied to each simulation                | refdata /Users/davidk/psims/data/common.isimip
ref\_year      | Reference year (the first year of the simulation)                                     | ref\_year 1980
s3\_tar\_inputs| Similar to tar\_inputs, but download data from an s3 bucket. Requires s3cmd util      | s3\_tar\_inputs s3://psims/soil/hwsd200.wrld.30min.tar.gz
scens          | Number of scenarios in the campaign                                                   | scens 8
soils          | Directory containing soils                                                            | soils /Users/davidk/psims/data/soils/hwsd200.wrld.30min
tar\_inputs    | Defines a list of tar (or tar.gz) files to be extracted into your current directory   | tar\_inputs /path/myfile.tar,/path/myfile2.tar
tappcamp       | Campaign translator application and arguments                                         | tappcamp "camp2json.py -c Campaign.nc4"
tappinp        | Input translator, goes from experiment.json and soil.json to model specific files     | tappinp "jsons2dssat.py -x X1234567.WHX"
tappwth        | Weather translater, converts .psims.nc format into model specfic weather files        | tappwth "psims2WTH.py -o GENERIC1.WTH"
postprocess    | Name of program and arguments to run after running executable                         | postprocess "./OUT2psims.py -i Summary.OUT"
var\_units     | Units to use for each variable, in the same order that variables are listed           | var\_units "DOY,Days,Days,kg/ha,kg/ha,mm,mm,mm"
variables      | Define the variables to extract and format                                            | variables PDAT,ADAT,MDAT,CWAM
weather        | Defines the directory where weather data is stored                                    | weather /Users/davidk/psims/data/agmerra
weight\_file   | Weight file for aggregation (only used if agg = true)                                 | weight\_file /project/joshuaelliott/psims/data/masks/weights/mirca/maize.us.sum.nc4
work\_directory| Defines a directory to read and write intermediate data (optional)                    | work\_directory /scratch/midway/$USER/psims.workdir

If a value in your params file contains spaces, it should be quoted.

```
tappinp "jsons2dssat.py -x X1234567.MZX -s soil.json -e experiment.json -S SOIL.SOL"
```
If a value in your params file is a "special" character (as defined at http://tldp.org/LDP/abs/html/special-chars.html), it needs to be escaped by putting a '\' in front of it.

```
tappwth          "psims2WTH.py -o \"GENERIC1.WTH\" -v tasmin,tasmax,rsds,pr,wind"
```

Obtaining Datasets
==================
We have made two full global datasets available to pSIMS users:

* AgMERRA Climate Forcing Dataset for Agricultural Modeling
* Harmonized World Soil Database

Due to the size of these datasets, they are available only via Globus online.
If you do not already have a Globus account, you may create one at globus.org.
The endpoint name is *davidk#psims*. Harmonized World Soil Database 
files are available in the */soils/hwsd200.wrld.30min* directory. AgMERRA 
climate data is available in the */clim/ggcmi/agmerra directory*.

Testing results
===============
The -t option allows you to compare the result of your current run to a known good result. The result directory
should contain a file called test.txt. The test.txt file contains a list of files and their md5 checksums. Here is an example
of a test.txt file:

    parts/200/227.psims.nc 8344c87c173f428b134f61d7abc3f485   
    parts/200/228.psims.nc 1ecde2bf35ee7b8b39177c6e6cf0aea2   

The actual test output files are not needed - the only file that gets read from the test directory is the test.txt file.

Gridlist Format
===============
A gridlist file contains a list of latitudes and longitudes to be processed, in the format of "lat/lon". Here is an example:

    104/114  
    104/115  
    104/116  

The latitude/longitude format is also appended to the weather and soils variables to determine the pathname to input 
files for a specific grid point. For example, suppose weather is set to /Users/davidk/psims/data/agmerra. For grid 
104/114, psims will include all files in the path: /Users/davidk/psims/data/agmerra/104/114/\*.

It is important then, that for data exists in the soils and weather directory for each grid point. Missing data will 
result in errors.

Output Files
============
The output/ directory contains a directory for each latitude being processed. Within each latitude directory,
a tar.gz file exists for each longitude. For example, if your gridList contained a grid 100/546, you would see an
output file called runNNN/output/100/546output.tar.gz. This file is generated from within the Swift work directory.
Which files get included in the file is determined by how you set "outtypes" in your parameter file.

The parts/ directory contains the output nc files for each grid being processed. When grid 100/546 is done processing,
you will see a file called runNNN/parts/100/546.psims.nc.

The combined nc file is saved in the runNNN directory. Its name depends on the value of "out\_file" in your
params file. If you set out\_file to "out.psims.apsim75.cfsr.whea", the final combined nc file would be called "out.psims.apsim75.cfsr.whea.nc4".

At the end of each run, a plot is generated in the run directory called activitylot.png. It shows the number of active jobs over time, and the amount
of time spent staging in and out files to the work directories.

How to Modify Swift Configuration
=================================
Determining how Swift runs is controlled by a file called conf/swift.properties. This file defines the
scheduler to use, the location of work and scratch directories, and the amount of parallelism.

Debugging
=========
When problems occur, there are a few places to look to get answers about why the problems are occuring. The first is the standard output of
Swift. You will see this info on your screen as psims is running. Since there are many tasks running at once, it may scroll by your screen
too quickly. This output will also be recorded in runNNN/swift.out.

Another place to look is the runNNN/\*.d directory. An info log file should exist in that directory for each failing task. The info file contains
the stdout and stderr output of RunpSIMS.sh. Each significant command should be logged with a timestamp so you can track the progress and get a
better idea of what's happening.

When a task fails, a failures directory gets created. The structure is failures/<lat>/<lon>. The data contained in that directory is a copy of
the work directory at the point of failure. Only data from the first 10 failing tasks will be contained in this directory.

If you would like a copy of the input data for grids not contained in the failures directory, you can use the "griddata" command. 

    $ bin/griddata -p paramfile -lat lat -lon lon

When griddata runs, a randomly named directory will be created in your current directory that contains the relevant data.

Rerunning and Restarting failed runs
====================================
There may be times when a psims run fails. Failures may be caused by problems with the data, the hardware, or with any of
the intermediate programs involved. From within the runNNN directory, you may run any of the following scripts

    $ ./resume.parts.sh     # Continue from where a failed run stopped (part generation)
    $ ./rerun.parts.sh      # Rerun all tasks (part generation)
    $ ./resume.combine.sh   # Continue from where a failed run stopped (combine)
    $ ./rerun.combine.sh    # Rerun all tasks (combine)

Running on the Midway cluster
=============================
Midway is a cluster at the University of Chicago. More information about Midway can be found at http://rcc.uchicago.edu/resources/midway\_specs.html.

To run pSIMS on midway, the first thing you need to do is load the required modules.

    $ module load java ant git mono/2.10 hdf5/1.8 nco/4.3 boost/1.50 netcdf/4.2 jasper python/2.7 cdo/1.6 tcllib/1.15 swift/0.95-RC5

The conf/midway.xml file is configured to use the sandyb slurm partition. The sandyb partition has 16 cores per node. The default configuration
is to request nodes in chunks of 3, up to the Midway limit of 1536 total cores.

Start jobs in /project/joshuaelliott/psims. The faster /scratch/midway and /scratch/local disks will be used automatically by Swift to speed things up and decrease
the load on the project filesystem.

Test data exists in the /project/joshuaelliott filesystem. You can run the following commands to test running the apsim, dssat, and cenw:

    $ ./psims -s midway -g /project/joshuaelliott/testing/psims/acceptance/gridlists/dssat45.100 -p /project/joshuaelliott/testing/psims/acceptance/params/dssat45 -c /project/joshuaelliott/testing/psims/acceptance/data/campaign/isi1.mai -t /project/joshuaelliott/testing/psims/acceptance/results/dssat45

    $ ./psims -s midway -g /project/joshuaelliott/testing/psims/acceptance/gridlists/apsim75.100 -p /project/joshuaelliott/testing/psims/acceptance/params/apsim75 -c /project/joshuaelliott/testing/psims/acceptance/data/campaign/ggcmi.whe -t /project/joshuaelliott/testing/psims/acceptance/results/apsim75

    $ ./psims -s midway -g /project/joshuaelliott/testing/psims/acceptance/gridlists/cenw.100 -p /project/joshuaelliott/testing/psims/acceptance/params/cenw -c /project/joshuaelliott/testing/psims/acceptance/data/campaign/pcenw -t /project/joshuaelliott/testing/psims/acceptance/results/cenw

pSIMS Overview
==============
pSIMS is a suite of tools, data, and models developed to facilitate access to high-resolution climate impact modeling. This system largely automates the labor-intensive processes of creating and running data ingest and transformation pipelines and allows researchers to use high-performance computing to run simulations that extend over large spatial extents, run for many growing seasons, or evaluate many alternative management practices or other input configurations. In so doing, pSIMS dramatically reduces the time and technical skills required to investigate global change vulnerability, impacts and potential adaptations. pSIMS is designed to support integration and high-resolution application of any site-based climate impact model that can be compiled in a Unix environment (with a focus on primary production: agriculture, livestock, and forestry).

For more information about pSIMS, please see the following paper:

Elliott, J., D. Kelly, J. Chryssanthacopoulos, M. Glotter, Kanika Jhunjhnuwala, N. Best, M. Wilde, and I. Foster, (2014). The Parallel System for Integrating Impact Models and Sectors (pSIMS). Environmental Modeling and Software: Special Issue on Agricultural systems modeling & software. Available online, May 22, 2014. http://dx.doi.org/10.1016/j.envsoft.2014.04.008

Software Dependencies
=====================
Package                  | Location                                       | Type
-------                  | --------                                       | ----
APSIM                    | https://www.apsim.info                         | Crop model
Boost                    | http://www.boost.org                           | Required to run APSIM
CenW                     | http://www.kirschbaum.id.au/Welcome_Page.htm   | Generic forestry model
DSSAT                    | http://dssat.net                               | Crop model
Mono                     | http://www.mono-project.com                    | Required to run APSIM
nco 4.4.3                | http://nco.sourceforge.net                     | Required for postprocessing
netcdf4                  | https://www.unidata.ucar.edu/software/netcdf/  | Required
netcdf4 python libraries | https://github.com/Unidata/netcdf4-python      | Required
Oracle Java 7            | http://www.oracle.com/us/downloads/index.html  | Required
Swift 0.95               | http://swift-lang.org                          | Required

In addition to installing these packages, there are also a number of python modules that must be installed. These are defined in pysims/requirements.txt. To install these packages in an automated way, run the command "pip install -r requirements.txt" within a Python virtual environment. For more information on Python virtual environments, please see http://docs.python-guide.org/en/latest/dev/virtualenvs.

Single Tile Simulation
=======================
Simulating a single tile is useful for testing purposes. It allows you to verify that your parameters are set correctly and to verify the simulation results looks reasonable. Create a new directory and change the The command for running a single point simulation is:

Usage: `pysims.py --campaign <campaign_dir> --param <param_file> --tlatidx <tile_latitude_index> --tlonidx <tile_longitude_index> [ --latidx <point_latitude_index> --lonidx <point_longitude_index> ]`

If a point latidx and lonidx is specified, only a single point will be simulated rather than all points in the tile.

Multi-Tile Simulation
======================
In most cases you'll want to simulate a group of tiles. Since this can be computationally expensive, this type of simulation will typically be done on a cluster or supercomputer. To accomplish this, pSIMS uses the Swift parallel scripting language. The "psims" script is a shell script used to start the simulations.

Usage: `./psims -s <sitename> -p <paramfile> -c <campaign> -t <tile_list> [ -split n ]`

The sitename option determines where a run will take place. Currently, valid
options are "sandyb", "westmere", and "local". The sandyb and westmere sites are for use on the Midway cluster at the University of Chicago. The "local" site assumes a 12 core machine. This can be tweaked by editing conf/swift.properties.

The params file defines the path to inputs, outputs, the type of model to run, and
what post processing steps need to happen.

The campaign option defines a directory that contains input file specific to a campaign.

The gridlist is a set of latitude and longitude indexes that should be processed.

The -split option may be used to break up the simulation in smaller chunks. For example, a split of 2 will run a single tile across four different nodes. This can be useful for very dense tiles.

The parameter file
==================
The parameter file is a YAML-formatted file containing all the parameters of a psims
run. It defines things like the number of simulation years, the path to climate input files,
and which model to use. Below is a list of parameters and a description of what it does.

Parameter      | Description
---------      |------------
aggregator     | Aggregator options, used to average a variable across a region
checker        | Checker translator and options, check if a tile should be simulated or not
delta          | Simulation delta, gridcell spacing in arcminutes
executable     | Name of executable and arguments to run for each grid
lat\_zero      | Top edge of the North most grid cell in the campaign
lon\_zero      | Left edge of the West most grid cell in the campaign
long\_names    | Long names for variables, in same order that variables are listed
model          | Defines the type of model to run. Valid options are dssat45, dssat46, apsim75
num\_lats      | Number of latitudes to be included in final nc4 file (starting with lat\_zero)
num\_lons      | Number of longitudes to be included in final nc4 file (starting with lon\_zero)
num\_years     | Number of years to simulate
out\_file      | Defines the prefix of the final nc4 filename
outtypes       | File extensions of files to include in output tar file
refdata        | Directory containing reference data. Will be copied to each simulation
ref\_year      | Reference year (the first year of the simulation)
scens          | Number of scenarios in the campaign
soils          | Directory containing soils
tappcmp        | Campaign translator and options
tappinp        | Input translator and options, goes from experiment.json and soil.json to model specific files
tapptilewth    | Weather tile translator and options
tapptilesoil   | Soil tile translator and options
tappnooutput   | The "no output" translator and options, typically used to create empty data
tappwth        | Weather translator and options, converts .psims.nc format into model specfic weather files
tdelta         | Tile delta gridcell spacing in arcminutes
postprocess    | Name of translator and options to run after running executable
var\_units     | Units to use for each variable, in the same order that variables are listed
variables      | Define the variables to extract to final outputs
weather        | Defines the directory where weather data is stored

Campaign Files
==============
When pysims is run, the user must specify a campaign directory with the --campaign parameter. Typically this campaign directory contains two relevant files named Campaign.nc4 and exp_template.json. These files are used by the jsons2dssat and jsons2apsim translators to create experiment files for the crop model.

The exp_template.json file contains key-value pairs for data that will be written to the experiment file. These values represent things like fertilizer amounts, irrigation settings, and planting dates. Static settings for the experiment are stored in exp_template.json. Values that vary by lat, lon, scenario, or time get stored in Campaign.nc4.

Here is an example of irrigation definitions in exp_template.json.
~~~
  "dssat_simulation_control": {
    "data": [
        "irrigation": {
          "ithru": "100",
          "iroff": "GS000",
          "imeth": "IR001",
          "imdep": "40",
          "ireff": "1.0",
          "iramt": "10",
          "ithrl": "80"
        },...
~~~

But users may not want to these irrigation settings everywhere. If they have a collection of irrigation amounts (iramt) that change by location, users may create a variable in Campaign.nc4 called iramt. The most basic version of this would be a NetCDF variable in the format of float iramt(lat, lon). When pysims runs for a given point, the appropriate value would transfer from Campaign.nc4 into the experiment file. If iramt is not defined in Campaign.nc4, the static value from exp_template.json is used instead.

There may be situations where users want to have multiple irrigation amounts defined in your exp_template.json. In this case having an iramt variable in Campaign.nc4 variable is ambiguous because you're not sure which irrigation amount it corresponds to. In these cases pysims uses a numbering system in the Campaign.nc4 variable names. The variable iramt_1 corresponds to the first instance of iramt in exp_template.json. iramt_2 corresponds to the second instance, and so on. This process works the same for all variables, not just limited to iramt.

Aggregation
===========
The aggregation script is responsible for taking the final output of a psims simulation and computing the average value for a variable across some geographic region. To enable aggregation, add a section named 'aggregator' to your parameters file with the following parameters:

Parameter | Description
-----     | -----------
aggfile   | Location of an aggfile. The aggfile contains information about geographic boundries at given lats/lons. Common uses here are gadm regions and food producing units.
weightfile| Location of the weightfile, used to give certain geographic areas more weight than others
levels    | Comma separated list of levels from the aggfile (example: gadm0, gadm1, gadm2)

The aggfile and weightfile must match the resolution used in your simulation. To generate a new aggfile you can use the gdal_rasterize utility to convert from a gadm shapefile to a netcdf file, then use bin/create_agg_limits.py to add the required variables and dimensions.

Example parameters:
~~~
aggregator:
    aggfile: /path/to/agg.nc
    weightfile: /path/to/weight.nc
    levels: gadm0
~~~

Obtaining Data
==============
We have made two full global datasets available to pSIMS users:

AgMERRA Climate Forcing Dataset for Agricultural Modeling

Harmonized World Soil Database

Due to the size of these datasets, they are available only via Globus online. If you do not already have a Globus account, you may create one at globus.org. The endpoint name is davidk#psims. Harmonized World Soil Database files are available in the /soils/hwsd200.wrld.30min directory. AgMERRA climate data is available in the /clim/ggcmi/agmerra directory.

Tilelists
=========
A tilelist file contains a list of latitudes and longitudes indexes to be processed, in the format of "latidx/lonidx". Here is an example:

0024/0044

0024/0045

Output Files
============
The output/ directory contains a directory for each latitude being processed. Within each latitude directory, a tar.gz file exists for each longitude. For example, if your gridList contained a grid 100/546, you would see an output file called runNNN/output/100/546output.tar.gz. This file is generated from within the Swift work directory. Which files get included in the file is determined by how you set "outtypes" in your parameter file.

The parts/ directory contains the output NetCDF files for each grid being processed. When grid 0024/0044 is done processing, you will see a file called runNNN/parts/0024/546.psims.nc.

The combined nc file is saved in the runNNN directory. Its name depends on the value of "out_file" in your params file. If you set out_file to "out.psims.apsim75.cfsr.whea", the final combined nc file would be called "out.psims.apsim75.cfsr.whea.nc4".

Rerunning and Restarting Failed Runs
====================================
There may be times when a psims run fails. Failures may be caused by problems with the data, the hardware, or with any of the intermediate programs involved. From within the runNNN directory, you may run any of the following scripts

	$ ./resume.parts.sh       # Continue part generation from where a failed run has stopped
	$ ./rerun.parts.sh        # Rerun all part generation tasks
	$ ./resume.combinelon.sh  # Continue combinelon from where a failed run has stopped
	$ ./rerun.combinelon.sh   # Rerun all combinelon tasks
	$ ./resume.combinelat.sh  # Continue combinelat from where a failed run has stopped
	$ ./rerun.combinelat.sh   # Rerun all combinelat tasks
	$ ./resume.aggregate.sh   # Continue aggregation from where a failed run has stopped
	$ ./rerun.aggregate.sh    # Rerun all aggregation tasks

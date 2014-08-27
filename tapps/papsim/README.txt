The Python translator "jsons2apsim" accepts three inputs: A soil JSON file, an experiment JSON file, and a template APSIM file.

The usage of "jsons2apsim" is as follows.

./jsons2apsim.py -s <soil>.json -e <experiment>.json -t <template>.apsim -o <output>.apsim

There are two experiment files corresponding to two crops, experiment_millet.apsim and experiment_maize.apsim, and one soil file, soil.json. The experiment files have two simulations each in them---one corresponding to automatic irrigation, one without. The Millet experiment file uses the "bj104" cultivar located in Millet.xml, the Maize experiment file, the "Pioneer_3153" cultivar located in Maize.xml.

The experiment files specify such things as the name of the crop, start and end dates of the simulation, reporting frequency, output variables, initial conditions, weather file, planting parameters, fertilizer parameters, and irrigation parameters, as well as any log messages.

To generate the APSIM file for millet, type:

./jsons2apsim.py -s soil.json -e experiment_millet.json -t template.apsim -o Generic_millet.apsim

Similarly, for maize:

./jsons2apsim.py -s soil.json -e experiment_maize.json -t template.apsim -o Generic_maize.apsim

These files can be copied to the APSIM 7.5 test directory (/project/joshuaelliott/psims/models/papsim75/test/Generic) to run the simulation. Simply type, from within the APSIM 7.5 test directory:

mono ../Model/ApsimToSim.exe Generic_millet.apsim # or Generic_maize.apsim

This will create two .sim files (Generic.sim and Generic1.sim), corresponding to the two simulations within the APSIM file. APSIM can be run on each .sim separately:

mono ../Model/Apsim.exe Generic.sim
mono ../Model/Apsim.exe Generic1.sim

The first command produces the output file Generic.out and the log file Generic.sum, the second command, Generic1.out and Generic1.sum. These represent the file APSIM output to be parsed.
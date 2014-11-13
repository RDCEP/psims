#!/usr/bin/env python

# add paths
import os, sys
for p in os.environ['PATH'].split(':'): sys.path.append(p)

# import modules
from optimizer import Optimizer
from optparse import OptionParser

class NoOptimizer(Optimizer):
    def __init__(self):
        super(NoOptimizer, self).__init__()
    def objective(self):      return 0
    def terminate(self, obj): return True
    def update(self, obj):    return 0
    def write(self, p):       return

# parse inputs
parser = OptionParser()
parser.add_option("-p", "--partsfile", dest = "partsfile", default = "parts.psims.nc", type = "string", 
                  help = "Parts file", metavar = "FILE")
parser.add_option("-e", "--expfile", dest = "expfile", default = "experiment.json", type = "string",
                  help = "Experiment file", metavar = "FILE")
options, args = parser.parse_args()

optimizer = NoOptimizer()

# compute objective
obj = optimizer.objective()

# determine whether to terminate
stop = optimizer.terminate(obj)

# update parameter vector if necessary
p = optimizer.update(obj) if not stop else None

# write new parts, experiment, and history files
optimizer.write(p)

# return termination indicator
exit(str(stop).lower())
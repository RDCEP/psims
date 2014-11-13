#!/usr/bin/env python

import sys,os,operator

# Human parsable seconds
def hsec(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return "%dh%dm" % (hours, minutes)
    elif minutes > 0:
        return "%dm%ds" % (minutes, seconds)
    else:
       return "%ds" % (seconds)

class Summary:
    prog = ''
    tsum = ''
    count = ''
    minimum = ''
    maximum = ''
    average = ''

summaries = {}
totalTime = 0

for filename in os.listdir(sys.argv[1]):
    file = open(os.path.join(sys.argv[1], filename), 'r')
    data = [int(line) for line in file]
    s = Summary()
    s.prog     = os.path.basename(filename).replace(".times", "")
    s.tsum     = sum(data)
    totalTime += s.tsum
    s.count    = len(data)
    s.minimum  = min(data)
    s.maximum  = max(data)
    s.average  = sum(data)/len(data)
    s.tsum     = sum(data)
    summaries[s.prog] = s

for s in sorted(summaries.values(), key=operator.attrgetter('tsum'), reverse=True):  
    print "%s: total=%s avg=%s min=%s max=%s count=%s" % ( s.prog.rjust(15),
                                                           hsec(s.tsum).ljust(15),
                                                           hsec(s.average).ljust(10), 
                                                           hsec(s.minimum).ljust(10),
                                                           hsec(s.maximum).ljust(10), 
                                                           str(s.count).ljust(10))

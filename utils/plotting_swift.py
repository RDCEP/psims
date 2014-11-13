#!/usr/bin/env python
#
# Print info about average task durations by parsing a Swift log
#

import sys
import os
import operator
from datetime import datetime

# Command line arguments
if len(sys.argv) != 2:
    sys.exit("Usage: %s <log>" % sys.argv[0])

# Open log file
log_file = open(sys.argv[1], "r")

# Class definition for a single Task
class Task:
    startTime  = ''
    stopTime   = ''
    taskNumber = ''

# Dictionary containing all tasks
tasks = {}

# Retrieve Task from dictionary, or create new
def getTask(taskid):
    if taskid in tasks:
        return tasks[taskid]
    else:
        t = Task()
        tasks[taskid] = t
        return tasks[taskid]

# In a log entry, find values that start with value=<nnn>
def getValue(entry, value):
    entry_array = entry.split()
    value += '='
    for word in entry_array:
        if word.startswith(value):
            return word.split(value, 1)[1]

# Get timestamp of a log entry
def getTime(entry):
   timestamp = entry.split()[1]
   return timestamp.split(',')[0]

# Difference between HH:MM:SS values
def HHMMSS_diff(hhmmss1, hhmmss2):
   FMT = '%H:%M:%S'
   return (datetime.strptime(hhmmss1, FMT) - datetime.strptime(hhmmss2, FMT)).seconds

# Human readable seconds
def hsec(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return "%dh%dm" % (hours, minutes)
    elif minutes > 0:
        return "%dm%ds" % (minutes, seconds)
    else:
       return "%ds" % (seconds)

# Parse log
for line in iter(log_file):

    if 'JOB_START' in line:
        taskid          = getValue(line, "jobid")
        task            = getTask(taskid)
        task.startTime  = getTime(line)

    elif 'JOB_END' in line:
        taskid        = getValue(line, "jobid")
        task          = getTask(taskid)
        task.stopTime = getTime(line)

# Create an array containing task run times
seconds_list = []
for t in tasks.values():
   seconds = HHMMSS_diff(t.stopTime, t.startTime)
   seconds_list.append(seconds)

count = len(seconds_list)
ssum  = sum(seconds_list)
savg  = ssum / count
smin  = min(seconds_list)
smax  = max(seconds_list)

print "%s: total=%s avg=%s min=%s max=%s count=%s" % ( 'Swift tasks'.rjust(15),
                                                       hsec(ssum).ljust(15),
                                                       hsec(savg).ljust(10),
                                                       hsec(smin).ljust(10),
                                                       hsec(smax).ljust(10),
                                                       str(count).ljust(10))

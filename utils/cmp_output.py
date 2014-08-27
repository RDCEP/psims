#!/usr/bin/python

import os
import sys
import hashlib

# Given a filename, generate md5 sum
def md5sum(filename, blocksize=1048576):
    hash = hashlib.md5()
    with open(filename, "r+b") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            hash.update(block)
    return hash.hexdigest()

# Command line arguments
if len(sys.argv) != 3:
    sys.exit("Usage: %s <run_directory> <test_directory>" % sys.argv[0])

run_dir  = os.path.normpath(sys.argv[1])
test_dir = os.path.normpath(sys.argv[2])

# Dictionary containing md5 checksums
test_sums={}

# Read test_dir/test.txt and store values in dict
testlist = open(os.path.join(test_dir, "test.txt"), "r")
for line in iter(testlist):
    [filename, checksum] = line.split()
    test_sums[filename] = checksum;

# Compare files in test.txt
ec = 0
for fn, checksum in test_sums.iteritems():
    fn = fn.rstrip()
    run_file_path = os.path.abspath(os.path.join(run_dir, fn))

    if not os.path.isfile(run_file_path):
        print "File %s was not created in run directory" % fn  
        ec = 1
        continue

    run_file_sum = md5sum(run_file_path)

    if test_sums[fn] != run_file_sum:
        print "File %s generated an incorrect checksum" % fn
        ec = 1

sys.exit(ec)

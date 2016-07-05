from model import Model
from subprocess import Popen, PIPE
import os
import sys

class Dssat45(Model):

    def run(self, latidx, lonidx):
        try:

            """Run model with given command line string"""
            print "Running DSSAT for point %04d/%04d" % (latidx, lonidx)
            cmd = self.config.get('executable')
            rc = -1
            try:
                p = Popen(cmd.split(), stdout=PIPE)
                stdout, stderr = p.communicate()
                stdout_file = open('RESULT.OUT', 'w')
                stdout_file.write(stdout)
                rc = p.returncode
            except Exception as e:
                print "Unable to run DSSAT45: %s" % e

            if rc != 0:
                return False
            print "DSSAT completed for point %04d/%04d" % (latidx, lonidx)
            return True

        except Exception as e:
            print "[%s]: %s" % (os.path.basename(__file__), e)
            return False

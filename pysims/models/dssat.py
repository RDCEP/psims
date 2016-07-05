from model import Model
from subprocess import Popen, PIPE
import glob
import os
import sys
import traceback

class Dssat(Model):

    def run(self, latidx, lonidx):
        try:
            cmd = self.config.get('executable')
            p = Popen(cmd.split(), stdout=PIPE)
            stdout, stderr = p.communicate()
            stdout_file = open('RESULT.OUT', 'w')
            stdout_file.write(stdout)
            stdout_file.close()

            if p.returncode != 0:
                return False
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

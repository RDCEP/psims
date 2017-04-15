import glob
import os
import shutil
import sys
import tarfile
import traceback
from model import Model
from subprocess import Popen, PIPE

class Apsim75(Model):

    def run(self, latidx, lonidx):
        try:
            apsim_bin = self.config.get('executable')

            # The apsim 'executable' is a gzipped tarball that needs to be extracted into the current working directory
            tar = tarfile.open(apsim_bin)
            tar.extractall()
            tar.close()
            model_dir = 'Model'
 
            for xml_file in glob.glob('*.xml'):
                if os.path.basename(xml_file) == 'Apsim.xml':
                    continue

                old_xml = '%s/%s' % (model_dir, os.path.basename(xml_file))
                if os.path.isfile(old_xml):
                    os.remove(old_xml)

                if os.path.islink(xml_file):
                    link = os.readlink(xml_file)
                    shutil.copy(link, model_dir)
                else:                    
                    shutil.copy(xml_file, model_dir)

            # Create sim files
            p = Popen('source paths.sh ; mono Model/ApsimToSim.exe Generic.apsim', shell=True, executable='/bin/bash', stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            stdout_file = open('RESULT.OUT', 'w')
            stdout_file.write(stdout)
            if p.returncode != 0:
                rc = p.returncode

            # Run apsim for each sim file
            for sim in glob.glob('*.sim'):
                p = Popen('source paths.sh ; Model/ApsimModel.exe %s' % sim, shell=True, executable='/bin/bash', stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                stdout_file.write(stdout)
                if p.returncode != 0:
                    rc = p.returncode
            stdout_file.close()
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

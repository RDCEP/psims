#!/usr/bin/env python
import errno
import glob
import os
import shutil
import traceback
from .. import translator

class StageOutputsSharedFS(translator.Translator):

    # Simulate mkdir -p (no errors if a directory already exists)
    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else: raise

    # Staging per point
    def run(self, latidx, lonidx):
        try:
            return True
        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

    # Staging per tile
    def run_tile(self, tlatidx, tlonidx):
        try:
            rundir           = self.config.get('rundir')
            if not rundir:
                return True
            split            = int(self.config.get('split'))
            tlatidx          = int(self.config.get('tlatidx'))
            slatidx          = int(self.config.get('slatidx'))
            tslatidx         = split * (tlatidx - 1) + slatidx
            part_directory   = os.path.join(rundir, 'parts', '%04d' % tslatidx)
            output_directory = os.path.join(rundir, 'outputs')

            self.mkdir_p(part_directory)
            self.mkdir_p(output_directory)

            # Create list of files to stage out
            expressions = [os.path.join('parts', '%04d' % tslatidx, "output*.psims.nc"),
                           os.path.join('parts', '%04d' % tslatidx, "daily*.psims.nc")]
            files_to_copy = []
            for exp in expressions:
                files_to_copy.extend(glob.glob(exp))

            for ftc in files_to_copy:
                shutil.copy(ftc, part_directory)

            tar_filenames = glob.glob(os.path.join('outputs', '*.tar'))
            for tar_file in tar_filenames:
                shutil.copy(tar_file, output_directory)

            return True
        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

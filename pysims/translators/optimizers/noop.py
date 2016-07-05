from .. import translator
import os
import traceback

# parse inputs
class Noop(translator.Translator):

    def run(self, latidx, lonidx):
        try:
            opt_file = open('OPT.OUT', 'w')
            opt_file.write('true')
            opt_file.close()
            return True

        except:
            print "[%s]: %s" % (os.path.basename(__file__), traceback.format_exc())
            return False

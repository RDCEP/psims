import os
import sys
import yaml

class YAMLConfiguration:

    def __init__(self, filename):
        
        try:
            self._config = yaml.safe_load(open(filename, "r"))
        except Exception as e:
            print "[%s]: %s" % (os.path.basename(__file__), e)
            sys.exit(-1)

    def get(self, property, default=None):
        try:
            return self._config[property]
        except:
            return default

    def get_dict(self, property, key, default=None):
        try: 
            return self._config[property][key]
        except:
            return default

    def set(self, property, value):
        self._config[property] = value

    def write(self, filename):
        outfile = open(filename, 'w')
        outfile.write( yaml.dump(self._config, default_flow_style=False) )
        outfile.close()

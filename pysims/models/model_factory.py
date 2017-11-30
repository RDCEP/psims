from dssat45 import Dssat45
from dssat46 import Dssat46
from dssat   import Dssat
from apsim75 import Apsim75
from apsim79 import Apsim79

class ModelFactory(object):
    """
        ModelFactory: A class to instantiate model objects
        The model_objects attribute controls how to map the 'model' configuration option to a model class
    """

    def __init__(self):
        self.model_objects = {
            'dssat'   : Dssat,
            'dssat45' : Dssat45,
            'dssat46' : Dssat46,
            'apsim75' : Apsim75,
            'apsim79' : Apsim79,
        }

    def create_model(self, config):
        try:
            m = self.model_objects[config.get('model')](config)
        except KeyError:
            print "Invalid model parameter. Valid models are %s\n" % ','.join([k for k in self.model_objects.keys()])
            raise 
        return m

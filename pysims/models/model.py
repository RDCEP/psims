from abc import ABCMeta, abstractmethod

class Model(object):
    """A generic pSIMS model

    Attributes:
        config: A YAMLConfiguration object that contains all config info
    """

    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def run(self, tlatidx, tlonidx):
        """Run model with given command line string"""
        pass

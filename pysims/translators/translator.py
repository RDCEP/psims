import logging
import multiprocessing
import os
import shutil
from abc import ABCMeta, abstractmethod

class Translator(object):
    """A generic pSIMS translator

    Attributes:
        config: A YAMLConfiguration object that contains all config info
    """

    __metaclass__ = ABCMeta

    def __init__(self, config, translator_type):
        self.config = config
        self.log = multiprocessing.get_logger()
        self.translator_type = translator_type

    @abstractmethod
    def run(self, latidx, lonidx):
        """Run the translator"""
        pass

    def verify_params(self, latidx, lonidx):
        return (True, "%s translator likes the parameters" % type(self).__name__)


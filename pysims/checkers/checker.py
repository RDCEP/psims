import logging
import os
import shutil
from abc import ABCMeta, abstractmethod

class Checker(object):
    """A generic Checker translator

    Attributes:
        config: A YAMLConfiguration object that contains all config info
    """

    __metaclass__ = ABCMeta

    def __init__(self, config, checker_type):
        self.config = config
        self.log = logging.getLogger(__name__)
        self.checker_type = checker_type

    @abstractmethod
    def run(self, latidx, lonidx):
        """Run the translator"""
        pass

    def verify_params(self, latidx, lonidx):
        return (True, "%s translator likes the parameters" % type(self).__name__)

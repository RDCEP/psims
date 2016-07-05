import common.noop
import common.simplechecker

class CheckerFactory(object):
    """
        CheckerFactory: A class to instantiate checker objects
    """

    def __init__(self):
        self.checker_objects = {
            'noop':          common.noop.Noop,
            'SimpleChecker': common.simplechecker.SimpleChecker,
        }

    def create_checker(self, config, checker_type):
        if config.get(checker_type) == None:
            return self.checker_objects['noop'](config, checker_type)
        try:
            t = self.checker_objects[config.get(checker_type)['class']](config, checker_type)
        except KeyError:
            print "Invalid %s translator specified. Valid translators are %s\n" % (checker_type, ', '.join([k for k in self.checker_objects.keys()]))
            raise
        return t

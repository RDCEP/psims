from .. import checker

class Noop(checker.Checker):
    def run(self, latidx, lonidx):
        return True

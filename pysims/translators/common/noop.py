#!/usr/bin/env python

from .. import translator

class Noop(translator.Translator):

    def run(self, latidx, lonidx):
        return True

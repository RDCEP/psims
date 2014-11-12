from numpy import log, exp

def dewpoint(vap = None, hur = None, tmax = None, tmin = None, tas = None, hus = None, ps = None):
    """ dewp = dewpoint(vap, hur, tmax, tmin, tas, hus, ps)
        Inputs:
            vap:  Vapor pressure (mb)
            hur:  Relative humidity (%)
            tmax: Maximum temperature (deg C)
            tmin: Minimum temperature (deg C)
            tas:  Average temperature (deg C)
            hus:  Specific humidity (kg/kg)
            ps:   Surface pressure (mb)
        Outputs:
            dewp: Dewpoint temperature (deg C)
    """
    if not vap is None: # f(vapor pressure)
        return 4302.65 / (19.4803 - log(vap)) - 243.5
    elif not hur is None and not tas is None: # f(relative humidity, temperature)
        N = 243.5 * log(0.01 * hur * exp((17.67 * tas) / (tas + 243.5)))
        D = 22.2752 - log(hur * exp((17.67 * tas) / (tas + 243.5)))
        return N / D
    elif not hur is None and not tmax is None and not tmin is None: # f(relative humdity, max/min temperature)
        tas = 0.5 * (tmax + tmin)
        N = 243.5 * log(0.01 * hur * exp((17.67 * tas) / (tas + 243.5)))
        D = 22.2752 - log(hur * exp((17.67 * tas) / (tas + 243.5)))
        return N / D
    elif not hus is None and not ps is None: # f(specific humidity, surface pressure)
        hus[hus == 0] = 0.00001
        N = -243.5 * log((2.31034 * hus + 3.80166) / (ps * hus))
        D = log((hus + 1.6455) / (ps * hus)) + 18.5074
        return N / D
    else:
        raise Exception('Cannot compute dewpoint temperature from inputs')
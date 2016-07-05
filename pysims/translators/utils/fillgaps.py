from numpy import array, zeros
from datetime import timedelta
from numpy.ma import masked_array, masked_where, is_masked

def fill(data, time, ref, varname):
    var = masked_array(data)

    for i in range(len(data)):
        isfill = var[i] > 1e10
        var[i] = masked_where(var[i] > 1e10, var[i]) # remove fill values
        var[i] = var[i].astype(float) # convert to float

        if isfill.sum():
            # if 100. * isfill.sum() / var[i].size > 1.:
            #     raise Exception('More than one percent of values for variable %s are masked!' % varname)
            if varname in ['RAIN', 'rain']:
                var[i, isfill] = 0. # fill with zeros
            else:
                days = array([int((ref + timedelta(int(t))).strftime('%j')) for t in time])
                fdays = days[isfill]
                varave = zeros(len(fdays))
                for j in range(len(fdays)):
                    ave = var[i, days == fdays[j]].mean()
                    varave[j] = ave if not is_masked(ave) else 1e20 
                var[i, isfill] = varave # fill with daily average

    return var

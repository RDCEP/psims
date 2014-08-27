#!/usr/bin/env python

from re import findall
from itertools import product
from netCDF4 import Dataset as nc
from optparse import OptionParser
from numpy.ma import masked_array
from numpy import where, zeros, ones, unique, floor, newaxis, array, argmax

parser = OptionParser()
parser.add_option("-o", "--optfile", dest = "optfile", default = "opt.scen.noconst.81-12.nc4", type = "string", 
                  help = "Optimal scenarios file", metavar = "FILE")
parser.add_option("-y", "--yldfile", dest = "yldfile", default = "yield_targets_all.nc4", type = "string", 
                  help = "Yield targets file", metavar = "FILE")
options, args = parser.parse_args()

fopt = nc(options.optfile, 'a') # append later

with nc(options.yldfile) as f:
    irryld = f.variables['irr'].long_name.split(', ')
    ytime = f.variables['time'][:]
    tunits = f.variables['time'].units
    harvested_area = f.variables['harvested_area'][:]

ytime += int(findall(r'\d+', tunits)[0]) # years since to years

counties = fopt.variables['county'][:]
ncounties = len(counties)

states = floor(counties / 1000.)
ustates = unique(states)
nstates = len(ustates)

otime = fopt.variables['time'][:]
tunits = fopt.variables['time'].units
otime += int(findall(r'\d+', tunits)[0]) - 1 # growing seasons since to years
ntime = len(otime)

time1, time2 = fopt.variables['time1'][:], fopt.variables['time2'][:]
ntime1, ntime2 = len(time1), len(time2)

irropt = fopt.variables['irr'].long_name.split(', ')
nirr = len(irropt)

tfullidx1, tfullidx2 = where(ytime == otime[0])[0][0], where(ytime == otime[-1])[0][0] + 1

sopt = fopt.variables['scenopt'][:]
syld = fopt.variables['sim_yield'][:]
rmse = fopt.variables['rmse'][:]

# harvested_area(time, county, irr) -> harvested_area_opt(county, time1, time2, irr)
# harvested_area(time, county, irr) -> harvested_area_yld(county, time1, time2, time, irr)

# ====================
# COUNTRY AGGREGATIONS
# ====================
sh1 = (ncounties, ntime1, ntime2, nirr)
sh2 = (ncounties, ntime1, ntime2, ntime, nirr)
sh3 = (1, ntime1, ntime2, nirr)
harvested_area_opt = masked_array(zeros(sh1), mask = ones(sh1))
harvested_area_yld = masked_array(zeros(sh2), mask = ones(sh2))
sopt_country = masked_array(zeros(sh3), mask = ones(sh3))
for i1, i2 in product(range(ntime1), range(ntime2)):
    t1, t2 = time1[i1], time2[i2]
    if t2 >= t1:
        tidx1, tidx2 = where(ytime == t1)[0][0], where(ytime == t2)[0][0] + 1
        harvested_area_opt[:, i1, i2, :] = harvested_area[tidx1 : tidx2].mean(axis = 0)
        for i in range(nirr):
            have_county = harvested_area_opt[:, i1, i2, i]
            sopt_county = sopt[:, i1, i2, i]
            usopt, uidx = unique(sopt_county, return_inverse = True)
            sumha = array([have_county[uidx == u].sum() for u in range(0, len(usopt))])
            maxidx = argmax(sumha)
            sopt_country[0, i1, i2, i] = usopt[maxidx]
    harvested_area_yld[:, i1, i2, :, :] = harvested_area[tfullidx1 : tfullidx2].transpose((1, 0, 2))

syld_country = (syld * harvested_area_yld).sum(axis = 0) / harvested_area_yld.sum(axis = 0)
syld_country = syld_country[newaxis, ...]
rmse_country = (rmse * harvested_area_opt).sum(axis = 0) / harvested_area_opt.sum(axis = 0)
rmse_country = rmse_country[newaxis, ...]

# ==================
# STATE AGGREGATIONS
# ==================
sh1 = (nstates, ntime1, ntime2, nirr)
sh2 = (nstates, ntime1, ntime2, ntime, nirr)
sopt_state = masked_array(zeros(sh1), mask = ones(sh1))
rmse_state = masked_array(zeros(sh1), mask = ones(sh1))
syld_state = masked_array(zeros(sh2), mask = ones(sh2))
for i in range(nstates):
    is_state = states == ustates[i]
    syld_state_i = syld[is_state]
    hvts_state_i = harvested_area_yld[is_state]
    syld_state[i] = (syld_state_i * hvts_state_i).sum(axis = 0) / hvts_state_i.sum(axis = 0)
    rmse_state_i = rmse[is_state]
    hvto_state_i = harvested_area_opt[is_state]
    rmse_state[i] = (rmse_state_i * hvto_state_i).sum(axis = 0) / hvto_state_i.sum(axis = 0)
    for i1, i2 in product(range(ntime1), range(ntime2)):
        t1, t2 = time1[i1], time2[i2]
        if t2 >= t1:
            for j in range(nirr):
                have_county = harvested_area_opt[is_state, i1, i2, j]
                sopt_county = sopt[is_state, i1, i2, j]
                usopt, uidx = unique(sopt_county, return_inverse = True)
                sumha = array([have_county[uidx == u].sum() for u in range(0, len(usopt))])
                sopt_state[i, i1, i2, j] = usopt[argmax(sumha)]

# =============
# ADD VARIABLES
# =============
fopt.createDimension('country', 1)
countryvar = fopt.createVariable('country', 'i4', 'country')
countryvar[:] = 240 # USA
countryvar.units = ''
countryvar.long_name = 'country index'

fopt.createDimension('state', nstates)
statevar = fopt.createVariable('state', 'i4', 'state')
statevar[:] = ustates
statevar.units = ''
statevar.long_name = 'state index'

# scenario
soptcvar = fopt.createVariable('scenopt_country', 'f4', ('country', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
soptcvar[:] = sopt_country
soptcvar.units = ''
soptcvar.long_name = 'optimal country-level scenario'
soptsvar = fopt.createVariable('scenopt_state', 'f4', ('state', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
soptsvar[:] = sopt_state
soptsvar.units = ''
soptsvar.long_name = 'optimal state-level scenario'

# RMSE
rmsecvar = fopt.createVariable('rmse_country', 'f4', ('country', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
rmsecvar[:] = rmse_country
rmsecvar.units = 'kg/ha'
rmsecvar.long_name = 'optimal country-level RMSE'
rmsesvar = fopt.createVariable('rmse_state', 'f4', ('state', 'time1', 'time2', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
rmsesvar[:] = rmse_state
rmsesvar.units = 'kg/ha'
rmsesvar.long_name = 'optimal state-level RMSE'

# sim_yield
syldcvar = fopt.createVariable('sim_yield_country', 'f4', ('country', 'time1', 'time2', 'time', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
syldcvar[:] = syld_country
syldcvar.units = ''
syldcvar.long_name = 'simulated country-level yield'
syldsvar = fopt.createVariable('sim_yield_state', 'f4', ('state', 'time1', 'time2', 'time', 'irr'), zlib = True, shuffle = False, complevel = 9, fill_value = 1e20)
syldsvar[:] = syld_state
syldsvar.units = ''
syldsvar.long_name = 'simulated state-level yield'

fopt.close()
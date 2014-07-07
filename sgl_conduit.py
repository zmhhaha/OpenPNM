# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 16:38:29 2014

@author: Jackie
"""
import OpenPNM
import matplotlib.pyplot as plt
import scipy as sp


r"""
returns array
array[0] = saturation
array[1] = relative permeability
array[2] = relative effective diffusivity
"""  
Lc = 40.5e-6
N = 10

#setting up network
sgl = OpenPNM.Network.Cubic(name = 'SGL10BA')
sgl.generate(divisions = [N, N, N], add_boundaries = True, lattice_spacing = [Lc])

#pore size distribution parameters
lmbda = 9e-6
k = 3.5
bmin = 9e-6
xmax = .9

#set up geometries
geo = OpenPNM.Geometry.GenericGeometry(name = 'sgl', network = sgl)
geo.set_locations(pores = sgl.pores('all'), throats = 'all')

Np = sgl.num_pores('sgl')
value = lmbda*(-sp.log(1-sp.random.rand(Np)*xmax))**(-1/k) + bmin
sgl.set_data(prop='diameter',pores=geo.pores(),data=value)

geo.add_method(prop='pore_volume',model='sphere')
geo.add_method(prop='throat_length',model='straight')
geo.add_method(prop='throat_volume',model='cuboid')

connected_pores = sgl.find_connected_pores(geo.throats())
value = [min(sgl.get_data(pores = pair[0], prop = 'diameter'), sgl.get_data(pores = pair[1], prop = 'diameter')) for pair in connected_pores]
sgl.set_data(prop = 'diameter', throats = geo.throats(), data = value)


sgl.regenerate_geometries()

#spatial correlation of pore sizes?!

#constricting sgl by .95 in both the z and y direction  
throats = geo.throats()
connected_pores = sgl.find_connected_pores(throats)
x1 = [sgl['pore.coords'][pair[0]][0] for pair in connected_pores]
x2 = [sgl['pore.coords'][pair[1]][0] for pair in connected_pores]
same_x = [x - y == 0 for x, y in zip(x1,x2)]
factor = [s*.95 + (not s)*1 for s in same_x]
throat_diameters = sgl['throat.diameter'][throats]*factor
sgl.set_data(throats = throats, prop = 'diameter', data = throat_diameters)

#set up fluids 
air = OpenPNM.Fluids.Air(network = sgl, name = 'air')
water = OpenPNM.Fluids.Water(network = sgl, name = 'water')
#MYSTERIOUSLY BROKEN LINE
#water_sgl.add_property(prop = 'contact_angle', model = 'constant', value = 100)
water['pore.contact_angle'] = 100
sgl.regenerate_fluids()

#set up physics 
phys_water = OpenPNM.Physics.GenericPhysics(network=sgl,fluid=water, geometry = geo, name='standard_water_physics')
phys_air = OpenPNM.Physics.GenericPhysics(network=sgl,fluid=air, geometry = geo, name='standard_air_physics')
   
phys_water.add_property(prop='capillary_pressure', model='washburn')
phys_water.add_property(prop='hydraulic_conductance',model='hagen_poiseuille')
phys_water.add_property(prop='diffusive_conductance', model='bulk_diffusion', shape = 'square')

phys_air.add_property(prop='hydraulic_conductance',model='hagen_poiseuille')
phys_air.add_property(prop='diffusive_conductance', model='bulk_diffusion') 


sgl.regenerate_physics()

#late pore filling?!

#running invasion percolation
inlets = sgl.get_pore_indices(labels = ['top','boundary'],mode='intersection')
outlets = sgl.get_pore_indices(labels = ['bottom','boundary'],mode='intersection')

end_condition = 'breakthrough'
    
OP_1 = OpenPNM.Algorithms.OrdinaryPercolation(network=sgl,loglevel=30)
OP_1.setup(invading_fluid = water, defending_fluid = air, inlets = inlets,npts=100)
OP_1.run() 

x_values = []
y_values = []
y2_values = []
z_values = []
z2_values = []

max_capillary_pressure = max(OP_1.get_throat_data(prop = 'inv_Pc'))
#    OP_1.update(max(OP_1.get_throat_data(prop='inv_Pc')))
#    OP_1.update(sp.stats.mstats.mode(OP_1.get_pore_data(prop='inv_Pc')))

for x in range(50):
    OP_1.update(max_capillary_pressure*(x/50.0))
    
    #adding multiphase conductances
    phys_air.add_property(prop='multiphase',model='conduit_conductance',
                      conductance = 'diffusive_conductance', prop_name='conduit_diffusive_conductance',mode='strict')
    phys_water.add_property(prop='multiphase',model='conduit_conductance',
                      conductance = 'diffusive_conductance', prop_name='conduit_diffusive_conductance',mode='strict')
    phys_air.add_property(prop='multiphase',model='conduit_conductance',
                      conductance = 'hydraulic_conductance', prop_name='conduit_hydraulic_conductance',mode='strict')
    phys_water.add_property(prop='multiphase',model='conduit_conductance',
                      conductance = 'hydraulic_conductance', prop_name='conduit_hydraulic_conductance',mode='strict')
    sgl.regenerate_physics()
    
    
    #run Stokes Flow and find Permeability
    #single phase
    Stokes_alg_single_phase_air = OpenPNM.Algorithms.StokesFlow(loggername = 'Stokes', name = 'Stokes_alg_single_phase_air', network = sgl)
    Stokes_alg_single_phase_water = OpenPNM.Algorithms.StokesFlow(loggername = 'Stokes_2', name = 'Stokes_alg_single_phase_water', network = sgl)
    
    Fickian_alg_single_phase_air = OpenPNM.Algorithms.FickianDiffusion(loggername = 'Fickian', name = 'Fickian_alg_single_phase_air', network = sgl)
    Fickian_alg_single_phase_water = OpenPNM.Algorithms.FickianDiffusion(loggername = 'Fickian_2', name = 'Fickian_alg_single_phase_water', network = sgl)
    
    Stokes_alg_multi_phase_air = OpenPNM.Algorithms.StokesFlow(loggername = 'Stokes', name = 'Stokes_alg_multi_phase_air', network = sgl)
    Stokes_alg_multi_phase_water = OpenPNM.Algorithms.StokesFlow(loggername = 'Stokes_2', name = 'Stokes_alg_multi_phase_water', network = sgl)
    
    Fickian_alg_multi_phase_air = OpenPNM.Algorithms.FickianDiffusion(loggername = 'Fickian', name = 'Fickian_alg_multi_phase_air', network = sgl)
    Fickian_alg_multi_phase_water = OpenPNM.Algorithms.FickianDiffusion(loggername = 'Fickian_2', name = 'Fickian_alg_multi_phase_water', network = sgl)
    
    #setting up boundary conditions and calculating effective_permeability
    #BC1
    BC1_pores = sgl.pores(labels=['top'],mode='intersection')
    Stokes_alg_single_phase_air.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.6, pores=BC1_pores)
    Stokes_alg_single_phase_water.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.6, pores=BC1_pores)
    Fickian_alg_single_phase_air.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .6, pores = BC1_pores)
    Fickian_alg_single_phase_water.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .6, pores = BC1_pores)
    
    Stokes_alg_multi_phase_air.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.6, pores=BC1_pores)
    Stokes_alg_multi_phase_water.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.6, pores=BC1_pores)
    Fickian_alg_multi_phase_air.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .6, pores = BC1_pores)
    Fickian_alg_multi_phase_water.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .6, pores = BC1_pores)   
    
    #BC2    
    BC2_pores = sgl.pores(labels=['bottom'],mode='intersection')
    Stokes_alg_single_phase_air.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.2, pores=BC2_pores)
    Stokes_alg_single_phase_water.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.2, pores=BC2_pores)
    Fickian_alg_single_phase_air.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .2, pores = BC2_pores)
    Fickian_alg_single_phase_water.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .2, pores = BC2_pores)
    
    Stokes_alg_multi_phase_air.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.2, pores=BC2_pores)
    Stokes_alg_multi_phase_water.set_boundary_conditions(bctype='Dirichlet', bcvalue=0.2, pores=BC2_pores)
    Fickian_alg_multi_phase_air.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .2, pores = BC2_pores)
    Fickian_alg_multi_phase_water.set_boundary_conditions(bctype = 'Dirichlet', bcvalue = .2, pores = BC2_pores)
    
    #conduit conductance
    Stokes_alg_single_phase_air.setup(conductance = 'hydraulic_conductance',fluid=air)
    Stokes_alg_single_phase_water.setup(conductance = 'hydraulic_conductance',fluid=water)
    Fickian_alg_single_phase_air.setup(conductance = 'diffusive_conductance',fluid=air) 
    Fickian_alg_single_phase_water.setup(conductance = 'diffusive_conductance',fluid=water)
    
    Stokes_alg_multi_phase_air.setup(conductance = 'conduit_hydraulic_conductance',fluid=air)
    Stokes_alg_multi_phase_water.setup(conductance = 'conduit_hydraulic_conductance',fluid=water)
    Fickian_alg_multi_phase_air.setup(conductance = 'conduit_diffusive_conductance',fluid=air) 
    Fickian_alg_multi_phase_water.setup(conductance = 'conduit_diffusive_conductance',fluid=water)
    
    #run
    Stokes_alg_single_phase_air.run()
    Stokes_alg_single_phase_water.run()
    Fickian_alg_single_phase_air.run()
    Fickian_alg_single_phase_water.run()
    
    Stokes_alg_multi_phase_air.run()
    Stokes_alg_multi_phase_water.run()
    Fickian_alg_multi_phase_air.run()
    Fickian_alg_multi_phase_water.run()
    
    #calc effective properties
    effective_permeability_air_single = Stokes_alg_single_phase_air.calc_eff_permeability(clean = False)  
    effective_diffusivity_air_single = Fickian_alg_single_phase_air.calc_eff_diffusivity(clean = False)
    effective_permeability_water_single = Stokes_alg_single_phase_water.calc_eff_permeability(clean = False)  
    effective_diffusivity_water_single = Fickian_alg_single_phase_water.calc_eff_diffusivity(clean = False)
    
    effective_permeability_air_multi = Stokes_alg_multi_phase_air.calc_eff_permeability(clean = False)  
    effective_diffusivity_air_multi = Fickian_alg_multi_phase_air.calc_eff_diffusivity(clean = False)
    effective_permeability_water_multi = Stokes_alg_multi_phase_water.calc_eff_permeability(clean = False)  
    effective_diffusivity_water_multi = Fickian_alg_multi_phase_water.calc_eff_diffusivity(clean = False)
    
    final_pores = water.get_pore_data('occupancy')*1
    pore_volumes = sgl.get_pore_data(prop = 'volume')
    final_throats = water.get_throat_data('occupancy')*1
    throat_volumes = sgl.get_throat_data(prop = 'volume')
    
    sum_volume = 0
    filled_volume = 0
    
    for i in range(len(sgl.pores())):
        sum_volume += pore_volumes[i]
        if final_pores[i] != 0:
            filled_volume += pore_volumes[i]
            
    for j in range(len(sgl.throats())):
        sum_volume += throat_volumes[j]
        if final_throats[j] != 0:
            filled_volume += throat_volumes[j]
        
    saturation = filled_volume/sum_volume
    
    relative_eff_perm_air = effective_permeability_air_multi/effective_permeability_air_single
    relative_eff_perm_water = effective_permeability_water_multi/effective_permeability_water_single
    relative_eff_diff_air = effective_diffusivity_air_multi/effective_diffusivity_air_single
    relative_eff_diff_water = effective_diffusivity_water_multi/effective_diffusivity_water_single
    
    x_values.append(saturation)
    y_values.append(relative_eff_perm_air)
    y2_values.append(relative_eff_perm_water)
    z_values.append(relative_eff_diff_air)
    z2_values.append(relative_eff_diff_water)


x_values1 = [x/20 for x in range(20)]

plt.plot(x_values, y_values, 'ro')
plt.plot(x_values, y2_values, 'bs')
plt.plot(x_values1, [x**(3) for x in x_values1], 'g--')

plt.title('saturation versus relative permeability')
plt.xlabel('saturation')
plt.ylabel('relative permeability')
plt.show()

plt.plot(x_values, z_values, 'ro')
plt.plot(x_values, z2_values, 'bs')
plt.plot(x_values1, [x**(2) for x in x_values1], 'g--')

plt.title('saturation versus relative diffusivity')
plt.xlabel('saturation')
plt.ylabel('relative diffusivity')
plt.show()
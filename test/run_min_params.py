from merlin import *
import shutil
import hashlib

run_name = sys.argv[1] if len(sys.argv)>1 else 'test'
optimization_method = sys.argv[2] if len(sys.argv)>2 else 'SBPLX'
random_seed = int(hashlib.md5(run_name).hexdigest(), 16)%(2**16)

I_ = 66
Cl_ = 21
H_ = 54
N_ = 53
Pb_ = 111

Pb = 907
I = 838
Cl = 344

extra = {
	(H_, I_): (100.0, 2.1), 
	(N_, H_, I_): (10.0, 180.0), 
	Pb: utils.Struct(index=Pb, index2=Pb_, element_name='Pb', element=82, mass=207.2, charge=0.4, vdw_e=10.1, vdw_r=3.0),
	I: utils.Struct(index=I, index2=I_, element_name='I', element=53, mass=126.9, charge=-0.2, vdw_e=10.1, vdw_r=2.5),
	Cl: utils.Struct(index=I, index2=Cl_, element_name='Cl', element=17, mass=35.435, charge=-0.2, vdw_e=10.1, vdw_r=2.0),
}

system = utils.System(box_size=[1e3, 50, 50], name=run_name)

systems_by_composition = {}

for outer in ['/fs/home/jms875/build/lammps/lammps-7Dec15/src/test/']:
	directories = next(os.walk(outer+'orca'))[1]
	for directory in directories:
		name = directory
		if not os.path.isfile(outer+'orca/'+name+'/'+name+'.orca.engrad'): continue
		try:
			atoms, energy = orca.engrad_read(outer+'orca/'+name+'/'+name+'.orca.engrad', pos='Ang')
		except IndexError:
			continue
		#if name not in ['PbCl6_-4_sp2_%d' % i for i in range(12)]:
		if len(atoms)>7 or 'mp2' not in name or 'qz' in name or len(atoms)==5: continue
		with_bonds = utils.Molecule(outer+'orca/'+name+'/system.cml', extra_parameters=extra, check_charges=False)
		for a,b in zip(atoms,with_bonds.atoms):
			convert = 627.51/0.529177249 #Hartee/Bohr to kcal/mole-Angstrom
			b.fx, b.fy, b.fz = a.fx*convert, a.fy*convert, a.fz*convert
			if utils.dist(a,b)>1e-4:
				raise Exception('Atoms too different:', (a.x,a.y,a.z), (b.x,b.y,b.z))
		with_bonds.energy = energy
		composition = ' '.join(sorted([a.element for a in atoms]))
		if composition not in systems_by_composition:
			systems_by_composition[composition] = []
		systems_by_composition[composition].append(with_bonds)

xyz_atoms = []

for composition in systems_by_composition: #within each type of system, lowest energy must be first and equal to 0.0
	systems_by_composition[composition].sort(key=lambda s:s.energy)
	baseline_energy = systems_by_composition[composition][0].energy
	for s in systems_by_composition[composition]:
		s.energy -= baseline_energy
		s.energy *= 627.5 #Convert Hartree to kcal/mol
		#todo: add energy cutoff, e.g. 1000 kcal/mol?
		print composition, s.energy #for testing purposes
		xyz_atoms.append(s.atoms) #for testing purposes
		system.add(s, len(system.molecules)*1000.0)

system.box_size[0] = len(system.molecules)*1000.0*2+200.0

files.write_xyz(xyz_atoms, 'states')
#exit()

os.chdir('lammps')
files.write_lammps_data(system)

#f = open('test_log.txt','w')
#for t in system.atom_types:
#	f.write(str(t)+' ')
#f.close()

shutil.copy('input.tersoff', system.name+'_input.tersoff')
shutil.copy('upper_bounds.tersoff', system.name+'_upper.tersoff')
shutil.copy('lower_bounds.tersoff', system.name+'_lower.tersoff')

# write forces to a file
f = open(system.name+'_forces.txt', 'w')
for a in system.atoms:
	f.write("%e\n%e\n%e\n" % (a.fx, a.fy, a.fz) )
f.close()
# write energies to a file
f = open(system.name+'_energies.txt', 'w')
for m in system.molecules:
	f.write("%e\n" % (m.energy) )
f.close()

commands = ('''units real
atom_style full
pair_style hybrid/overlay lj/cut/coul/inout 0.2 3.5 15 tersoff
bond_style harmonic
angle_style harmonic
dihedral_style opls
special_bonds lj/coul 0.0 0.0 0.5

boundary f f f
read_data	'''+system.name+'''.data

pair_coeff * * lj/cut/coul/inout 0.0 1.0 3.5
''').splitlines()
lmp = utils.Struct()
lmp.file = open(system.name+'.in', 'w')
def writeline(line):
	lmp.file.write(line+'\n')
lmp.command = writeline
for line in commands:
	lmp.command(line)

lmp.command('pair_coeff * * tersoff '+system.name+'_input.tersoff Pb Cl '+(' NULL'*(len(system.atom_types)-2)) )

for t in system.bond_types:
	lmp.command('bond_coeff %d	%f %f' % (t.lammps_type, t.e, t.r) )
for t in system.angle_types:
	lmp.command('angle_coeff %d	%f %f' % (t.lammps_type, t.e, t.angle) )
for t in system.dihedral_types:
	lmp.command('dihedral_coeff %d	%f %f %f %f' % ((t.lammps_type,)+t.e))

commands = '''
compute atom_pe all pe/atom
compute sum_pe all reduce sum c_atom_pe
thermo_style custom c_sum_pe
#thermo 1
neigh_modify once yes

min_style params
min_modify '''+run_name+''' '''+optimization_method+''' '''+str(random_seed)+'''
minimize 0.01 0.01 1728000000 1728000000 #with 224 atoms, does 2e4 steps/second. One day = 1728000000, 40% of 2^32. 
'''
for line in commands.splitlines():
	lmp.command(line)

lmp.file.close()
os.system('../../lmp_serial -in %s.in -log %s.log' % (system.name,system.name))


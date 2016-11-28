import mcsmrff_opt

LJ = [[2.0, -1.0, 1.0], [3.98892, 4.15625, 4.0], [0.1, 0.1, 0.1]]
three_body_interactions = ['Pb, Pb, Pb',
                           'Pb, Pb, Cl',
                           'Pb, Pb, Cs',
                           'Pb, Cl, Pb',
                           'Pb, Cl, Cl',
                           'Pb, Cl, Cs',
                           'Pb, Cs, Pb',
                           'Pb, Cs, Cl',
                           'Pb, Cs, Cs',
                           'Cl, Pb, Pb',
                           'Cl, Pb, Cl',
                           'Cl, Pb, Cs',
                           'Cl, Cl, Pb',
                           'Cl, Cl, Cl',
                           'Cl, Cl, Cs',
                           'Cl, Cs, Pb',
                           'Cl, Cs, Cl',
                           'Cl, Cs, Cs',
                           'Cs, Pb, Pb',
                           'Cs, Pb, Cl',
                           'Cs, Pb, Cs',
                           'Cs, Cl, Pb',
                           'Cs, Cl, Cl',
                           'Cs, Cl, Cs',
                           'Cs, Cs, Pb',
                           'Cs, Cs, Cl',
                           'Cs, Cs, Cs']

Pb = 907
Cl = 344
Cs = 352
tersoff_atoms = [Pb, Cl, Cs]

mcsmrff_opt.run_mcsmrff_optimizer(
    n_sets=5,
    sim_name="test",
    lennard_jones=LJ,
    atom_list=three_body_interactions,
    tersoff=None,
    lj_coul=None,
    constant_charge=True,
    training_set_pickle_path=(
        "/fs/home/hch54/"
        "Grad-MCSMRFF/PbCl3Cs/set2/"
        "set2.pickle"),
    tersoff_atoms=tersoff_atoms
)
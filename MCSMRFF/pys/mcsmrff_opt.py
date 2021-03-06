'''
mcsmrff_opt
-----------

Optimization algorithm for parameterization of MCSMRFF.  Works as follows:

1. Generate M sets of N dimensional parameters using LHC.  That is, there is a
   set of parameters we need for MCSMRFF to run which is N dimensional, and we
   have M sets of these to search the energy landscape.

2. Submit M simulations in parallel on the cluster.  These will run either bfgs
   or steepest descent (SD) to minimize the parameter space.

3. As simulations begin converging, ...
'''

import os
import time

import jobs as JLIST

from mcsmrff_lhs import create_lhs
from mcsmrff_queue_job import job
from mcsmrff_files import read_params, write_params


def run_mcsmrff_optimizer(
        n_sets=3,
        sim_name="Debug",
        lennard_jones=None,
        atom_list=None,
        path_to_parameters=None,
        tersoff=None,
        lj_coul=None,
        constant_charge=True,
        tersoff_atoms=[],
        new_pdf_props={},
        new_opt_props={},
        training_set_pickle_path=None):
    """
    Run an optimization for the tersoff parameters.

    **Parameters**

        n_sets: *int, optional*
            The number of parameter sets to run in parallel.
        sim_name: *str, optional*
            The name for this optimization.
        lj_paramlist: *list, list, float*
            Three lists, holding (1) charges, (2) LJ sigma, and (3) LJ epsilon
        atom_list: *list, str*
            1D array holding the different 3-body interactions
        training_set_pickle_path: *str, optional*
            The path to the pickled training set.
        path_to_parameters: *str, optional*
            A .tersoff file containing LJ and Coul parameters.

    **Returns**

        Stuff.
    """

    num_combinations = len(atom_list)
    if tersoff is not None:
        num_combinations = len(tersoff)

    # Part 1, generation of parameter sets
    PARAMETER_SETS = create_lhs(num_combinations, num_samples=n_sets)

    # Read in the lennard jones and atom list from
    # another mcsmrff .tersoff file
    if path_to_parameters is not None:
        P1, P2, _ = read_params(path_to_parameters, exact=True)
    if lennard_jones is not None:
        P1 = lennard_jones
    if atom_list is not None:
        P2 = atom_list

    if (lennard_jones is None and
            atom_list is None and
            path_to_parameters is None):
        raise Exception("Need to specify parameters, either from old parameter \
file, or manually.")

    # Part 2, submit jobs to queue
    if not os.path.isdir(sim_name):
        os.mkdir(sim_name)
    os.chdir(sim_name)
    if not os.path.isdir("parameters"):
        os.mkdir("parameters")

    jobs = []
    # Loop through the randomized parameter sets and
    # start simulations for gradient optimization.
    for i, P3 in enumerate(PARAMETER_SETS):
        job_name = "%s_%d" % (sim_name, i)
        pname = "parameters/" + job_name
        write_params(P1, P2, P3, pname, append="")

        job(job_name, pname, atom_list, tersoff_atoms,
            tersoff=tersoff,
            lj_coul=lj_coul,
            constant_charge=constant_charge,
            new_pdf_props=new_pdf_props,
            new_opt_props=new_opt_props,
            disregard=["N", "C", "H"])
        jobs.append(job_name)

    # Part 3, monitor jobs. Follow lowest error jobs.
    # Whenever one finishes with higher error, kill
    # neighbourhood and resubmit EXPANSION_NUMBER more
    job_output = {}
    while len(jobs) > 0:
        time.sleep(60)
        running = JLIST.get_running_jobs()
        to_kill = []
        for i, j in enumerate(jobs):
            if j not in running:
                # If we have finished the job, store the end results
                # Output will be in file j.log
                # NOTE, this is all running from the "sim_name" folder
                output = open("%s.log" % j).read().split("\n")
                endpoint = len(output) - 1
                while(endpoint > 0 and output[endpoint].strip() == ""):
                    endpoint -= 1

                # If we have output, try reading it in. Else this job failed
                fail_flag = False
                if endpoint > 0:
                    output = output[:endpoint + 1]
                    rms = output[-1]
                    if "RMS" in rms:
                        job_output[j] = {"rms": float(rms.split()[-1]),
                                         "passed": True}
                        k = 0
                        while (k < len(output) and
                               not output[k].startswith("Running glimpse")):
                            k += 1
                        final_error = output[k - 1].split()[-2:]
                        job_output[j]["force_error"] = float(final_error[0])
                        job_output[j]["energy_error"] = float(final_error[1])
                    else:
                        fail_flag = True

                else:
                    fail_flag = True

                if fail_flag:
                    job_output[j] = {"passed": False}

                to_kill.append(i)

        to_kill = sorted(to_kill)[::-1]
        for k in to_kill:
            del jobs[k]

    print("\nOutput data for debugging is...\n\n")
    print job_output

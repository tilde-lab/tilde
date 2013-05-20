from ase.tasks.main import run

# warning! parameters are not converged - only an illustration!

atoms, task = run('aims bulk Li -x bcc -a 3.6 --k-point-density 1.5 --srelax 0.05 --srelaxsteps 1 -t stress -p xc=pw-lda,sc_accuracy_eev=5.e-2,relativistic=none,compute_analytical_stress=True,sc_accuracy_forces=5.e-2')
atoms, task = run('aims bulk Li -x bcc -a 3.6 -t stress -s')
data = task.data['Li']

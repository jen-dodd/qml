r"""

Differentiable Hartree-Fock Solver
==================================

.. meta::
    :property="og:description": Learn how to use the differentiable Hartree-Fock solver
    :property="og:image": https://pennylane.ai/qml/_images/differentiable_HF.png

.. related::
    tutorial_quantum_chemistry Quantum chemistry with PennyLane
    tutorial_vqe A brief overview of VQE
    tutorial_givens_rotations Givens rotations for quantum chemistry
    tutorial_adaptive_circuits Adaptive circuits for quantum chemistry


*Author: PennyLane dev team. Posted:  2021. Last updated: XX January 2022*

Variational quantum algorithms aim to calculate the energy of a molecule by constructing a
parametrized quantum circuit and finding a set of parameters that minimize the expectation value of
the electronic `molecular Hamiltonian <https://en.wikipedia.org/wiki/Molecular_Hamiltonian>`_. The
optimization can be carried out by computing the gradients of the expectation value with respect to
these parameters and iteratively updating them until convergence is achieved. In principle, the
optimization process is not limited to the circuit parameters and can be extended to include the
parameters of the Hamiltonian that can be optimized concurrently with the circuit parameters. The
aim is now to obtain the set of parameters that minimize the following expectation value

.. math:: \left \langle \Psi(\theta) | H(\beta) | \Psi(\theta) \right \rangle,

where :math:`\theta` and :math:`\beta` represent the circuit and Hamiltonian parameters,
respectively.

Computing the gradient of a molecular Hamiltonian is challenging because the dependency of the
Hamiltonian to the molecular parameters is typically not very straightforward. This makes symbolic
differentiation methods, which obtain derivatives of an input function by direct mathematical
manipulation, of limited scope. Furthermore, numerical differentiation methods based on finite
differences are not always reliable due to their intrinsic instability specially when the number of
differentiable parameters is large. These limitations can be alleviated by using automatic
differentiation methods which can be used to compute exact gradients of a function, implemented with
computer code, using resources comparable to those required to evaluate the function itself.

Efficient optimization of the molecular Hamiltonian parameters in a variational quantum algorithm
is essential for tackling problems such as geometry optimization and vibrational frequency
calculations. These problems require computing the first- and second-order derivatives of the
molecular energy with respect to nuclear coordinates which can be efficiently obtained if the
variational workflow is automatically differentiable. Another important example is the simultaneous
optimization of the parameters of the basis set used to construct the atomic orbitals which can in
principle increase the accuracy of the computed energy without increasing the number of qubits in a
quantum simulation. The joint optimization of the circuit and Hamiltonian parameters can also be
used when the chemical problem involves optimizing the parameters of external potentials. The
electronic Hamiltonian for a given molecule is constructed using one- and two-electron integrals
over optimized molecular orbitals which are obtained by solving the Hartree-Fock equations.

In this tutorial, you will learn how to use PennyLane's differentiable Hartree-Fock solver. The
Hartree-Fock module in PennyLane provides built-in methods for constructing atomic and molecular
orbitals, building Fock matrices, and solving the self-consistent field equations to obtain
optimized orbitals, which can be used to construct fully-differentiable molecular Hamiltonians.
PennyLane allows users to natively compute derivatives of all these objects with respect to the
underlying parameters using the methods of automatic differentiation. We introduce a workflow
to jointly optimize circuit parameters, nuclear coordinates, and basis set parameters in a
variational quantum eigensolver algorithm. You will also learn how to visualize the atomic and
molecular orbital and create images like this:

.. figure:: /demonstrations/differentiable_HF/h2.gif
    :width: 75%
    :align: center

    The bonding molecular orbital of hydrogen visualized during a full geometry, circuit, and
    basis set optimization.

Let's get started!

The Hartree-Fock method
-----------------------

The main goal of the Hartree-Fock method is to obtain molecular orbitals that minimize the
energy of a system where electrons are treated as independent particles that experience a mean field
generated by the other electrons. These optimized molecular orbitals are then used to
construct one- and two-body electron integrals in the basis of molecular orbitals, :math:`\phi`,

.. math:: h_{pq} =\int dx \,\phi_p^*(x)\left(-\frac{\nabla^2}{2}-\sum_{i=1}^N\frac{Z_i}{|r-R_i|}\right)\phi_q(x),\\\\
.. math:: h_{pqrs} = \int dx_1 dx_2\, \frac{\phi_p^*(x_1)\phi_q^*(x_2)\phi_r(x_2)\phi_s(x_1)}{|r_1-r_2|}.

These integrals are used to generate a differentiable
`second-quantized <https://en.wikipedia.org/wiki/Second_quantization>`_ molecular Hamiltonian as


.. math:: H=\sum_{pq} h_{pq}a_p^\dagger a_q +\frac{1}{2}\sum_{pqrs}h_{pqrs}a_p^\dagger a_q^\dagger a_r a_s,

where :math:`a^\dagger` and :math:`a` are the fermionic creation and annihilation operators,
respectively. This Hamiltonian is then transformed to the qubit basis. Let's see how this can be
done in PennyLane.

To get started, we need to define the atomic symbols and the nuclear coordinates of the molecule.
For the hydrogen molecule we have
"""
import pennylane.hf
from autograd import grad
import pennylane as qml
from pennylane import numpy as np
import matplotlib.pyplot as plt
np.set_printoptions(precision=5)

symbols = ["H", "H"]
# optimized geometry at the Hartree-Fock level
geometry = np.array([[-0.672943567415407, 0.0, 0.0],
                     [ 0.672943567415407, 0.0, 0.0]], requires_grad=True)

##############################################################################
# The use of ``requires_grad=True`` specifies that the nuclear coordinates are differentiable
# parameters. We can now compute the Hartree-Fock energy and its gradient with respect to the
# nuclear coordinates. To do that, we create a molecule object that stores all the molecular
# parameters needed to perform a Hartree-Fock calculation.

mol = qml.hf.Molecule(symbols, geometry)

##############################################################################
# The Hartree-Fock energy can now be computed with the :func:`~.pennylane.hf.hf_energy` function
# which is a function transform

qml.hf.hf_energy(mol)(geometry)

##############################################################################
# We now compute the gradient of the energy with respect to the nuclear coordinates

grad(qml.hf.hf_energy(mol))(geometry)

##############################################################################
# The obtained gradients are equal or very close to zero because the geometry we used here has been
# previously optimized at the Hartree-Fock level. You can use a different geometry and verify that
# the newly computed gradients are not all zero.
#
# We can also compute the values and gradients of several other quantities that are obtained during
# the Hartree-Fock procedure. These include all integrals over basis functions, matrices formed from
# these integrals and the one- and two-body integrals over molecular orbitals [#arrazola2021]_.
# Let's look at a few examples.
#
# We first compute the overlap integral between the two S-type atomic orbitals of the hydrogen
# atoms. Here we are using the `STO-3G <https://en.wikipedia.org/wiki/STO-nG_basis_sets>`_
# basis set in which each of the atomic orbitals is represented by one basis function composed of
# three primitive Gaussian functions. These basis functions can be accessed from the molecule
# object as

S1 = mol.basis_set[0]
S2 = mol.basis_set[1]

##############################################################################
# We can check the parameters of the basis functions as

for param in S1.params:
    print(param)

##############################################################################
# This returns the exponents, contraction coefficients and the centres of the three Gaussian
# functions of the STO-3G basis set. These parameters can be also obtained individually by using
# ``S1.alpha``, ``S1.coeff`` and ``S1.r``, respectively. You can verify that both of the ``S1`` an
# ``S2`` atomic orbitals have the same exponents and contraction coefficients but are centred on
# different hydrogen atoms. You can also verify that the orbitals are S-type by printing the angular
# momentum quantum numbers with

S1.l

##############################################################################
# This gives us a tuple of three integers, representing the exponents of the ``x``, ``y`` and ``z``
# components in the Gaussian functions [#arrazola2021]_.
#
# We can now compute the overlap integral,
#
# .. math::
#
#     S_{\mu \nu} = \int \chi_\mu^* (r) \chi_\nu (r) dr
#
# between the atomic orbitals :math:`\chi`, by passing the orbitals and the initial values of their
# centres to the :func:`~.pennylane.hf.generate_overlap` function. The centres of the orbitals are
# those of the hydrogen atoms by default and are therefore treated as differentiable parameters by
# PennyLane.

qml.hf.generate_overlap(S1, S2)([geometry[0], geometry[1]])

##############################################################################
# You can verify that the overlap integral between two identical atomic orbitals is equal to one.
# We can now compute the gradient of the overlap integral with respect to the orbital centres

grad(qml.hf.generate_overlap(S1, S2))([geometry[0], geometry[1]])

##############################################################################
# Can you explain why some of the computed gradients are zero?
#
# Let's now plot the atomic orbitals and their overlap. We can do it by using
# the :py:meth:`~.pennylane.hf.Molecule.atomic_orbital` function, which evaluates the atomic
# orbital at a given coordinate. For instance, the value of the S orbital on the first hydrogen atom
# can be computed at the origin as

V1 = mol.atomic_orbital(0)
V1(0.0, 0.0, 0.0)

##############################################################################
# We can evaluate this orbital at different points along the ``x`` axis and plot it.

x = np.linspace(-5, 5, 1000)
plt.plot(x, V1(x, 0.0, 0.0), color='teal')
plt.xlabel('X [Bohr]')
plt.show()

##############################################################################
# We can also plot the second S orbital and visualize the overlap between them

V2 = mol.atomic_orbital(1)
plt.plot(x, V1(x, 0.0, 0.0), color='teal')
plt.plot(x, V2(x, 0.0, 0.0), color='teal')
plt.fill_between(
    x,  np.minimum(V1(x, 0.0, 0.0), V2(x, 0.0, 0.0)), color = 'red', alpha = 0.5, hatch = '||')
plt.xlabel('X [Bohr]')
plt.show()

##############################################################################
# By looking at the orbitals, can you guess at what distance the value of the overlap becomes
# negligible? Can you verify your guess by computing the overlap at that distance?
#
# Similarly, we can plot the molecular orbitals of the hydrogen molecule obtained from the
# Hartree-Fock calculations. We plot the cross section of the bonding orbital on the ``x-y`` plane.

n = 30 # number of grid points along each axis

mol.mo_coefficients = mol.mo_coefficients.T
mo = mol.molecular_orbital(0)
x, y = np.meshgrid(np.linspace(-2, 2, n),
                   np.linspace(-2, 2, n))
val = np.vectorize(mo)(x, y, 0)
val = np.array([val[i][j]._value for i in range(n) for j in range(n)]).reshape(n, n)

fig, ax = plt.subplots()
co = ax.contour(x, y, val, 10, cmap='summer_r', zorder=0)
ax.clabel(co, inline=2, fontsize=10)
plt.scatter(mol.coordinates[:,0], mol.coordinates[:,1], s = 80, color='black')
ax.set_xlabel('X [Bohr]')
ax.set_ylabel('Y [Bohr]')
plt.show()

##############################################################################
# VQE simulations
# ---------------
#
# By performing the Hartree-Fock calculations, we obtain a set of one- and two-body integrals
# over molecular orbitals that can be used to construct the molecular Hamiltonian with the
# :func:`~.pennylane.hf.generate_hamiltonian` function.

hamiltonian = qml.hf.generate_hamiltonian(mol)(geometry)
print(hamiltonian)

##############################################################################
# The Hamiltonian contains 15 terms and, importantly, the coefficients of the Hamiltonian are all
# differentiable. We can construct a circuit and perform a VQE simulation in which both of the
# circuit parameters and the nuclear coordinates are optimized simultaneously by using the computed
# gradients. We will have two sets of differentiable parameters: the first set is the
# rotation angles of the excitation gates which are applied to the reference Hartree-Fock state
# to construct the exact ground state. The second set contains the nuclear coordinates of the
# hydrogen atoms.

dev = qml.device("default.qubit", wires=4)
def energy(mol):
    @qml.qnode(dev)
    def circuit(*args):
        qml.BasisState(np.array([1, 1, 0, 0]), wires=range(4))
        qml.DoubleExcitation(*args[0][0], wires=[0, 1, 2, 3])
        return qml.expval(qml.hf.generate_hamiltonian(mol)(*args[1:]))
    return circuit

##############################################################################
# Note that we only use the ``DoubleExcitation`` gate as the ``SingleExcitation`` ones can be
# neglected in this particular example [#szabo1996]_. We now compute the gradients of the energy
# with respect to the circuit parameter and the nuclear coordinates and update the parameters
# iteratively. Note that the nuclear coordinate gradients are simply the forces on the atomic
# nuclei.

# initial value of the circuit parameter
circuit_param = [np.array([0.0], requires_grad=True)]

for n in range(36):

    args = [circuit_param, geometry]
    mol = qml.hf.Molecule(symbols, geometry)

    # gradient for circuit parameters
    g_param = grad(energy(mol), argnum = 0)(*args)
    circuit_param = circuit_param - 0.25 * g_param[0]

    # gradient for nuclear coordinates
    forces = -grad(energy(mol), argnum = 1)(*args)
    geometry = geometry + 0.5 * forces

    if n % 5 == 0:
        print(f'n: {n}, E: {energy(mol)(*args):.8f}, Force-max: {abs(forces).max():.8f}')

##############################################################################
# After 35 steps of optimization, the forces on the atomic nuclei and the gradient of the
# circuit parameter are both approaching zero, and the energy of the molecule is that of the
# optimized geometry at the
# `full-CI <https://en.wikipedia.org/wiki/Full_configuration_interaction>`_ level:
# :math:`-1.1373060483` Ha. You can print the optimized geometry and verify that the final bond
# length of hydrogen is identical to the one computed with full-CI which is :math:`1.3888`
# `Bohr <https://en.wikipedia.org/wiki/Bohr_radius>`_.
#
# We are now ready to perform a full optimization where the circuit parameters, the nuclear
# coordinates and the basis set parameters are all differentiable parameters that can be optimized
# simultaneously.

# initial values of the nuclear coordinates
geometry = np.array([[0.0, 0.0, -0.672943567415407],
                     [0.0, 0.0, 0.672943567415407]], requires_grad=True)

# initial values of the basis set exponents
alpha = np.array([[3.42525091, 0.62391373, 0.1688554],
                  [3.42525091, 0.62391373, 0.1688554]], requires_grad=True)

# initial values of the basis set contraction coefficients
coeff = np.array([[0.1543289673, 0.5353281423, 0.4446345422],
                  [0.1543289673, 0.5353281423, 0.4446345422]], requires_grad=True)

# initial value of the circuit parameter
circuit_param = [np.array([0.0], requires_grad=True)]

for n in range(36):

    args = [circuit_param, geometry, alpha, coeff]
    mol = qml.hf.Molecule(symbols, geometry, alpha=alpha, coeff=coeff)

    # gradient for circuit parameters
    g_param = grad(energy(mol), argnum=0)(*args)
    circuit_param = circuit_param - 0.25 * g_param[0]

    # gradient for nuclear coordinates
    forces = -grad(energy(mol), argnum=1)(*args)
    geometry = geometry + 0.5 * forces

    # gradient for basis set exponents
    g_alpha = grad(energy(mol), argnum=2)(*args)
    alpha = alpha - 0.25 * g_alpha

    # gradient for basis set contraction coefficients
    g_coeff = grad(energy(mol), argnum=3)(*args)
    coeff = coeff - 0.25 * g_coeff

    if n % 5 == 0:
        print(f'n: {n}, E: {energy(mol)(*args):.8f}, Force-max: {abs(forces).max():.8f}')

##############################################################################
# You can also print the gradients of the circuit and basis set parameters and confirm that they are
# approaching zero. The computed energy of :math:`-1.14040160` Ha is
# lower than the full-CI energy, :math:`-1.1373060483` Ha (obtained with the STO-3G basis set for
# the hydrogen molecule) because we have optimized the basis set parameters in our example. This
# means that we can reach a lower energy for hydrogen without increasing the basis set size which in
# principle leads to a larger number of qubits.
#
# Conclusions
# -----------
# This tutorial introduces an important feature of PennyLane that allows performing
# fully-differentiable Hartree-Fock and subsequently VQE simulations. This feature provides two
# major benefits: i) All gradient computations needed for parameter optimization can be carried out
# with the elegant methods of automatic differentiation which facilitates simultaneous optimizations
# of circuit and Hamiltonian parameters in applications such as VQE molecular geometry
# optimizations. ii) By optimizing the molecular parameters such as the exponent and contraction
# coefficients of Gaussian functions of the basis set, one can reach a lower energy without
# increasing the number of basis functions. Can you think of other interesting molecular parameters
# that can be optimized along with the nuclear coordinates and basis set parameters that we
# optimized in this tutorial?
#
# References
# ----------
#
# .. [#arrazola2021]
#
#     Juan Miguel Arrazola, Soran Jahangiri, Alain Delgado, Jack Ceroni *et al.*, "Differentiable
#     quantum computational chemistry with PennyLane". `arXiv:2111.09967
#     <https://arxiv.org/abs/2111.09967>`__
#
# .. [#szabo1996]
#
#     Attila Szabo, Neil S. Ostlund, "Modern Quantum Chemistry: Introduction to Advanced Electronic
#     Structure Theory". Dover Publications, 1996.

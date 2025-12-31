# Conceptual Differences between THAMES and VCCTL

## How phases are modeled

VCCTL defines the number of possible microstructure phases, and the integer id of those phases.
The compositions and names of all VCCTL phases are fixed. All of these are hard-coded into the
backend C programs.

THAMES uses the structure of the GEMS3 library, which defines matter at three
different levels:
1. **Independent Components (ICs)**: Elements in the periodic table and electric
   charge.
2. **Dependent Components (DCs)**: Composed of fixed numbers of different ICs.
   Examples include ions in solution like Ca+2, SO4-2, OH-, and also compounds with
   fixed composition, such as H2O (water), CaSO4 (anhydrite), Al2O3 (corundum).
3. **GEM Phases**: Composed of one or more DCs but can have variable mole fractions
   of those DCs. Examples are the aqueous electrolyte solution, C-S-H, and AFt

The possible ICs, DCs, and phases are provided in the thames-dch.dat data file
long with the relationships between them and some of their thermodynamic
properties.

The phases in THAMES are a user-defined subset of those in the thames-dch.dat
file. The user can name the phases however he chooses (although the user must
link the chosen phase name to the corresponding GEM phase).
The integer ID of most phase in THAMES can be assigned by the user (or hopefully
automatically by the UI).

In addition, the user may define concentrations of impurities in phases that
will be part of the initial microstructure, and the user may define
concentrations of impurities that will be incorporated into precipitated phases
during simulation, in terms of "partition coefficients" for that impurity in that
phase.

Finally, the user may also define any given phase to have some volume fraction
of porosity at a scale that is less than one voxel dimension. The most common
example is for C-S-H, which has interconnected porosity at the scale of tens of
nanometers, which is much smaller than the typical size of a voxel in the
microstructure.

All of these possibilities make the input file (JSON format) fairly complicated.

Despite this flexibility and increase in the number of phases available, the
thames hydration model ALWAYS requires two phases to be included in any
simulation:
1. A "void" phase which is the absence of any matter. This phase must be named
   "Void" and it must have integer ID = 0. The void phase is not defined as a
GEM phase but is needed by the hydration model to handle absence of any phase.
2. An aqueous electrolyte, which is the GEM phase named 'aq-gen'. This phase
must be named "Electrolyte" and it must have integer ID = 1.

## Kinetics
The VCCTL hydration model does not really have any kinetic aspect; the relative
probabilities of different reactions are hard-coded into the disrealnew program
without a definite time scale. The thames hydration model allows users to define
the kinetics of dissolution, nucleation, and growth according to one of three
models:
1. The Parrot-Killoh model, which can be applied to cement clinker phases
   (C3S, C2S, etc). It can be applied to other phases but usually is not.
   The Parrot-Killoh model requires the user to provide values for eight
   empirical parameters (k1, k2, k3, n1, n2, dorHcoeff, activationEnergy, and loi)
2. The "standard" model, which is based on fundamental chemical kinetic
   principles. It can be applied to any phase, whether dissolving or
precipitating. It requires the user to provide values for nine empirical
parameters (dissolutionRateConst, diffusionRateConstEarly,
diffusionRateConstLate, dissolvedUnits, siexp, dfexp, loi, and activationEnergy)
3. The "pozzolanic" model which is nearly the same as the "standard" model
except that it adds three more parameters the user must provide (sio2,
dorexp, and ohexp)

## Environmental conditions
VCCTL allows thermal conditions to be isothermal, adiabatic, or temperature
profile. In contrast, THAMES currently only allows isothermal, but I expect
to develop the other two options in the future.

VCCTL allows moisture conditions of "saturated" or "sealed". THAMES allows
"saturated" or "sealed" too. In addition, the user can define the concentrations
of different DCs in the initial electrolyte solution, either as initial
concentrations that will change as the system evolves, or as fixed
concentrations throughout the simulation.

## Thermodynamic data
Besides the user input file that will be created by the UI (JSON format), the
model also requires all the thermodynamic data for the phases, which is
currently in the three files thames-dch.dat, thames-dbr.dat, and thames-ipm.dat.
These three files, and a master file called thames-dat.lst, must be provided
as input becuase they are read in that format by the GEMS3 library to initiate
the thermodynamic system.

/**
@file  StandardKineticModel.cc
@brief Method definitions for the StandardKineticModel class.

*/
#include "StandardKineticModel.h"

using std::cout;
using std::endl;

StandardKineticModel::StandardKineticModel() {

  ///
  /// Default temperature in the PK model is 20 C (or 293 K)
  ///

  temperature_ = 293.15; // default temperature (K)
  refT_ = 293.15;        // default temperature (K)

  ///
  /// Default values for the rate constants
  ///

  dissolutionRateConst_ = 0.0;

  diffusionRateConstEarly_ = 2.0e-9;
  diffusionRateConstLate_ = 2.0e-9;

  ///
  /// Default value for the exponents in the rate equation
  ///

  siexp_ = 1.0;
  dfexp_ = 1.0;
  lossOnIgnition_ = 0.0;

  name_ = "";
  microPhaseId_ = 2;
  DCId_ = 2;
  GEMPhaseId_ = 2;
  activationEnergy_ = 0.0;
  scaledMass_ = 0.0;
  initScaledMass_ = 0.0;

  temperature_ = lattice_->getTemperature();
  double critporediam = lattice_->getLargestSaturatedPore(); // in nm
  critporediam *= 1.0e-9;                                    // in m
  rh_ = exp(-6.23527e-7 / critporediam / temperature_);
  rh_ = rh_ > 0.55 ? rh_ : 0.551;
  rhFactor_ = rh_;

  arrhenius_ = exp((activationEnergy_ / GASCONSTANT) *
                   ((1.0 / refT_) - (1.0 / temperature_)));

  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion hours or 114,000 years
  ///

  sulfateAttackTime_ = 1.0e10;
  leachTime_ = 1.0e10;

  return;
}

StandardKineticModel::StandardKineticModel(ChemicalSystem *cs, Lattice *lattice,
                                           struct KineticData &kineticData,
                                           const bool verbose,
                                           const bool warning) {

  // Set the verbose and warning flags

  verbose_ = verbose;
  warning_ = warning;
#ifdef DEBUG
  verbose_ = true;
  warning_ = true;
#else
  verbose_ = verbose;
  warning_ = warning;
#endif

  chemSys_ = cs;
  lattice_ = lattice;

  setDissolutionRateConst(kineticData.dissolutionRateConst);
  setSurfaceAreaMultiplier(kineticData.surfaceAreaMultiplier);
  setDissolvedUnits(kineticData.dissolvedUnits);
  setSiexp(kineticData.siexp);
  setDfexp(kineticData.dfexp);
  lossOnIgnition_ = kineticData.loi;

  // This is a kluge for now to avoid needing to change the input files again
  // For now we use values typical of calcium in bulk water at infinite dilution
  /// @todo Make these diffusion constants part of the input files

  diffusionRateConstEarly_ = 2.0e-9;
  diffusionRateConstLate_ = 2.0e-9;

  ///
  /// Default initial solid mass is 100 g
  ///

  initSolidMass_ = 100.0;

  temperature_ = kineticData.temperature;
  refT_ = kineticData.reftemperature;

  modelName_ = "StandardKineticModel";
  name_ = kineticData.name;
  microPhaseId_ = kineticData.microPhaseId;
  DCId_ = kineticData.DCId;
  GEMPhaseId_ = kineticData.GEMPhaseId;
  activationEnergy_ = kineticData.activationEnergy;
  scaledMass_ = kineticData.scaledMass;
  initScaledMass_ = kineticData.scaledMass;

  double critporediam = lattice_->getLargestSaturatedPore(); // in nm
  critporediam *= 1.0e-9;                                    // in m
  rh_ = exp(-6.23527e-7 / critporediam / temperature_);
  rh_ = rh_ > 0.55 ? rh_ : 0.551;
  rhFactor_ = rh_;

  arrhenius_ = exp((activationEnergy_ / GASCONSTANT) *
                   ((1.0 / refT_) - (1.0 / temperature_)));

  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion hours or 114,000 years
  ///

  sulfateAttackTime_ = 1.0e10;
  leachTime_ = 1.0e10;

  return;
}

void StandardKineticModel::calculateKineticStep(const double timestep,
                                                double &scaledMass,
                                                double &massChange, int cyc,
                                                double totalDOR) {
  ///
  /// Initialize local variables
  ///

  double surfacePrecipRate = 1.0e9; // Precipitation rate (positive for growth)
  double diffrate = 1.0e9;          // Default diffusion rate

  diffusionRateConstEarly_ = 2.0e-9;
  diffusionRateConstLate_ = 2.0e-9;

  double rate = 1.0e-10; // Selected rate

  ///
  /// Determine if this is a normal step or a necessary
  /// tweak from a failed GEM_run call
  ///

  try {

    // Each component has its own kinetic model
    // We want to know the *change* in DC moles caused by
    // this component's dissolution or growth.

    // RH factor is the same for all clinker phases
    /// This is a big kluge for internal relative humidity
    /// @note This whole comment block is out of place here.
    /// @todo Move this comment block to somewhere more appropriate
    /// @note Using new gel and interhydrate pore size distribution model
    ///       which is currently contained in the Lattice object.
    ///
    /// Surface tension of water is gamma = 0.072 J/m2
    /// Molar volume of water is Vm = 1.8e-5 m3/mole
    /// The Kelvin equation is
    ///    p/p0 = exp (-4 gamma Vm / d R T) = exp (-6.23527e-7 / (d T))
    ///
    ///    where d is the pore diameter in meters and T is absolute
    ///    temperature

    /// Assume a zero contact angle for now.
    /// @todo revisit the contact angle issue

    scaledMass_ = scaledMass;

    // JWB BEWARE: The new definition of area is truly a geometric calculation
    // made on the microstructure. It does not catch BET or internal surface
    // area if that ends up being important. The units of area are m2 per 100
    // g of intial total solid

    double area = lattice_->getSurfaceArea(microPhaseId_);

    // surfaceAreaMultiplier_ is a way to account for the influence
    // of subvoxel porosity that increases the total surface area in a voxel.

    area *= surfaceAreaMultiplier_;

    // Saturation index , but be sure that there is only one GEM Phase
    /// @note Assumes there is only one phase in this microstructure
    /// component
    /// @todo Generalize to multiple phases in a component (how?)

    double saturationIndex = chemSys_->getMicroPhaseSI(microPhaseId_);

    // dissolutionRateConst_ has units of mol/m2/h
    // area has units of m2 of phase per 100 g of total solid
    // Therefore surfacePrecipRate has units of mol of phase per 100 g of all
    // solid per h

    // This equation basically implements the Dove and Crerar rate
    // equation for quartz.  Needs to be calibrated for silica fume, but
    // hopefully the BET area and LOI will help do that.

    double baserateconst = dissolutionRateConst_;
    surfacePrecipRate = baserateconst * rhFactor_ * area *
                        pow(abs(pow(saturationIndex, siexp_) - 1.0), dfexp_);
    double signOf = (saturationIndex > 1.0) ? 1.0 : -1.0;
    surfacePrecipRate *= signOf;

    // GODZILLA
    // cout << endl << "===> Standard Model for " << name_ << " <===" << endl;
    // cout << "  baserateconst = " << baserateconst << endl
    //      << "  rhFactor_ = " << rhFactor_ << endl
    //      << "  saturationIndex = " << saturationIndex << endl
    //      << "  siexp_ = " << siexp_ << endl
    //      << "  dfexp_ = " << dfexp_ << endl
    //      << "======================><=========================" << endl;
    // cout.flush();
    // GODZILLA

    /// Check for diffusion as possible rate-controlling step
    /// Assume steady-state diffusion, with the surface being
    /// at equilibrium and the bulk being at the current
    /// saturation index.
    ///
    /// Also assume a particular, fixed boundary layer thickness
    /// through which diffusion occurs, like one micrometer

    double boundaryLayer = 1.0e-7; // Units of m

    double average_cgrad = 1.0;
    double average_cdiff = 1.0;
    if (abs(initScaledMass_ - scaledMass_) > 1.0e-6) {
      /// Below is very rough approximation to chemical potential gradient
      /// Would be better if we knew the equilibrium constant of
      /// the dissociation reaction.  We would need to raise
      /// it to the power 1/dissolvedUnits and then multiply
      /// it by average_cgrad.
      ///
      /// @todo Find a way to get Delta Gf from GEMS and then
      /// use it to calculate K
      ///
      // Gradient uses vector pointing AWAY from surfae as positive
      // Electrolyte assumed to be at equilibrium at the surface and
      // to have the bulk concentration at the boundary layer thickness

      double Keq = 1.0e-5;
      // average_cdiff has units of mol/dm3, so convert to mol/m3
      average_cdiff = 1000.0 * pow(Keq, (1.0 / dissolvedUnits_)) *
                      (pow(saturationIndex, (1.0 / dissolvedUnits_)) - 1.0);
      average_cgrad = average_cdiff / boundaryLayer;
      // Estimate diffusion rate TO the surface using the negative
      // of Fick's first law
      diffrate = diffusionRateConstEarly_ * (average_cgrad) / boundaryLayer;
      if (abs(diffrate) < 1.0e-10) {
        signOf = (std::signbit(diffrate)) ? -1.0 : 1.0;
        diffrate = signOf * 1.0e-10;
      }
    } else {
      signOf = (std::signbit(saturationIndex - 1.0)) ? -1.0 : 1.0;
      diffrate = signOf * 1.0e9;
    }

    // surfacePrecipRate has units of mol of phase per 100 g of solid per hour
    // timestep has units of hours
    // molar mass has units of grams per mole
    // Therefore, massChange has units of grams of phase per 100 g of all
    // solid

    /// @todo JWB Check to make sure that diffrate has same units as
    /// surfacePrecipRate

    rate = surfacePrecipRate;
    if (abs(diffrate) < abs(rate))
      rate = diffrate;

    rate *= arrhenius_;

    // Mass dissolved has units of g of phase per 100 g of all initial solid
    massChange = rate * timestep * chemSys_->getDCMolarMass(DCId_);

    if (verbose_) {
      cout << "    StandardKineticModel::calculateKineticStep "
              "surfacePrecipRate/massChange : "
           << surfacePrecipRate << " / " << massChange << endl;
    }

    scaledMass = scaledMass_ + massChange;

    if (scaledMass < 0.0) {
      massChange = -1.0 * scaledMass_;
      scaledMass = 0.0;
    }
    scaledMass_ = scaledMass;

    // GODZILLA
    // if (verbose_) {
    cout << endl
         << "  ********* SKM_hT = " << timestep << "    cyc = " << cyc
         << "*********" << endl
         << "    microPhaseId_ = " << microPhaseId_
         << "    microPhase = " << name_
         << "    GEMPhaseIndex = " << GEMPhaseId_ << endl;
    cout << "    rhFactor_: " << rhFactor_ << "    arrhenius_: " << arrhenius_
         << "    saturationIndex: " << saturationIndex << "    area: " << area
         << endl;
    cout << "   surfacePrecipRate: " << surfacePrecipRate << endl;
    cout << "   average_cdiff: " << average_cdiff << endl;
    cout << "   average_cgrad: " << average_cgrad << endl;
    cout << "   diffusionRateConstEarly_: " << diffusionRateConstEarly_ << endl;
    cout << "   diffrate: " << diffrate << endl;
    cout << "   rate: " << rate << endl;
    cout << "   initScaledMass_: " << initScaledMass_
         << "   scaledMass_: " << scaledMass_ << "   massChange: " << massChange
         << endl
         << "   Dc_a = " << chemSys_->getNode()->DC_a(DCId_) << endl;
    cout << "  ********* SKM_hT = " << timestep << "    cyc = " << cyc
         << "*********" << endl;
    cout.flush();
    // }
    // GODZILLA
  } catch (EOBException eex) {
    eex.printException();
    exit(1);
  } catch (DataException dex) {
    dex.printException();
    exit(1);
  } catch (FloatException flex) {
    flex.printException();
    exit(1);
  } catch (out_of_range &oor) {
    EOBException ex("StandardKineticModel", "calculateKineticStep", oor.what(),
                    0, 0);
    ex.printException();
    exit(1);
  }

  return;
}

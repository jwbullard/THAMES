/**
@file  PozzolanicModel.cc
@brief Method definitions for the PozzolanicModel class.

*/
#include "PozzolanicModel.h"

using std::cout;
using std::endl;

PozzolanicModel::PozzolanicModel() {

  ///
  /// Default temperature in the PK model is 20 C (or 293 K)
  ///

  temperature_ = 293.15; // default temperature (K)
  refT_ = 293.15;        // default temperature (K)

  ///
  /// Default values for the rate constants
  ///

  dissolutionRateConst_ = 0.0;
  diffusionRateConstEarly_ = 0.0;
  diffusionRateConstLate_ = 0.0;
  surfaceAreaMultiplier_ = 1.0;

  ///
  /// Default value for the exponents in the rate equation
  ///

  siexp_ = 1.0;
  dfexp_ = 1.0;
  ohexp_ = 0.0;
  sio2_ = 1.0;
  al2o3_ = cao_ = 0.0;
  lossOnIgnition_ = 0.0;

  name_ = "";
  microPhaseId_ = 2;
  DCId_ = 2;
  GEMPhaseId_ = 2;
  activationEnergy_ = 0.0;
  scaledMass_ = 0.0;
  initScaledMass_ = 0.0;

  // Units of specific surface area should be m2 per kg of solid
  // Reference is for an undensified silica fume
  refSpecificSurfaceArea_ = 1437.0392203;

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

PozzolanicModel::PozzolanicModel(ChemicalSystem *cs, Lattice *lattice,
                                 struct KineticData &kineticData,
                                 const bool verbose, const bool warning) {

  // Set the verbose and warning flags

  verbose_ = verbose;
  warning_ = warning;
#ifdef DEBUG
  verbose_ = true;
  warning_ = true;
  cout << "PozzolanicModel::PozzolanicModel Constructor sio2 value = "
       << kineticData.sio2 << endl;
  cout.flush();
#else
  verbose_ = verbose;
  warning_ = warning;
#endif

  chemSys_ = cs;
  lattice_ = lattice;

  setSio2(kineticData.sio2);
  setAl2o3(kineticData.al2o3);
  setCao(kineticData.cao);
  setSurfaceAreaMultiplier(kineticData.surfaceAreaMultiplier);
  setDissolutionRateConst(kineticData.dissolutionRateConst);
  setDiffusionRateConstEarly(kineticData.diffusionRateConstEarly);
  setDiffusionRateConstLate(kineticData.diffusionRateConstLate);
  setDissolvedUnits(kineticData.dissolvedUnits);
  setSiexp(kineticData.siexp);
  setDfexp(kineticData.dfexp);
  setOhexp(kineticData.ohexp);
  lossOnIgnition_ = kineticData.loi;

  ///
  /// Default initial solid mass is 100 g
  ///

  initSolidMass_ = 100.0;

  temperature_ = kineticData.temperature;
  refT_ = kineticData.reftemperature;

  modelName_ = "PozzolanicModel";
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

void PozzolanicModel::calculateKineticStep(const double timestep,
                                           double &scaledMass,
                                           double &massChange, int cyc,
                                           double totalDOR) {

  ///
  /// Initialize local variables
  ///

  double surfacePrecipRate = 1.0e9; // Precipitation rate (positive for growth)
  double diffrate = 1.0e9;          // Diffusion rate

  double rate = 1.0e-10; // Selected rate

  double DOR;

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
    /// @todo Revisit the contact angle issue once we account
    /// for the chemical potential difference of confined water
    /// in small pores

    scaledMass_ = scaledMass;

    if (initScaledMass_ > 0.0) {
      DOR = (initScaledMass_ - scaledMass_) / (initScaledMass_);
      // prevent DOR from prematurely stopping PK calculations
      // DOR = min(DOR, 0.99);
    } else {
      throw FloatException("PozzolanicModel", "calculateKineticStep",
                           "initScaledMass_ = 0.0");
    }

    double baserateconst = dissolutionRateConst_;

    /// @note The following influence alkali and alkali earth cations
    /// was asserted by Dove and Crerar (1990) but only at near-neutral pH

    double ca = chemSys_->getDCConcentration("Ca+2");
    double kca = 0.00144; // mol m-2 h-1 ads.
                          // rate const for Ca (guess)
    double Kca = 10.0;    // adsorption equilibrium
                          // constant is a guess
    double na = chemSys_->getDCConcentration("Na+");
    double kna = 0.002286; // mol m-2 h-1 ads. rate
                           // const from Dove and Crerar
    double Kna = 58.3;     // adsorption equilibrium
                           // constant from Dove and Crerar
    double k = chemSys_->getDCConcentration("K+");
    double kk = 0.002016; // mol m-2 h-1 ads. rate
                          // const from Dove and Crerar
    double Kk = 46.6;     // adsorption equilibrium constant
                          // from Dove and Crerar

    // Langmuir adsorption isotherms assumed to be additive

    baserateconst += (kca * Kca * ca / (1.0 + (Kca * ca)));
    baserateconst += (kna * Kna * na / (1.0 + (Kna * na)));
    baserateconst += (kk * Kk * k / (1.0 + (Kk * k)));

    double ohActivity = chemSys_->getDCActivity("OH-");

    // double area = (specificSurfaceArea_ / 1000.0) * scaledMass_; // m2

    // JWB BEWARE: The new definition of area is truly a geometric calculation
    // made on the microstructure. It does not catch BET surface area
    // if that ends up being important.
    // This area value has units of m2 per 100 g of initial solid
    double area = lattice_->getSurfaceArea(microPhaseId_);
    area *= surfaceAreaMultiplier_;

    // Saturation index , but be sure that there is only one GEM Phase
    /// @note Assumes there is only one phase in this microstructure
    /// component
    /// @todo Generalize to multiple phases in a component (how?)

    // double saturationIndex = solut_->getSI(GEMPhaseId_);
    double saturationIndex = chemSys_->getMicroPhaseSI(microPhaseId_);

    // activity of water
    double waterActivity = chemSys_->getDCActivity(chemSys_->getDCId("H2O@"));

    // This equation basically implements the Dove and Crerar rate
    // equation for quartz.  Needs to be calibrated for silica fume, but
    // hopefully the BET area and LOI will help do that.

    // baserateconst_ has units of mol/m2/h
    // area has units of m2 of phase per 100 g of total solid
    // Therefore surfacePrecipRate has units of mol of phase per 100 g of all
    // solid per h
    surfacePrecipRate =
        baserateconst * rhFactor_ * pow(ohActivity, ohexp_) * area *
        pow(waterActivity, 2.0) * (1.0 - (lossOnIgnition_ / 100.0)) *
        (sio2_)*pow((pow(saturationIndex, siexp_) - 1.0), dfexp_);

    /// Check for diffusion as possible rate-controlling step
    /// Assume steady-state diffusion, with the surface being
    /// at equilibrium and the bulk being at the current
    /// saturation index.
    ///
    /// Also assume a particular, fixed boundary layer thickness
    /// through which diffusion occurs, like one micrometer

    double boundaryLayer = 1.0;

    double average_cgrad = 1.0e9;
    double sgnof = 1.0;
    if (DOR > 0.0) {
      /// Below is very rough approximation to chemical potential gradient
      /// Would be better if we knew the equilibrium constant of
      /// the dissociation reaction.  We would need to raise
      /// it to the power 1/dissolvedUnits and then multiply
      /// it by average_cgrad.
      // Gradient uses vector pointing AWAY from surfae as positive
      // Electrolyte assumed to be at equilibrium at the surface and
      // to have the bulk concentration at the boundary layer thickness
      average_cgrad =
          (pow(saturationIndex, (1.0 / dissolvedUnits_)) - 1.0) / boundaryLayer;
      // Estimate diffusion rate TO the surface using the negative
      // of Fick's first law
      diffrate = diffusionRateConstEarly_ * (average_cgrad) / boundaryLayer;
      if (abs(diffrate) < 1.0e-10)
        sgnof = (std::signbit(diffrate)) ? -1.0 : 1.0;
      diffrate = sgnof * 1.0e-10;
    } else {
      sgnof = (std::signbit(saturationIndex - 1.0)) ? -1.0 : 1.0;
      diffrate = sgnof * 1.0e9;
    }

    // surfacePrecipRate has units of mol of phase per 100 g of all solid
    // per h
    /// @todo JWB Check to make sure that diffrate has same units as
    /// surfacePrecipRate

    rate = surfacePrecipRate;
    if (abs(diffrate) < abs(rate))
      rate = diffrate;

    rate *= arrhenius_;

    // Mass dissolved has units of g of phase per 100 g of all initial solid
    massChange = rate * timestep * chemSys_->getDCMolarMass(DCId_); //

    if (verbose_) {
      cout << "    PozzolanicModel::calculateKineticStep rate/massChange : "
           << rate << " / " << massChange << endl;
    }

    scaledMass = scaledMass_ + massChange;

    if (scaledMass < 0) {
      massChange = -1.0 * scaledMass_;
      scaledMass = 0.0;
    }
    scaledMass_ = scaledMass;

    if (verbose_) {
      cout << "  ****************** PZM_hT = " << timestep << "\tcyc = " << cyc
           << "\tmicroPhaseId_ = " << microPhaseId_
           << "    microPhase = " << name_
           << "\tGEMPhaseIndex = " << GEMPhaseId_ << " ******************"
           << endl;
      cout << "   PZM_hT   " << "rhFacto_r: " << rhFactor_
           << "\tarrhenius_: " << arrhenius_
           << "\tsaturationIndex: " << saturationIndex
           << "\twaterActivity: " << waterActivity << endl;
      cout << "   PZM_hT   " << "surfacePrecipRate: " << surfacePrecipRate
           << "\tdiffrate: " << diffrate << "\trate: " << rate << endl;
      cout << "   PZM_hT   " << "initScaledMass_: " << initScaledMass_
           << "\tscaledMass_: " << scaledMass_ << "\tmassChange: " << massChange
           << endl;
      cout.flush();
    }

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
    EOBException eex("PozzolanicModel", "calculateKineticStep", oor.what(), 0,
                     0);
    eex.printException();
    exit(1);
  }

  return;
}

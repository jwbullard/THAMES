/**
@file  StandardKineticModel.cc
@brief Method definitions for the StandardKineticModel class.

*/
#include "StandardKineticModel.h"

StandardKineticModel::StandardKineticModel() {

  ///
  /// Default value for specific surface area is 385 m<sup>2</sup>/kg
  ///

  specificSurfaceArea_ = 385.0;
  refSpecificSurfaceArea_ = 385.0; // reference specific surface area (m2/kg)
  ssaFactor_ = 1.0;

  ///
  /// Default temperature in the PK model is 20 C (or 293 K)
  ///

  temperature_ = 293.15; // default temperature (K)
  refT_ = 293.15;        // default temperature (K)

  ///
  /// Default values for the rate constants
  ///

  dissolutionRateConst_ = 0.0;

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

  T_ = lattice_->getTemperature();
  double critporediam = lattice_->getLargestSaturatedPore(); // in nm
  critporediam *= 1.0e-9;                                    // in m
  rh_ = exp(-6.23527e-7 / critporediam / T_);
  rh_ = rh_ > 0.55 ? rh_ : 0.551;
  rhFactor_ = rh_;

  arrhenius_ =
      exp((activationEnergy_ / GASCONSTANT) * ((1.0 / refT_) - (1.0 / T_)));

  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion days or 27 million years
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

  ///
  /// Default value for specific surface area in PK model is 385
  /// m<sup>2</sup>/kg
  ///

  specificSurfaceArea_ = kineticData.specificSurfaceArea;
  refSpecificSurfaceArea_ = kineticData.refSpecificSurfaceArea;
  ssaFactor_ = specificSurfaceArea_ / refSpecificSurfaceArea_;
  setDissolutionRateConst(kineticData.dissolutionRateConst);
  setDissolvedUnits(kineticData.dissolvedUnits);
  setSiexp(kineticData.siexp);
  setDfexp(kineticData.dfexp);
  lossOnIgnition_ = kineticData.loi;

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

  T_ = lattice_->getTemperature();
  double critporediam = lattice_->getLargestSaturatedPore(); // in nm
  critporediam *= 1.0e-9;                                    // in m
  rh_ = exp(-6.23527e-7 / critporediam / T_);
  rh_ = rh_ > 0.55 ? rh_ : 0.551;
  rhFactor_ = rh_;

  arrhenius_ =
      exp((activationEnergy_ / GASCONSTANT) * ((1.0 / refT_) - (1.0 / T_)));


  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion days or 27 million years
  ///

  sulfateAttackTime_ = 1.0e10;
  leachTime_ = 1.0e10;

  return;
}

void StandardKineticModel::calculateKineticStep(const double timestep,
                                                double &scaledMass,
                                                double &massDissolved, int cyc,
                                                double totalDOR) {

  ///
  /// Initialize local variables
  ///

  double dissrate = 1.0e9; // Nucleation and growth rate

  double DOR, newDOR;

  ///
  /// Determine if this is a normal step or a necessary
  /// tweak from a failed GEM_run call
  ///

  try {

    // if (timestep < leachTime_ && timestep < sulfateAttackTime_) {

    // @todo BULLARD PLACEHOLDER
    // Still need to implement constant gas phase composition
    // Will involve equilibrating gas with aqueous solution
    //
    // First step each iteration is to equilibrate gas phase
    // with the electrolyte, while forbidding anything new
    // from precipitating.

    // RH factor is the same for all clinker phases
    // double vfvoid = lattice_->getVolumefraction(VOIDID);
    // double vfh2o = lattice_->getVolumefraction(ELECTROLYTEID);

    /// This is a big kluge for internal relative humidity
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

    if (initScaledMass_ > 0.0) {
      DOR = (initScaledMass_ - scaledMass_) / initScaledMass_;
      // prevent DOR from prematurely stopping PK calculations
      // DOR = min(DOR, 0.99);
    } else {
      throw FloatException("StandardKineticModel", "calculateKineticStep",
                           "initScaledMass_ = 0.0");
    }

    if (DOR < 0.0) {
      cout << endl << "    StandardKineticModel::calculateKineticStep - for cyc = " << cyc
           << "  => negative DOR : DOR = " << DOR << "  &  initScaledMass_/scaledMass_ : "
           << initScaledMass_ << " / " << scaledMass_ << endl;
      cout<< "        microPhaseId_ = " << microPhaseId_ << "    microPhase = " << name_
          << "    GEMPhaseIndex = " << GEMPhaseId_ << "    DCId_ = " << DCId_ << endl;
    }

    // if (DOR < 1.0) { //test!

      double area = (specificSurfaceArea_ / 1000.0) * scaledMass_; // m2

      // Saturation index , but be sure that there is only one GEM Phase
      /// @note Assumes there is only one phase in this microstructure
      /// component
      /// @todo Generalize to multiple phases in a component (how?)

      double saturationIndex = chemSys_->getMicroPhaseSI(microPhaseId_);

      // This equation basically implements the Dove and Crerar rate
      // equation for quartz.  Needs to be calibrated for silica fume, but
      // hopefully the BET area and LOI will help do that.

      if (saturationIndex < 1.0) {
        dissrate = dissolutionRateConst_ * area *
                   pow((1.0 - pow(saturationIndex, siexp_)), dfexp_);
      } else {
        dissrate = -dissolutionRateConst_ * area *
                   pow((pow(saturationIndex, siexp_) - 1.0), dfexp_);
      }

      double dissrate_ini = dissrate;

      dissrate *= (rhFactor_ * arrhenius_);

      massDissolved = dissrate * timestep * chemSys_->getDCMolarMass(DCId_); //

      if (verbose_) {
        cout << "    StandardKineticModel::calculateKineticStep dissrate/massDissolved : "
             << dissrate << " / " << massDissolved << endl;
      }

      scaledMass = scaledMass_ - massDissolved;

      if (scaledMass < 0) {
        massDissolved = scaledMass_;
        scaledMass = 0;
      }
      scaledMass_ = scaledMass;

      //scaledMass_ = max(scaledMass_ - massDissolved, 0.0);

      // newDOR = (initScaledMass_ - scaledMass_) / initScaledMass_;

      //scaledMass = scaledMass_;

      if (verbose_) {
        newDOR = (initScaledMass_ - scaledMass_) / initScaledMass_;
        cout << "  ****************** SKM_hT = " << timestep << "    cyc = " << cyc
             << "    microPhaseId_ = " << microPhaseId_
             << "    microPhase = " << name_
             << "    GEMPhaseIndex = " << GEMPhaseId_ << " ******************"
             << endl;
        cout << "   SKM_hT   " << "rhFactor_: " << rhFactor_
             << "\tarrhenius_: " << arrhenius_
             << "\tsaturationIndex: " << saturationIndex << "\tarea: " << area
             << endl;
        cout << "   SKM_hT   " << "dissrate_ini: " << dissrate_ini
             << "\tdissrate: " << dissrate << endl;
        cout << "   SKM_hT   " << "DOR: " << DOR << "\tnewDOR: " << newDOR
             << "\tinitScaledMass_: " << initScaledMass_
             << "\tscaledMass_: " << scaledMass_
             << "\tmassDissolved: " << massDissolved << endl;
        cout << "   cyc = " << cyc << "    microPhaseId_ = " << microPhaseId_
             << "    microPhaseName = " << name_
             << "    saturationIndex = " << saturationIndex << "   Dc_a = "
             << chemSys_->getNode()->DC_a(DCId_)
             // << "   SI_["
             << endl;
        cout.flush();
      }
    // } else {
    //   throw DataException("StandardKineticModel", "calculateKineticStep",
    //                       "DOR >= 1.0");
    // }

    //} // End of normal hydration block
  } // End of try block

  catch (EOBException eex) {
    eex.printException();
    exit(1);
  } catch (DataException dex) {
    dex.printException();
    exit(1);
  } catch (FloatException fex) {
    fex.printException();
    exit(1);
  } catch (out_of_range &oor) {
    EOBException ex("StandardKineticModel", "calculateKineticStep", oor.what(),
                    0, 0);
    ex.printException();
    exit(1);
  }

  return;
}


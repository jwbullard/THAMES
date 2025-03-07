/**
@file  KineticController.cc
@brief Method definitions for the KineticController class.

*/
#include "KineticController.h"

KineticController::KineticController() {
  temperature_ = 293.15;

  // default temperature (K)
  refT_ = 293.15;

  ///
  /// Clear out the vectors so they can be populated with values from the
  ///

  numPhases_ = 0;
  chemSys_ = NULL;
  lattice_ = NULL;
  phaseKineticModel_.clear();
  name_.clear();
  initScaledMass_.clear();
  scaledMass_.clear();
  specificSurfaceArea_.clear();
  refSpecificSurfaceArea_.clear();
  isKinetic_.clear();
  // waterId_ = 1;
  ICNum_ = 0;
  ICName_.clear();
  DCNum_ = 0;
  DCName_.clear();
  GEMPhaseNum_ = 0;

  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion days or 27 million years
  ///

  sulfateAttackTime_ = 1.0e10;
  leachTime_ = 1.0e10;

  verbose_ = warning_ = false;

  return;
}

KineticController::KineticController(ChemicalSystem *cs, Lattice *lattice,
                                     const string &fileName, const bool verbose,
                                     const bool warning)
    : chemSys_(cs), lattice_(lattice) {
  ///
  /// Clear out the vectors so they can be populated with values from the
  ///

  numPhases_ = 0;
  phaseKineticModel_.clear();
  name_.clear();
  isKinetic_.clear();

  // Set the verbose and warning flags

#ifdef DEBUG
  verbose_ = true;
  warning_ = true;
  cout << "KineticController::KineticController Constructor" << endl;
  cout.flush();
#else
  verbose_ = verbose;
  warning_ = warning;
#endif

  ///
  /// Default temperature in the PK model is 20 C (or 293 K)
  ///

  temperature_ = 293.15;
  refT_ = 293.15;

  ///
  /// Clear out the vectors so they can be populated with values from the
  /// XML input file
  ///

  name_.clear();
  microPhaseId_.clear();

  ///
  /// The default is to not have sulfate attack or leaching, so we set the
  /// default time for initiating these simulations to an absurdly large value:
  /// 10 billion days or 27 million years
  ///

  sulfateAttackTime_ = 1.0e10;
  leachTime_ = 1.0e10;

  ///
  /// Open the input XML file for kinetic data and parse it
  ///

  string xmlext = ".xml";
  size_t foundxml;
  foundxml = fileName.find(xmlext);
  try {
    if (foundxml != string::npos) {
      if (verbose_) {
        cout << "KineticModel data file is an XML file" << endl;
      }
      parseDoc(fileName);
    } else {
      throw FileException("KineticModel", "KineticModel", fileName,
                          "NOT in XML format");
    }
  } catch (FileException fex) {
    fex.printException();
    exit(1);
  }

  int microPhaseId;

  if (verbose_) {
    cout << "KineticController::KineticController Finished reading "
            "chemistry.xml "
         << endl;
    int size = microPhaseId_.size();
    for (int i = 0; i < size; ++i) {
      microPhaseId = microPhaseId_[i];
      if (isKinetic_[i]) {
        cout << "KineticController::KineticController kinetic phase "
             << microPhaseId << endl;
        cout << "KineticController::KineticController     name = "
             << chemSys_->getMicroPhaseName(microPhaseId) << endl;
      }
    }
    cout.flush();
  }

  // Assign the DC index for water

  // waterId_ = chemSys_->getDCId(WaterDCName);
  ICNum_ = chemSys_->getNumICs();
  DCNum_ = chemSys_->getNumDCs();
  ICName_ = chemSys_->getICName();
  DCName_ = chemSys_->getDCName();
  GEMPhaseNum_ = chemSys_->getNumGEMPhases();

  ICMoles_.resize(ICNum_, 0.0);
  ICMolesTot_.resize(ICNum_, 0.0);
  DCMoles_.resize(DCNum_, 0.0);
  DCMolesIni_.resize(DCNum_, 0.0);

  calcPhaseMasses();

  // initScaledCementMass_ = chemSys_->getInitScaledCementMass();

  pKMsize_ = phaseKineticModel_.size();
  impurity_K2O_.resize(pKMsize_, 0);
  impurity_Na2O_.resize(pKMsize_, 0);
  impurity_Per_.resize(pKMsize_, 0);
  impurity_SO3_.resize(pKMsize_, 0);

  impurityDCID_.clear();
  impurityDCID_.push_back(chemSys_->getDCId("K2O"));
  impurityDCID_.push_back(chemSys_->getDCId("Na2O"));
  impurityDCID_.push_back(chemSys_->getDCId("Per")); // 170
  impurityDCID_.push_back(chemSys_->getDCId("SO3"));

  //initScaledMass_, scaledMass_ & scaledMassIni_ are
  //initialized in KineticController::parseMicroPhase :
  //initScaledMass_.push_back(0.0);
  //scaledMass_.push_back(0.0);
  //scaledMassIni_.push_back(0.0);

  string modelName;
  int phID;
  initScaledCementMass_ = 0;
  cout << endl << "KineticController::KineticController - only these phases "
                  "(controlled by the Parrot-Killoh model)" << endl;
  cout << "                                       contribute to "
          "initScaledCementMass_ & scaledCementMass_ :" << endl;

  for (int i; i < pKMsize_; i++) {
    modelName = phaseKineticModel_[i]->getModelName();
    // cout << endl << "    modelName = " << modelName << endl;
    if (modelName == "ParrotKillohModel") {
      phID = phaseKineticModel_[i]->getMicroPhaseId();
      initScaledCementMass_ += chemSys_->getMicroPhaseMass(phID);
      cout << "      microPhaseID/microPhaseName/microPhaseMass : "
           << setw(3) << right << phID << " / "
           << setw(15) << left << phaseKineticModel_[i]->getName()
           << " / " << chemSys_->getMicroPhaseMass(phID) << " g" << endl;
      chemSys_->setIsParrotKilloh(phID);
    }
  }
  cout << endl << "      initScaledCementMass_ = " <<  initScaledCementMass_
       << " g (same value for scaledCementMass_)" << endl;
  chemSys_->setInitScaledCementMass(initScaledCementMass_);

  hyd_time_ini_ = 0;

  return;
}

KineticController::~KineticController() {
  for (int midx = 0; midx < pKMsize_; ++midx) {
    delete phaseKineticModel_[midx];
  }
}

void KineticController::parseDoc(const string &docName) {
  int numEntry = -1; // Tracks number of solid phases
  int testgemid;

  ///
  /// The kineticData structure is used to temporarily hold parsed data
  /// for a given phase before the data are loaded permanently into class
  /// members.
  ///

  struct KineticData kineticData;

  ///
  /// This method uses the libxml library, so it needs to be added and linked
  /// at compile time.
  ///

  xmlDocPtr doc;
  xmlChar *key;
  xmlNodePtr cur;

  cout.flush();
  doc = xmlParseFile(docName.c_str());

  ///
  /// Check if the xml file is valid and parse it if so.
  /// @note This block requires schema file to be local

  try {
    string rxcsd = "chemistry.xsd";
    if (!is_xml_valid(doc, rxcsd.c_str())) {
      throw FileException("KineticModel", "KineticModel", docName,
                          "xml NOT VALID");
    }

    if (doc == NULL) {
      throw FileException("KineticModel", "KineticModel", docName,
                          "xml NOT parsed successfully");
    }

    cur = xmlDocGetRootElement(doc);

    if (cur == NULL) {
      xmlFreeDoc(doc);
      throw FileException("KineticModel", "KineticModel", docName,
                          "xml document is empty");
    }

    cur = cur->xmlChildrenNode;
    while (cur != NULL) {
      if ((!xmlStrcmp(cur->name, (const xmlChar *)"temperature"))) {
        key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
        string st((char *)key);
        from_string(temperature_, st);
        xmlFree(key);
      } else if ((!xmlStrcmp(cur->name, (const xmlChar *)"reftemperature"))) {
        key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
        string st((char *)key);
        from_string(refT_, st);
        xmlFree(key);
      } else if ((!xmlStrcmp(cur->name, (const xmlChar *)"phase"))) {

        /// Each phase is a more complicated grouping of data that
        /// has a separate method for parsing.

        parseMicroPhase(doc, cur, numEntry, kineticData);
      }
      cur = cur->next;
    }

    /// Push a copy of the isKinetic vector to the ChemicalSystem

    chemSys_->setIsKinetic(isKinetic_);

    xmlFreeDoc(doc);
    xmlFreeNode(cur);
  } catch (FileException fex) {
    fex.printException();
    exit(1);
  }

  /// All kinetic components have been parsed now.  Next, this block tries
  /// to handle pozzolanic effects (loi, SiO2 content, etc.) on any other
  /// kinetic phases

  setPozzEffectOnPK();

  return;
}

void KineticController::parseMicroPhase(xmlDocPtr doc, xmlNodePtr cur,
                                        int &numEntry,
                                        struct KineticData &kineticData) {
  xmlChar *key;
  int proposedgemphaseid, proposedDCid;
  int testgemid, testdcid;
  string testname;
  bool kineticfound = false;
  bool ispozz = false;
  bool isParrotKilloh = false;
  bool istherm = false;
  bool issol = false;

  initKineticData(kineticData);

  cur = cur->xmlChildrenNode;

  isKinetic_.push_back(false);

  while (cur != NULL) {
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"thamesname"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string testname((char *)key);
      kineticData.name = testname;
      kineticData.microPhaseId = chemSys_->getMicroPhaseId(testname);
      xmlFree(key);
    }
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"kinetic_data"))) {
      numEntry += 1;
      kineticfound = true;
      isKinetic_[isKinetic_.size() - 1] = true;
      kineticData.GEMPhaseId =
          chemSys_->getMicroPhaseToGEMPhase(kineticData.microPhaseId, 0);
      kineticData.DCId =
          chemSys_->getMicroPhaseDCMembers(kineticData.microPhaseId, 0);

      ///
      /// Kinetic data are grouped together,
      /// so there is a method written just for parsing that grouping
      ///

      parseKineticData(doc, cur, kineticData);
    }

    cur = cur->next;
  }

  if (kineticfound) {
    kineticData.scaledMass =
        chemSys_->getMicroPhaseMass(kineticData.microPhaseId);
    kineticData.temperature = temperature_;
    kineticData.reftemperature = refT_;
    makeModel(doc, cur, kineticData);
  }

  /// Some items should be added to vectors whether kinetically controlled or
  /// not

  name_.push_back(kineticData.name);
  microPhaseId_.push_back(kineticData.microPhaseId);
  initScaledMass_.push_back(0.0);
  scaledMass_.push_back(0.0);
  scaledMassIni_.push_back(0.0);

  return;
}

void KineticController::parseKineticData(xmlDocPtr doc, xmlNodePtr cur,
                                         struct KineticData &kineticData) {
  bool typefound = false;
  xmlChar *key;
  cur = cur->xmlChildrenNode;

  try {
    while (cur != NULL) {
      if ((!xmlStrcmp(cur->name, (const xmlChar *)"type"))) {
        key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
        string st((char *)key);
        kineticData.type = st;
        if (kineticData.type == ParrotKillohType) {
          typefound = true;
          parseKineticDataForParrotKilloh(doc, cur, kineticData);
        } else if (kineticData.type == StandardType) {
          typefound = true;
          parseKineticDataForStandard(doc, cur, kineticData);
        } else if (kineticData.type == PozzolanicType) {
          typefound = true;
          parseKineticDataForPozzolanic(doc, cur, kineticData);
        } else {
          xmlFree(key);
          throw HandleException("KineticController", "parseKineticData", "type",
                                "Model type not found");
        }
        xmlFree(key);
      }
      cur = cur->next;
    }

    if (!typefound) {
      xmlFree(key);
      throw HandleException("KineticController", "parseKineticData", "type",
                            "Model type not specified");
    }
  } catch (HandleException hex) {
    xmlFree(key);
    hex.printException();
  }

  return;
}

void KineticController::parseKineticDataForParrotKilloh(
    xmlDocPtr doc, xmlNodePtr cur, struct KineticData &kineticData) {
  xmlChar *key;
  cur = cur->next;

  if (verbose_) {
    cout << "--->Parsing PK data for " << kineticData.name << endl;
    cout.flush();
  }
  while (cur != NULL) {

    // Specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"specificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.specificSurfaceArea, st);
      xmlFree(key);
    }
    // Reference specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"refSpecificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.refSpecificSurfaceArea, st);
      xmlFree(key);
    }
    // Parrot-Killoh k1 parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"k1"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.k1, st);
      xmlFree(key);
    }
    // Parrot-Killoh k2 parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"k2"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.k2, st);
      xmlFree(key);
    }
    // Parrot-Killoh k3 parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"k3"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.k3, st);
      xmlFree(key);
    }
    // Parrot-Killoh n1 parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"n1"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.n1, st);
      xmlFree(key);
    }
    // Parrot-Killoh n3 parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"n3"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.n3, st);
      xmlFree(key);
    }
    // Parrot-Killoh DOR_Hcoeff parameter
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dorHcoeff"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dorHcoeff, st);
      xmlFree(key);
    }
    // Activation energy
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"activationEnergy"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.activationEnergy, st);
      xmlFree(key);
    }
    cur = cur->next;
  }

  return;
}

void KineticController::parseKineticDataForStandard(
    xmlDocPtr doc, xmlNodePtr cur, struct KineticData &kineticData) {
  xmlChar *key;
  cur = cur->next;

  if (verbose_) {
    cout << "--->Parsing standard kinetic data for " << kineticData.name
         << endl;
    cout.flush();
  }
  while (cur != NULL) {

    // Specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"specificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.specificSurfaceArea, st);
      xmlFree(key);
    }

    // Reference specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"refSpecificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.refSpecificSurfaceArea, st);
      xmlFree(key);
    }

    // Dissolution rate constant (mol/m2/s)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dissolutionRateConst"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dissolutionRateConst, st);
      xmlFree(key);
    }
    // Number of DC units produced in dissociation reaction
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dissolvedUnits"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dissolvedUnits, st);
      xmlFree(key);
    }
    // Exponent on  the saturation index in the rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"siexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.siexp, st);
      xmlFree(key);
    }
    // Exponent on  the driving force term in the rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dfexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dfexp, st);
      xmlFree(key);
    }
    // Loss on ignition of the material
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"loi"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.loi, st);
      xmlFree(key);
    }
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"activationEnergy"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.activationEnergy, st);
      xmlFree(key);
    }
    cur = cur->next;
  }

  return;
}

void KineticController::parseKineticDataForPozzolanic(
    xmlDocPtr doc, xmlNodePtr cur, struct KineticData &kineticData) {
  xmlChar *key;
  cur = cur->next;

  if (verbose_) {
    cout << "--->Parsing pozzolanic data for " << kineticData.name << endl;
    cout.flush();
  }
  while (cur != NULL) {

    // Specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"specificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.specificSurfaceArea, st);
      xmlFree(key);
    }

    // Reference specific surface area (m2/kg)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"refSpecificSurfaceArea"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.refSpecificSurfaceArea, st);
      xmlFree(key);
    }

    // Dissolution rate constant (mol/m2/s)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dissolutionRateConst"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dissolutionRateConst, st);
      xmlFree(key);
    }
    // Early-age diffusion rate constant (mol/m2/s)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"diffusionRateConstEarly"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.diffusionRateConstEarly, st);
      xmlFree(key);
    }
    // Number of DC units produced in dissociation reaction
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dissolvedUnits"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dissolvedUnits, st);
      xmlFree(key);
    }
    // Later-age diffusion rate constant (mol/m2/s)
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"diffusionRateConstLate"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.diffusionRateConstLate, st);
      xmlFree(key);
    }
    // Exponent on  the saturation index in the rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"siexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.siexp, st);
      xmlFree(key);
    }
    // Exponent on  the driving force term in the rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dfexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dfexp, st);
      xmlFree(key);
    }
    // Exponent on  the degree of reaction term in the diffusion rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"dorexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.dorexp, st);
      xmlFree(key);
    }
    // Exponent on  the hydroxy ion activity in the rate equation
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"ohexp"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.ohexp, st);
      xmlFree(key);
    }
    // SiO2 mass fraction in the material
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"sio2"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.sio2, st);
      xmlFree(key);
    }
    // Al2O3 mass fraction in the material
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"al2o3"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.al2o3, st);
      xmlFree(key);
    }
    // CaO mass fraction in the material
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"cao"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.cao, st);
      xmlFree(key);
    }
    // Loss on ignition of the material
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"loi"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.loi, st);
      xmlFree(key);
    }
    if ((!xmlStrcmp(cur->name, (const xmlChar *)"activationEnergy"))) {
      key = xmlNodeListGetString(doc, cur->xmlChildrenNode, 1);
      string st((char *)key);
      from_string(kineticData.activationEnergy, st);
      xmlFree(key);
    }
    cur = cur->next;
  }

  return;
}

void KineticController::calcPhaseMasses(void) {
  int microPhaseId;
  double pscaledMass = 0.0;

  int size = microPhaseId_.size();

  for (int i = 0; i < size; i++) {
    microPhaseId = microPhaseId_[i];
    if (microPhaseId != VOIDID && microPhaseId != ELECTROLYTEID) {
      pscaledMass = chemSys_->getMicroPhaseMass(microPhaseId);
      scaledMass_[i] = pscaledMass;
      initScaledMass_[i] = pscaledMass;
      scaledMassIni_[i] = pscaledMass;

      // Setting the phase mass will also automatically calculate the phase volume

      if (verbose_) {
        cout << "KineticController::getPhaseMasses reads solid micphase mass of "
             << chemSys_->getMicroPhaseName(microPhaseId) << " as "
             << initScaledMass_[i] << endl;
        cout.flush();
      }
    }
  }

  return;
}

double KineticController::getSolidMass(void) {
  int microPhaseId;
  double totmass = 0.0;
  int size = microPhaseId_.size();
  for (int i = 0; i < size; i++) {
    microPhaseId = microPhaseId_[i];
    if (microPhaseId != VOIDID && microPhaseId != ELECTROLYTEID) {
      totmass += chemSys_->getMicroPhaseMass(microPhaseId);
    }
  }

  return (totmass);
}

void KineticController::makeModel(xmlDocPtr doc, xmlNodePtr cur,
                                  struct KineticData &kineticData) {
  KineticModel *km = NULL;

  if (kineticData.type == ParrotKillohType) {
    // Read remaining Parrot and Killoh model parameters
    km = new ParrotKillohModel(chemSys_, lattice_, kineticData, verbose_,
                               warning_);
  } else if (kineticData.type == StandardType) {
    // Read remaining pozzolanic model parameters
    km = new StandardKineticModel(chemSys_, lattice_, kineticData, verbose_,
                                  warning_);
  } else if (kineticData.type == PozzolanicType) {
    // Read remaining pozzolanic model parameters
    km = new PozzolanicModel(chemSys_, lattice_, kineticData, verbose_,
                             warning_);
  }

  phaseKineticModel_.push_back(km);

  return;
}

void KineticController::setPozzEffectOnPK(void) {

  /// @todo This is the block where the influence of some components on the
  /// kinetic parameters of other components can be set.

  double refloi = 0.8;
  double loi = refloi;
  double maxloi = refloi;
  double fillareaeff = 1.0;
  double sio2val = 0.94;
  double refsio2val = 0.94;
  double betval = 29.0;
  double refbetval = 29.0;
  // double minpozzeffect = 1000.0;
  double minpozzeffect = 1.0;
  double pozzeffect = 1.0;

  int size = phaseKineticModel_.size();

  for (int midx = 0; midx < size; ++midx) {
    loi = phaseKineticModel_[midx]->getLossOnIgnition();
    if (loi > maxloi)
      maxloi = loi;
    if (phaseKineticModel_[midx]->getType() == PozzolanicType) {
      sio2val = phaseKineticModel_[midx]->getSio2();
      betval = phaseKineticModel_[midx]->getSpecificSurfaceArea();
      refbetval = phaseKineticModel_[midx]->getRefSpecificSurfaceArea();
      pozzeffect = pow((sio2val / refsio2val), 2.0) * (betval / refbetval);
      if (pozzeffect < minpozzeffect)
        minpozzeffect = pozzeffect;
      cout << endl << "KineticController::setPozzEffectOnPK for midx = " << midx
           << " (microPhaseId =  " << phaseKineticModel_[midx]->getMicroPhaseId()
           << ", microPhaseName = " << phaseKineticModel_[midx]->getName() << endl;

      cout << "  Ref LOI = " << refloi << endl;
      cout << "  LOI     = " << loi << endl;
      cout << "  Max LOI = " << maxloi << endl;
      cout << "  SiO2     = " << sio2val << endl;
      cout << "  Ref SiO2 = " << refsio2val << endl;
      cout << "  BET      = " << betval << endl;
      cout << "  Ref BET  = " << refbetval << endl;
      cout << "  Pozz Effect     = " << pozzeffect << endl;
      cout << "  Min Pozz Effect = " << minpozzeffect << endl;
      cout.flush();
    }
  }

  minpozzeffect *= (refloi / maxloi);

  /// The way this is set up, 0.0 <= refloi / maxloi <= 1.0
  for (int midx = 0; midx < size; ++midx) {
    if (phaseKineticModel_[midx]->getType() == ParrotKillohType) {
      phaseKineticModel_[midx]->setPfk(minpozzeffect);
    }
  }

  return;
}

void KineticController::calculateKineticStep(const double timestep,
                                             int cyc) {
  ///
  /// Initialize local variables
  ///
  ///

  int i;

  // double massDissolved = 0.0;
  cout << scientific << setprecision(15);
  ///
  /// Determine if this is a normal step or a necessary
  /// tweak from a failed GEM_run call
  ///

  //vector<int> impurityDCID;
  //impurityDCID.clear();
  //impurityDCID.push_back(chemSys_->getDCId("K2O"));
  //impurityDCID.push_back(chemSys_->getDCId("Na2O"));
  //impurityDCID.push_back(chemSys_->getDCId("Per")); // 170
  //impurityDCID.push_back(chemSys_->getDCId("SO3"));

  // cout << endl << "impurityDCID : " << endl;
  // for(i = 0; i < chemSys_->getNumMicroImpurities(); i++){
  //     cout << i << "\t" << impurityDCID[i] << endl; cout.flush();
  // }
  // cout << endl ;

  double totMassImpurity, massImpurity;

  int DCId;
  //int pKMsize = phaseKineticModel_.size();
  //static vector<double> scaledMassIni;
  double keepNumDCMoles;
  vector<int> phaseDissolvedId;
  phaseDissolvedId.resize(pKMsize_, 0);
  double numDCMolesDissolved, scaledMass, massDissolved;

  // static double hyd_time_ini = 0.0;
  double hyd_time = 0.0;

  for (i = 0; i < ICNum_; i++) {
    ICMoles_[i] = 0.0;
  }

  bool doTweak = (chemSys_->getTimesGEMFailed() > 0) ? true : false;

  if (doTweak) {
    hyd_time = hyd_time_ini_ + timestep;
    if (verbose_) {
      cout << endl
           << "  KineticController::calculateKineticStep - tweak cyc = " << cyc
           << " :  hyd_time = " << hyd_time << "   hyd_time_ini_ = " << hyd_time_ini_
           << "   timestep = " << timestep << endl;
    }
    for (int midx = 0; midx < pKMsize_; ++midx) {
      phaseDissolvedId[midx] = phaseKineticModel_[midx]->getMicroPhaseId();
      chemSys_->setMicroPhaseMass(phaseDissolvedId[midx], scaledMassIni_[midx]);

      if (verbose_) {
        cout << "    midx = " << midx << "     scaledMassIni[midx] = " << scaledMassIni_[midx]
             << "     microPhaseName = " << phaseKineticModel_[midx]->getName()
             << endl;
      }
    }

    for (i = 0; i < DCNum_; i++) {
      DCMoles_[i] = DCMolesIni_[i];
    }

  } else {

    hyd_time = hyd_time_ini_ + timestep;
    cout << endl
         << "  KineticController::calculateKineticStep - cyc = " << cyc
         << " :  hyd_time = " << hyd_time
         << "   hyd_time_ini_ = " << hyd_time_ini_ << "   timestep = " << timestep
         << endl;

    for (int midx = 0; midx < pKMsize_; ++midx) {
      phaseDissolvedId[midx] = phaseKineticModel_[midx]->getMicroPhaseId();
      scaledMassIni_[midx] = chemSys_->getMicroPhaseMass(phaseDissolvedId[midx]);
      if (verbose_) {
        cout << "    midx = " << midx << "     scaledMassIni[midx] = " << scaledMassIni_[midx]
             << "     microPhaseName = " << phaseKineticModel_[midx]->getName()
             << endl;
      }
    }

    for (i = 0; i < DCNum_; i++) {
      DCMoles_[i] = chemSys_->getDCMoles(i);
      DCMolesIni_[i] = DCMoles_[i];
    }
  }

  try {
    // cout << "  KineticController::calculateKineticStep     hyd_time = "
    //      << hyd_time << "\tcyc = " << cyc << endl;

    if (hyd_time < leachTime_ && hyd_time < sulfateAttackTime_) {

      // if (!doTweak) {
      //  @todo BULLARD PLACEHOLDER
      //  Still need to implement constant gas phase composition
      //  Will involve equilibrating gas with aqueous solution
      //
      //  First step each iteration is to equilibrate gas phase
      //  with the electrolyte, while forbidding anything new
      //  from precipitating.

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

      /// Loop over all kinetic models

      //*******
      double totalDOR = 0;

      if (initScaledCementMass_> 0) {
        totalDOR = (initScaledCementMass_ - chemSys_->getScaledCementMass()) / initScaledCementMass_;
      } else {
        int numPKMphases = 0;
        for (int midx = 0; midx < pKMsize_; ++midx) {
          if (phaseKineticModel_[midx]->getName() == "Alite") numPKMphases++;
          if (phaseKineticModel_[midx]->getName() == "Belite") numPKMphases++;
          if (phaseKineticModel_[midx]->getName() == "Ferrite") numPKMphases++;
          if (phaseKineticModel_[midx]->getName() == "Aluminate") numPKMphases++;
        }
        if (numPKMphases > 0) {

          cout << endl << "     KineticController::calculateKineticStep error - initScaledCementMass_ = 0 "
                          "while numPKMphases = " << numPKMphases << " :" << endl;
          for (int midx = 0; midx < pKMsize_; ++midx) {
            phaseDissolvedId[midx] = phaseKineticModel_[midx]->getMicroPhaseId();
            scaledMassIni_[midx] = chemSys_->getMicroPhaseMass(phaseDissolvedId[midx]);
            cout << "    midx = " << midx << "     scaledMassIni[midx] = " << scaledMassIni_[midx]
                 << "     microPhaseName = " << phaseKineticModel_[midx]->getName() << endl;
          }
          cout << endl << "        cyc/doTweak/timesGEMFailed : " << cyc << " / "
               << doTweak << " / " << chemSys_->getTimesGEMFailed() << endl;
          throw FloatException("KineticController", "calculateKineticStep",
                               "initScaledCementMass_ = 0");
        }
      }
      if (totalDOR < 0) {
        cout << endl << "     KineticController::calculateKineticStep error : totalDOR < 0" << endl;
        cout << endl << "        cyc/doTweak/timesGEMFailed : " << cyc << " / "
             << doTweak << " / " << chemSys_->getTimesGEMFailed() << endl;
        cout << endl << "        initScaledCementMass_/scaledCementMass/totalDOR : "
            << initScaledCementMass_ << " / " << chemSys_->getScaledCementMass() << " / " << totalDOR << endl;
        throw DataException("KineticController", "calculateKineticStep",
                            "totalDOR < 0");
      }
      if (!doTweak) {
        cout << "  KineticController::calculateKineticStep - cyc = " << cyc << " :  scaledCementMass = "
             << chemSys_->getScaledCementMass() << "   totalDOR = " << totalDOR << endl;
      }

      //*******

      double dcmoles;
      bool runKM = true;

      for (int midx = 0; midx < pKMsize_; ++midx) {
        scaledMass = scaledMassIni_[midx];
        runKM = true;
        if (scaledMass == 0 && phaseKineticModel_[midx]->getModelName() == "ParrotKillohModel") {
          runKM = false;
        }

        // if (scaledMass > 0) {
        if (runKM) {
          DCId = phaseKineticModel_[midx]->getDCId();
          // scaledMass = scaledMassIni_[midx];
          massDissolved = 0;
          phaseKineticModel_[midx]->calculateKineticStep(
                timestep, scaledMass, massDissolved, cyc, totalDOR);

          if (scaledMass < 0) { // || massDissolved < 0) {
            cout << endl << "KineticController::calculateKineticStep error for cyc = " << cyc
                 << " - scaledMass = " << scaledMass << "   massDissolved = " << massDissolved << endl;
            cout << "   midx/phName/scaledMassIni_[midx] : " << midx << " / "
                 << phaseKineticModel_[midx]->getName() << " / " << scaledMassIni_[midx] << endl;
            cout << endl << "end program" << endl;
            exit(0);
          }

          chemSys_->updateMicroPhaseMasses(phaseDissolvedId[midx], scaledMass, 0);

          if (verbose_) {
            cout << "New scaled mass = "
                 << chemSys_->getMicroPhaseMass(phaseDissolvedId[midx])
                 << " and new volume = "
                 << chemSys_->getMicroPhaseVolume(phaseDissolvedId[midx]) << endl;
            cout.flush();
          }

          totMassImpurity = 0;
          numDCMolesDissolved = 0;
          keepNumDCMoles = 0;

          massImpurity = massDissolved * chemSys_->getK2o(phaseDissolvedId[midx]);
          totMassImpurity += massImpurity;
          dcmoles = massImpurity / chemSys_->getDCMolarMass("K2O");
          DCMoles_[impurityDCID_[0]] += dcmoles;
          impurity_K2O_[midx] = dcmoles;
          //DCMoles_[impurityDCID[0]] +=
          //    massImpurity / chemSys_->getDCMolarMass("K2O");

          massImpurity = massDissolved * chemSys_->getNa2o(phaseDissolvedId[midx]);
          totMassImpurity += massImpurity;
          dcmoles = massImpurity / chemSys_->getDCMolarMass("Na2O");
          DCMoles_[impurityDCID_[1]] += dcmoles;
          impurity_Na2O_[midx] = dcmoles;
          //DCMoles_[impurityDCID[1]] +=
          //    massImpurity / chemSys_->getDCMolarMass("Na2O");

          massImpurity = massDissolved * chemSys_->getMgo(phaseDissolvedId[midx]);
          totMassImpurity += massImpurity;
          dcmoles = massImpurity / chemSys_->getDCMolarMass("Per");
          DCMoles_[impurityDCID_[2]] += dcmoles;
          impurity_Per_[midx] = dcmoles;
          //DCMoles_[impurityDCID[2]] +=
          //    massImpurity / chemSys_->getDCMolarMass("Per"); // MgO

          massImpurity = massDissolved * chemSys_->getSo3(phaseDissolvedId[midx]);
          totMassImpurity += massImpurity;
          dcmoles = massImpurity / chemSys_->getDCMolarMass("SO3");
          DCMoles_[impurityDCID_[3]] += dcmoles;
          impurity_SO3_[midx] = dcmoles;
          //DCMoles_[impurityDCID[3]] +=
          //    massImpurity / chemSys_->getDCMolarMass("SO3");

          numDCMolesDissolved =
              (massDissolved - totMassImpurity) / chemSys_->getDCMolarMass(DCId);
          keepNumDCMoles = DCMoles_[DCId] - numDCMolesDissolved;

          chemSys_->setDCLowerLimit(DCId, keepNumDCMoles);
          if (verbose_) {
            cout << "    calculateKineticStep - "
                    "midx/DCId/DCMoles_/numDCMolesDissolved/keepNumDCMoles : "
                 << midx << " / " << DCId << " / " << DCMoles_[DCId] << " / " << numDCMolesDissolved
                 << " / " << keepNumDCMoles << endl;
            cout << "    calculateKineticStep - scaledMass/massDissolved/"
                    "totMassImpurity/massDissolved - totMassImpurity : "
                 << scaledMass << " / " << massDissolved << " / " << totMassImpurity << " / "
                 << massDissolved - totMassImpurity << endl;
          }
        } // if (scaledMass > 0) {
      } // for (int midx = 0; midx < pKMsize_; ++midx) {

      if (verbose_ && doTweak) {
        cout << endl << "  KineticController::calculateKineticStep "
                "- tweak after for cyc = " << cyc << endl;
      }

    } // End of normal hydration block
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
    EOBException ex("KineticController", "calculateKineticStep", oor.what(), 0,
                    0);
    ex.printException();
    exit(1);
  }

  for (i = 0; i < DCNum_; i++) {
    // cout << " " << i << "\t" << DCName_[i] << ": " << DCMoles_[i] << " mol"
    // << endl;
    chemSys_->setDCMoles(i, DCMoles_[i]);
    // cout << "          " << DCName_[i] << ": " << chemSys_->getDCMoles(i) <<
    // " mol" << endl;
  }

  // if (!doTweak) {
  //   cout << "  KineticController::calculateKineticStep end - cyc = " << cyc << endl;
  //   cout.flush();
  // }

  return;
}

double KineticController::updateKineticStep(int cyc, int pId, double scaledMass) {
  int i;
  string modelName;
  double totMassImpurity, massImpurity;
  int DCId;
  double keepNumDCMoles;
  int phaseDissolvedId;
  double numDCMolesDissolved, massDissolved;

  for (i = 0; i < ICNum_; i++) {
    ICMoles_[i] = 0.0;
  }

  int midx;
  for (midx = 0; midx < pKMsize_; ++midx) {
    phaseDissolvedId = phaseKineticModel_[midx]->getMicroPhaseId();
    if (pId == phaseDissolvedId) {
      DCId = phaseKineticModel_[midx]->getDCId();
      break;
    }
  }
  chemSys_->setMicroPhaseMass(phaseDissolvedId, scaledMassIni_[midx]);
  modelName = phaseKineticModel_[midx]->getModelName();// updateKineticStep(scaledMass , massDissolved);
  cout << endl
       << "  KineticController::updateKineticStep - for cyc = " << cyc << " & phaseId = " << pId
       << " [" << phaseKineticModel_[midx]->getName() << " / DCId:"
       << chemSys_->getMicroPhaseDCMembers(pId, 0) << "]" << endl;
  cout << "    midx = " << midx << "   modelName : " << modelName
       << "   scaledMassIni[midx] = " << scaledMassIni_[midx] << "   scaledMass = " << scaledMass
       << endl;

  //DCMoles_[DCId] = DCMolesIni_[DCId];
  DCMoles_[impurityDCID_[0]] -= impurity_K2O_[midx];
  DCMoles_[impurityDCID_[1]] -= impurity_Na2O_[midx];
  DCMoles_[impurityDCID_[2]] -= impurity_Per_[midx];
  DCMoles_[impurityDCID_[3]] -= impurity_SO3_[midx];

  /// for this kinetic model

  massDissolved = scaledMassIni_[midx] - scaledMass;

  //chemSys_->setMicroPhaseMass(phaseDissolvedId, scaledMass);
  //chemSys_->setMicroPhaseMassDissolved(phaseDissolvedId, massDissolved);
  chemSys_->updateMicroPhaseMasses(phaseDissolvedId, scaledMass, 1);

  totMassImpurity = 0;
  keepNumDCMoles = 0;
  numDCMolesDissolved = 0;

  double dcmoles;
  massImpurity = massDissolved * chemSys_->getK2o(phaseDissolvedId);
  totMassImpurity += massImpurity;
  dcmoles = massImpurity / chemSys_->getDCMolarMass("K2O");
  DCMoles_[impurityDCID_[0]] += dcmoles;
  impurity_K2O_[midx] = dcmoles;
  //DCMoles_[impurityDCID[0]] +=
  //    massImpurity / chemSys_->getDCMolarMass("K2O");

  massImpurity = massDissolved * chemSys_->getNa2o(phaseDissolvedId);
  totMassImpurity += massImpurity;
  dcmoles = massImpurity / chemSys_->getDCMolarMass("Na2O");
  DCMoles_[impurityDCID_[1]] += dcmoles;
  impurity_Na2O_[midx] = dcmoles;
  //DCMoles_[impurityDCID[1]] +=
  //    massImpurity / chemSys_->getDCMolarMass("Na2O");

  massImpurity = massDissolved * chemSys_->getMgo(phaseDissolvedId);
  totMassImpurity += massImpurity;
  dcmoles = massImpurity / chemSys_->getDCMolarMass("Per");
  DCMoles_[impurityDCID_[2]] += dcmoles;
  impurity_Per_[midx] = dcmoles;
  //DCMoles_[impurityDCID[2]] +=
  //    massImpurity / chemSys_->getDCMolarMass("Per"); // MgO

  massImpurity = massDissolved * chemSys_->getSo3(phaseDissolvedId);
  totMassImpurity += massImpurity;
  dcmoles = massImpurity / chemSys_->getDCMolarMass("SO3");
  DCMoles_[impurityDCID_[3]] += dcmoles;
  impurity_SO3_[midx] = dcmoles;
  //DCMoles_[impurityDCID[3]] +=
  //    massImpurity / chemSys_->getDCMolarMass("SO3");

  numDCMolesDissolved = (massDissolved - totMassImpurity) / chemSys_->getDCMolarMass(DCId);
  keepNumDCMoles = DCMoles_[DCId] - numDCMolesDissolved;
  chemSys_->setDCLowerLimit(DCId, keepNumDCMoles);
  cout << "    DCId/DCMoles_/numDCMolesDissolved/keepNumDCMoles : "
       << DCId << " / " << DCMoles_[DCId] << " / " << numDCMolesDissolved << " / "
       << keepNumDCMoles << endl;
  cout << "    massDissolved/totMassImpurity/massDissolved - totMassImpurity : "
       << massDissolved << " / " << totMassImpurity << " / "
       << massDissolved - totMassImpurity << endl;

  for (i = 0; i < DCNum_; i++) {
    // cout << " " << i << "\t" << DCName_[i] << ": " << DCMoles_[i] << " mol"
    // << endl;
    chemSys_->setDCMoles(i, DCMoles_[i]);
    // cout << "          " << DCName_[i] << ": " << chemSys_->getDCMoles(i) <<
    // " mol" << endl;
  }

  cout << "  KineticController::updateKineticStep end - cyc = " << cyc << endl;
  cout.flush();

  return massDissolved;
}

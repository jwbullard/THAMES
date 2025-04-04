/**
@file thames.cc

*/

#include "thames.h"
#include "version.h"
#include <limits>

/**
@brief The main block for running THAMES.

@return 0 on successful completion, non-zero otherwise
*/
int main(int argc, char **argv) {

  // Check command line arguments

  cout << scientific << setprecision(15);
  if (checkArgs(argc, argv)) {
    exit(0);
  }

  // Set up the strainenergy vector.  We allow no more than 156 phases,
  // but this can be changed below.

  strainenergy.clear();
  strainenergy.resize(156, 0.0);

  int choice, simtype;
  string buff = "";
  ChemicalSystem *ChemSys = NULL;
  Lattice *Mic = NULL;
  ThermalStrain *ThermalStrainSolver = NULL;
  AppliedStrain *AppliedStrainSolver = NULL;
  KineticController *KController = NULL;
  Controller *Ctrl = NULL;
  RanGen *RNG = NULL;

  bool errorProgram = false;

  int resCallSystem;

  //
  // Main menu where user decides what kind of simulation this will be.
  //

  cout << "Enter choice: " << endl;
  cout << "  " << QUIT_PROGRAM << ") Exit program " << endl;
  cout << "  " << HYDRATION << ") Hydration " << endl;
  cout << "  " << LEACHING << ") Leaching " << endl;
  cout << "  " << SULFATE_ATTACK << ") Sulfate attack " << endl;
  cin >> choice;
  cout << endl << "choice = " << choice << endl;

  // cout << "epsilon for double : \t" << numeric_limits<double>::epsilon() <<
  // endl; cout << "epsilon for int : \t" << numeric_limits<int>::epsilon() <<
  // endl; cout << "epsilon for float : \t" << numeric_limits<float>::epsilon()
  // << endl;

  if (choice <= QUIT_PROGRAM || choice > SULFATE_ATTACK) {

    cout << "Exiting program now." << endl << endl;
    exit(1);
  }

  int seedRNG = -25943; // -142234;
  // cin >> seedRNG;
  cout << endl
       << "The RNG seed is                 : seedRNG = " << seedRNG << endl;

  double elemTimeInterval = (24.0 * 1.e-7); // 24 factor to convert from days to
                                            // hours
  // cin >> elemTimeInterval;
  cout << "The elementary time interval is : elemTimeInterval = "
       << setprecision(3) << elemTimeInterval << endl;

  cout << scientific << setprecision(15) << endl;

  time_t lt = time(NULL);
  struct tm *inittime;
  inittime = localtime(&lt);
  cout << asctime(inittime);
  clock_t starttime = clock();
  simtype = choice;

  //
  // User must provide the name of the GEM chemical system definition (CSD) file
  // for the aqueous solution
  //

  // Read the newline character.  Wish there was a better way!
  getline(cin, buff);

  //
  // User must provide the name of the GEM CSD for the whole system
  //

  cout << endl << "What is the name of the GEM input file? " << endl;
  getline(cin, buff);
  const string gemInputName(buff);
  cout << "   - gemInputName      :  " << gemInputName << endl;
  cout.flush();

  //
  // User must provide the name of the file specifying the microstructre
  // phase data
  //

  cout << endl
       << "What is the name of the microstructure phase definition file? "
       << endl;
  getline(cin, buff);
  const string micDefName(buff);
  cout << "   - micDefName        :  " << micDefName << endl;

  //
  // Create the ChemicalSystem object
  //

  try {
    ChemSys = new ChemicalSystem(gemInputName, micDefName, VERBOSE, WARNING);
  } catch (bad_alloc &ba) {
    cout << "Bad memory allocation in ChemicalSystem constructor: " << ba.what()
         << endl;
    errorProgram = true;
  } catch (FileException fex) {
    fex.printException();
    errorProgram = true;
  } catch (GEMException gex) {
    gex.printException();
    errorProgram = true;
  } catch (DataException dex) {
    dex.printException();
    errorProgram = true;
  }
  if (errorProgram) {
    deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                      AppliedStrainSolver, KController, Ctrl, starttime, lt,
                      errorProgram);
  }

  //
  // Create the random number generator
  //

  RNG = new RanGen(seedRNG);

  //
  // User must specifiy the file containing the 3D microstructure itself
  //

  cout << endl << "What is the name of the MICROSTRUCTURE file? " << endl;
  getline(cin, buff);
  const string initMicName(buff);
  cout << "   - initMicName       :  " << initMicName << endl;

  //
  // Create the Lattice object to hold the microstructure
  //

  try {
    Mic = new Lattice(ChemSys, RNG, seedRNG, initMicName, VERBOSE, WARNING);
    cout << endl << "Lattice creation done... " << endl;
    cout << "X size of lattice is " << Mic->getXDim() << endl;
    cout << "Y size of lattice is " << Mic->getYDim() << endl;
    cout << "Z size of lattice is " << Mic->getZDim() << endl;
    cout << "Total number of sites is " << Mic->getNumSites() << endl;
  } catch (bad_alloc &ba) {
    cout << "Bad memory allocation in Lattice constructor: " << ba.what()
         << endl;
    errorProgram = true;
  } catch (FileException fex) {
    fex.printException();
    errorProgram = true;
  } catch (GEMException gex) {
    gex.printException();
    errorProgram = true;
  } catch (EOBException eex) {
    eex.printException();
    errorProgram = true;
  } catch (FloatException flex) {
    flex.printException();
    errorProgram = true;
  }
  if (errorProgram) {
    deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                      AppliedStrainSolver, KController, Ctrl, starttime, lt,
                      errorProgram);
  }

  if (choice == SULFATE_ATTACK) {

    //
    // This block is executed only if simulating external sulfate attack,
    // in which case we need information about the elastic moduli of the
    // constituent phases, and will need to include a finite element solver
    //

    cout << endl << "What is the name of the elastic modulus file?" << endl;
    buff = "";
    // cin >> buff;  // C++ >> operator does not allow spaces
    getline(cin, buff);
    const string phasemod_fileName(buff);
    cout << "   - phasemod_fileName :  " << phasemod_fileName << endl;

    //
    // Create the ThermalStrain FE solver, which handles phase transformation
    // misfit
    //

    try {
      ThermalStrainSolver =
          new ThermalStrain(Mic->getXDim(), Mic->getYDim(), Mic->getZDim(),
                            (Mic->getNumSites() + 2),
                            ChemSys->getNumMicroPhases(), 1, VERBOSE, WARNING);
      cout << "ThermalStrain object creation done... " << endl;
      ThermalStrainSolver->setPhasemodfileName(phasemod_fileName);
    } catch (bad_alloc &ba) {
      cout << "Bad memory allocation in ThermalStrain constructor: "
           << ba.what() << endl;
      errorProgram = true;
    } catch (FileException ex) {
      ex.printException();
      errorProgram = true;
    } catch (GEMException ex) {
      ex.printException();
      errorProgram = true;
    }
    if (errorProgram) {
      deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                        AppliedStrainSolver, KController, Ctrl, starttime, lt,
                        errorProgram);
    }

    int nx, ny, nz;
    nx = ny = nz = 3;
    int ns = nx * ny * nz;

    //
    // Create the AppliedStrain FE solver, which handles applied external
    // strains
    //

    try {
      AppliedStrainSolver = new AppliedStrain(
          nx, ny, nz, ns, ChemSys->getNumMicroPhases(), 1, VERBOSE, WARNING);
      AppliedStrainSolver->setPhasemodfileName(phasemod_fileName);
    } catch (bad_alloc &ba) {
      cout << "Bad memory allocation in AppliedStrain constructor: "
           << ba.what() << endl;
      errorProgram = true;
    } catch (FileException ex) {
      ex.printException();
      errorProgram = true;
    } catch (GEMException ex) {
      ex.printException();
      errorProgram = true;
    }
    if (errorProgram) {
      deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                        AppliedStrainSolver, KController, Ctrl, starttime, lt,
                        errorProgram);
    }

    Mic->setFEsolver(AppliedStrainSolver);
  }

  string jobRoot, parFileName, statFileName;
  if (VERBOSE) {
    cout << "About to enter KineticController constructor" << endl;
    cout.flush();
  }

  //
  // Create the KineticController object
  //

  try {
    KController =
        new KineticController(ChemSys, Mic, micDefName, VERBOSE, WARNING);
  } catch (bad_alloc &ba) {
    cout << "Bad memory allocation in KineticController constructor: "
         << ba.what() << endl;
    errorProgram = true;
  } catch (FileException ex) {
    ex.printException();
    errorProgram = true;
  } catch (GEMException ex) {
    ex.printException();
    errorProgram = true;
  } catch (FloatException ex) {
    ex.printException();
    errorProgram = true;
  } catch (DataException ex) {
    ex.printException();
    errorProgram = true;
  }
  if (errorProgram) {
    deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                      AppliedStrainSolver, KController, Ctrl, starttime, lt,
                      errorProgram);
  }

  if (VERBOSE) {
    cout << "Finished constructing KineticController KController" << endl;
    cout.flush();
  }

  cout << endl << "What is the name of the simulation parameter file? " << endl;
  getline(cin, buff);
  parFileName.assign(buff);
  cout << "   - parFileName       :  " << parFileName << endl;

  cout << endl << "What is the root name of output files?" << endl;
  getline(cin, buff);
  jobRoot.assign(buff);
  cout << "   - files root name   :  " << jobRoot << endl;

  prepOutputFolder(outputFolder, jobRoot, gemInputName, statFileName,
                   initMicName, micDefName, parFileName);

  //
  // Create the Controller object to direct flow of the program
  //

  try {
    Ctrl = new Controller(Mic, KController, ChemSys, ThermalStrainSolver,
                          simtype, parFileName, jobRoot, VERBOSE, WARNING, XYZ);
  } catch (bad_alloc &ba) {
    cout << "Bad memory allocation in Controller constructor: " << ba.what()
         << endl;
    errorProgram = true;
  } catch (FileException ex) {
    ex.printException();
    errorProgram = true;
  } catch (GEMException ex) {
    ex.printException();
    errorProgram = true;
  }
  if (errorProgram) {
    deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                      AppliedStrainSolver, KController, Ctrl, starttime, lt,
                      errorProgram);
  }

  //
  // Write a formatted output of the simulation parameters for later reference
  //

  writeReport(jobRoot, inittime, initMicName, micDefName, parFileName,
              gemInputName, ChemSys, Ctrl);

  //
  // Launch the main controller to run the simulation
  //

  // if (VERBOSE) {
  cout << endl << "Going into Controller::doCycle" << endl;
  cout.flush();
  //}

  try {

    Ctrl->doCycle(statFileName, choice, elemTimeInterval);

  } catch (GEMException gex) {
    gex.printException();
    errorProgram = true;
  } catch (DataException dex) {
    dex.printException();
    errorProgram = true;
  } catch (EOBException ex) {
    ex.printException();
    errorProgram = true;
  } catch (MicrostructureException mex) {
    mex.printException();
    errorProgram = true;
  }
  if (errorProgram) {
    deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver,
                      AppliedStrainSolver, KController, Ctrl, starttime, lt,
                      errorProgram);
  }

  //
  // Simulation is finished.
  //

  deleteDynAllocMem(ChemSys, Mic, RNG, ThermalStrainSolver, AppliedStrainSolver,
                    KController, Ctrl, starttime, lt, errorProgram);

  return 0;
}

void deleteDynAllocMem(ChemicalSystem *ChemSys, Lattice *Mic, RanGen *RNG,
                       ThermalStrain *ThermalStrainSolver,
                       AppliedStrain *AppliedStrainSolver,
                       KineticController *KController, Controller *Ctrl,
                       clock_t st_time, time_t lt, bool errorProgram) {

  string buff = "";
  int resCallSystem;

  if (Ctrl) {
    delete Ctrl;
  }
  if (KController) {
    delete KController;
  }
  if (AppliedStrainSolver) {
    delete AppliedStrainSolver;
  }
  if (ThermalStrainSolver) {
    delete ThermalStrainSolver;
  }
  if (Mic) {
    delete Mic;
  }
  if (ChemSys) {
    delete ChemSys;
  }
  if (RNG) {
    delete RNG;
  }

  //
  // Move remaining output files to output folder
  //

  string name = "ipmlog.txt";
  ifstream f(name.c_str());
  if (f.good()) {
    buff = "mv -f ipmlog.txt " + outputFolder + "/.";
    resCallSystem = system(buff.c_str());
    if (resCallSystem == -1) {
      throw FileException("thames", "deleteDynAllocMem", buff, "FAILED");
    }
    // cout << buff << endl;
    f.close();
  }

  name = "IPM_dump.txt";
  f.open(name.c_str());
  if (f.good()) {
    buff = "mv -f IPM_dump.txt " + outputFolder + "/.";
    resCallSystem = system(buff.c_str());
    if (resCallSystem == -1) {
      throw FileException("thames", "deleteDynAllocMem", buff, "FAILED");
    }
    // cout << buff << endl;
    f.close();
  }

  cout << endl
       << "=> IPM_dump.txt & ipmlog.txt are into " << outputFolder << " folder"
       << endl;

  cout << endl << "STOP Program" << endl;
  timeCount(st_time, lt);

  if (errorProgram) {
    exit(1);
  } else {
    exit(0);
  }
}

void timeCount(clock_t time_, time_t lt_) {

  time_t lt1 = time(NULL);
  struct tm *inittime1;
  inittime1 = localtime(&lt1);
  cout << endl << asctime(inittime1);
  clock_t endtime = clock();

  double elapsedtime = (double)(endtime - time_) / CLOCKS_PER_SEC;
  double ltD = difftime(lt1, lt_);
  cout << endl << "Total time = " << ltD << " seconds" << endl;
  cout << endl
       << "Total time with clock = " << elapsedtime << " seconds" << endl;
}

void printHelp(void) {
  cout << endl;
  cout << "Usage: \"thames [--verbose|-v] [--suppress|-s] [--xyz|-x] "
          "[--outfolder|-o] folder [--help|-h]\""
       << endl;
  cout << "        --verbose [-v]      Produce verbose output" << endl;
  cout << "        --suppress [-s]     Suppress warning messages" << endl;
  cout << "        --xyz [-x]          Create 3D visualization movie" << endl;
  cout << "        --outfolder [-o]    Name of folder for output data (default "
          "is Result)"
       << endl;
  cout << endl;
  cout << "Note: thames --help [-h] will print this help message" << endl;

  return;
}

int checkArgs(int argc, char **argv) {

  // Many of the variables here are defined in the getopts.h system header file
  // Can define more options here if we want

  const char *const short_opts = "vsxo:h";
  const option long_opts[] = {{"verbose", no_argument, nullptr, 'v'},
                              {"suppress", no_argument, nullptr, 's'},
                              {"xyz", no_argument, nullptr, 'x'},
                              {"outfolder", required_argument, nullptr, 'o'},
                              {"help", no_argument, nullptr, 'h'},
                              {nullptr, no_argument, nullptr, 0}};

  VERBOSE = false;
  WARNING = true;
  XYZ = false;

  // Default value of output folder unless user overrides it
  outputFolder = "Result";

  while (true) {

    const auto opt = getopt_long(argc, argv, short_opts, long_opts, nullptr);

    if (-1 == opt)
      break; // breaks out of this while loop

    switch (opt) {
    case 'v':
      VERBOSE = true; // Verbose defined in thameslib global.h
      cout << "**Will produce verbose output**" << endl;
      break;
    case 's':
      WARNING = false; // Verbose defined in thameslib global.h
      cout << "**Will suppress warning messages**" << endl;
      break;
    case 'x':
      XYZ = true; // Verbose defined in thameslib global.h
      cout << "**Will create 3D visualization file **" << endl;
      break;
    case 'o':
      outputFolder = optarg; // Verbose defined in thameslib global.h
      if ((outputFolder[0] == ' ') || (outputFolder[0] == '-') ||
          (outputFolder[0] == '\\')) {
        printHelp();
        return (1);
      }
      cout << "Output folder: " << outputFolder << endl;
      break;
    case 'h': // -h or --help
    case '?': // Unrecognized option
    default:
      printHelp();
      return (1);
      break;
    }
  }
  return (0);
}

void prepOutputFolder(const string &outputFolder, string &jobRoot,
                      const string &gemInputName, string &statFileName,
                      const string &initMicName, const string &micDefName,
                      const string &parFileName) {

  int resCallSystem;

  string buff = "mkdir -p " + outputFolder;
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }
  jobRoot = outputFolder + "/" + jobRoot;
  cout << "   - jobRoot           :  " << jobRoot << endl;
  cout.flush();

  statFileName = jobRoot + ".stats";

  // Read the gem input master file to get file names
  // and copy them to the output folder

  ifstream in(gemInputName);
  string buff1;
  in >> buff1; // discard flag

  // DCH file
  buff1.clear();
  in >> buff1; // This is the dch file with quotes
  if (buff1[0] == '"' || buff1[0] == '\'') {
    buff1 = buff1.substr(1, buff1.size() - 2);
  }
  buff = "cp -f " + buff1 + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  // IPM file
  buff1.clear();
  in >> buff1; // This is the ipm file with quotes
  if (buff1[0] == '"' || buff1[0] == '\'') {
    buff1 = buff1.substr(1, buff1.size() - 2);
  }
  buff = "cp -f " + buff1 + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  // DBR file
  buff1.clear();
  in >> buff1; // This is the dbr file with quotes
  in.close();

  if (buff1[0] == '"' || buff1[0] == '\'') {
    buff1 = buff1.substr(1, buff1.size() - 2);
  }
  buff = "cp -f " + buff1 + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  buff = "cp -f " + gemInputName + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  buff = "cp -f " + initMicName + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  buff = "cp -f " + micDefName + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }

  buff = "cp -f " + parFileName + " " + outputFolder + "/.";
  resCallSystem = system(buff.c_str());
  if (resCallSystem == -1) {
    throw FileException("thames", "prepOutputFolder", buff, "FAILED");
  }
  cout << "     => All input files have been copied into " << outputFolder
       << " folder" << endl;

  return;
}

void writeReport(const string &jobRoot, struct tm *itime,
                 const string &initMicName, const string &micDefName,
                 const string &parFileName, const string &csdName,
                 ChemicalSystem *csys, Controller *ctr) {
  string statName = jobRoot + ".stats";
  string jFileName = jobRoot + ".report";
  ofstream out(jFileName.c_str());
  if (!out.is_open()) {
    if (WARNING)
      cout << "WARNING:  Could not open report file" << endl;
    return;
  }

  //
  // Write the time the job was executed
  //

  out << "THAMES simulation " << jobRoot;
  out << " initialized on " << asctime(itime) << endl;
  out << endl;
  out << "INPUT FILES USED:" << endl;
  out << "              Microstructure file name: " << initMicName << endl;
  out << "   Microstructure definition file name: " << micDefName << endl;
  out << "            Output frequency file name: " << parFileName << endl;
  out << "                   GEM input file name: " << csdName << endl;
  out << endl;
  out << "OUTPUT FILES GENERATED:" << endl;
  out << "                Global phase fractions: " << statName << endl;
  out << endl;
  out << "----------------------------------------------------------" << endl;
  out << endl;

  csys->writeChemSys(out);
  out << endl;

  out.close();
  return;
}

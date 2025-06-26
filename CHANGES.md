# THAMES

## CHANGES

| Date                     | Description                         |
|:-------------------------|:-------------------------------------|
| Jun 26 11:01 2025 | Desaturating nanoporosity merged with chemical "attack" |
| Jun 2 13:46 2025 | Microstructure-based calculation of pozzolanic surface area |
| Jun 2 12:59 2025 | Fixed a few discrepancies between commit 6fd2fd4 and HEAD |
| May 31 14:57 2025 | Updated cmake directives to allow for Apple Clang |
| May 30 09:48 2025 | Made all global variables inline |
| May 29 16:32 2025 | Removed namespace directives |
| May 28 16:16 2025 | Using recommended header guards |
| May 23 20:08 2025 | Reverted GEM input files (dch,dbr, etc) to avoid infinite loops in GEM_run |
| May 20 14:31 2025 | Merged main with branch florinnita_recoverMainAndFixIssues |
| May 19 16:31 2025 | Fixed header error in _CSH.csv output file |
| May 17 15:49 2025 | Changed time format for output file names |
| May 15 13:12 2025 | Removed runtime errors; improved time string formation |
| May 14 21:43 2025 | Removed compile time warnings in thameslib; still runtime errors |
| May 14 17:02 2025 | Getting GEMS3K library to compile with strainenergy added |
| May 19 16:31 2025 | Fixed header error in _CSH.csv output file |
| May 17 15:49 2025 | Changed time format for output file names |
| May 11 15:53 2025 | Streamlined JSON input to one file only |
| May 08 16:20 2025 | Calculate PK SSA, tested surface area scaling, and updated test cases (tested) |
| May 05 22:58 2025 | Calculate and use PK SSA instead of using user input (untested) |
| May 05 18:15 2025 | Implemented automatic time steps |
| May 05 08:05 2025 | Debug fixed boundary conditions |
| Apr 22 10:58 2025 | Updated to reflect v4.0 |
| Apr 18 10:58 2025 | Merged update branch onto main |
| Apr 03 16:47 2025 | Removed a few obsolete references to xml file input |
| Apr 03 15:06 2025 | Read surface area multiplier from JSON input file |
| Apr 02 16:52 2025 | Removed dependence on DOR for all but Parrot Killoh model |
| Apr 02 10:41 2025 | Validated test cases against HEAD of main branch |
| Mar 28 16:49 2025 | Fixed more bugs with recovering from GEM convergence error |
| Mar 28 16:49 2025 | Fixed most or all of bug with recovering from GEM convergence error |
| Mar 28 11:47 2025 | Debugging problem with recovery from GEM convergence error |
| Mar 26 22:25 2025 | Corrected recent bug introduction in Parrot-Killoh model |
| Mar 20 16:59 2025 | Minor changes to verbose output |
| Mar 20 16:36 2025 | Debugged surface scaling for Parrot-Killoh kinetics |
| Mar 18 19:02 2025 | Very minor changes to comments |
| Mar 18 18:08 2025 | Area scaling is working for standard phases |
| Mar 16 21:34 2025 | Fixed time conversion error in PK model |
| Mar 14 19:39 2025 | Fixed compile-time errors due to code repetition |
| Mar 12 15:11 2025 | Improved the help/usage message |
| Mar 12 12:49 2025 | Merge branch florinnita_THAMES_avoidGEMfailure-xyzfile |
| Mar 10 15:01 2025 |Fixed segmentation fault given by ChemicalSystem::parseDisplayData(…) |
| Mar 07 15:36 2025 | Fixed a few inconsistencies in the test input files |
| Mar 04 10:02 2025 | Merged changes from branch `florinnita_THAMES_avoidGEMfailure` from past month |
| Mar 03 13:43 2025 | Added recalculation of surface areas each cycle in KineticController::calculateKineticStep |
| Mar 03 00:28 2025 | Include surface area scaling in kinetics |
| Mar 01 22:36 2025 | Converted all model times to hours |
| Feb 03 21:24 2025 | Created `surfacearea` branch from `json` to account for surface area scaling in kinetics |
| Feb 03 21:02 2025 | Merged `xyzfile` branch into `json` branch |
| Feb 03 20:09 2025 | Pore size distribution data included in chemistry.json |
| Feb 02 23:21 2025 | Corrected error preventing identification of kinetic phases |
| Feb 01 14:39 2025 | Fixed compile-time bug in `thames.cc` after merging |
| Feb 01 11:41 2025 | Merged branch `florinnita_THAMES_avoidGEMfailure` to take small time steps to get past a GEM_run failure |
| Jan 12 17:45 2025 | Updated test input files to put pore size distribution data in microstructure definition file |
| Jan 12 09:16 2025 | Fixed a bug with json parsing and also with Pozzolanic kinetic model |
| Jan 11 02:59 2025 | Tested json on all test cases |
| Jan 08 17:36 2025 | Fixed more runtime errors related to how json parses chemistry file |
| Jan 08 14:49 2025 | Fixed some runtime errors related to json iterator misassignments |
| Jan 07 14:24 2025 | Removed Doxyfile$ file which only records local changes to environment |
| Jan 01 23:44 2024 | Updated CMakeLists.txt |
| Dec 27 22:08 2024 | Fixed small runtime bug in pore distributions |
| Dec 27 21:49 2024 | Pore size distribution now with microstructure definition file |
| Dec 27 12:23 2024 | Added command line option to toggle xyz output |
| Dec 24 21:20 2024 | Debugged run-time errors on xyzfile branch |
| Dec 24 17:32 2024 | Create xyzfile branch and integrate xyz file writing internally |
| Dec 23 23:03 2024 | Fixed all compile-time errors in json branch. |
| Nov 11 10:14 2024 | Merged branch `florinnita_THAMES_v3.0.1-v4.0.0` which fixed some memory leaks and updated test input files; tagged v3.0.0 |
| Nov 01 09:45 2024 | Commit in preparation for v3.0.0 release |
| Oct 30 17:51 2024 | Fixed gas and electrolyte composition functionality |
| Oct 29 11:19 2024 | Small tweaks here and there |
| Oct 28 13:31 2024 | Merged `florinnita_THAMES_Version3.0` branch |
| Jul 25 09:16 2024 | Updated format of Colors.csv output |
| Jul 24 11:01 2024 | Merged latest version of branch florinRecoverLatticeAndRNG onto main |
| Jul 18 15:49 2024 | Merged changes to main branch for dealing with critDOH effect in PK model |
| Jul 10 21:02 2024 | Major changes to main branch, merging several branches onto main, includes all development since June 4 |
| Jul 11 17:53 2024 | Implemented initial and fixed solution DC composition |
| Jun 04 09:00 2024 | Saturation indices all reading zero no matter what. Debugging. |
| May 22 10:51 2024 | Beginning to generalize dissolution and precipitation kinetics |
| May 22 10:51 2024 | Propagated fix for StandardKineticModel to PozzolanicModel |
| May 21 13:46 2024 | Fixed accidental resetting of ICmoles assignment in StandardKineticModel |
| May 16 16:53 2024 | Removed Solution class and all dependencies on it |
| May 16 11:19 2024 | Committing because I'm about to try radical surgery on structure |
| May 06 22:14 2024 | Now using DCLowerLimit for kinetics |
| May 03 12:00 2024 | Preliminary planning of code restructuring for precipitation kinetics |
| May 02 17:47 2024 | Changed DOH to DOR while planning for new changes to kinetics branch |
| May 01 13:45 2024 | Small changes KineticController |
| May 01 15:37 2024 | Created kineticPrecip branch off of main |
| Apr 27 23:35 2024 | Initial and fixed solution compositions both specified with DCs now |
| Apr 26 22:49 2024 | Cleaned up install instructions; force initial microstructure output |
| Apr 26 17:43 2024 | Writing PNG files now done directly. |
| Apr 24 13:24 2024 | minpozzeffect is set only if at least one kinetically pozzolanic component is detected. |
| Apr 24 11:19 2024 | KineticController has minpozzeffect as a kluge; must fix later. |
| Apr 23 15:07 2024 | Copied thameslib source files from florinTH branch. |
| Apr 04 12:13 2024 | Changed naming convention of img files, with time string now in minutes. |
| Mar 19 14:49 2024 | Better handling of color scheme for visualization of microstructure |
| Mar 19 13:41 2024 | Very minor changes to output of pore size distribution in Lattice.cc |
| Mar 19 13:33 2024 | viz program now creates one master xyz file with time stamps for Ovito |
| Mar 17 22:08 2024 | Removed createmic from main branch |
| Mar 15 14:09 2024 | Updated test file input |
| Mar 15 12:55 2024 | Merged some improvements made by Florin Nita |
| Mar 14 18:10 2024 | Added new createmic program to make THAMES input microstructures directly |
| Feb 22 09:15 2024 | Added Cemdata18 database files from EMPA to the repository; updated build instructions |
| Jan 28 15:27 2024 | Minor changes to visualization programs |
| Jan 20 15:17 2024 | Added StandardKineticModel class for dissolution of salts. Compiles and runs |
| Jan 18 10:16 2024 | Cleaned up some debugging output |
| Jan 17 00:58 2024 | Debugged behavior for adding growth sites |
| Dec 29 19:21 2023 | Formatting uniformity and added viz to build |
| Dec 23 22:34 2023 | Streamlined adjustment of microstructure volumes and output chemical shrinkage in Microstructure csv file |
| Dec 22 13:51 2023 | Total microstructure volume now forced constant and capillary porosity modified to keep it that way; actual volume still tracked |
| Dec 20 16:43 2023 | Modified pozzolanic rate law; all solid phases are increasing in volume fraction (needs debug) |
| Dec 19 22:51 2023 | Fixed retrieval of saturation index from solution object for pozzolanic kinetic step |
| Dec 19 17:18 2023 | Debugging of pozzolanic kinetics; code compiles but does not run correctly |
| Dec 18 23:36 2023 | Modified pozzolanic rate equations for diffusion and updated chemistry.xsd |
| Dec 18 16:01 2023 | Added LOI influences on clinker component reaction rates |
| Dec 18 14:09 2023 | Fixed increment of IC moles for kinetic models and added hydroxyl activity term to pozzolanic model |
| Dec 17 15:11 2023 | Added two diffusion rate constants for pozzolanic reactions, akin to the k2 and k3 parameters in the Parrot-Killoh model |
| Dec 15 16:08 2023 | Updating kinetic models to have initial specific surface areas for each phase; compile not checked |
| Dec 14 16:28 2023 | Fixed run-time errors in KineticController that were not assigning water or solid masses initially |
| Dec 08 09:50 2023 | Added more in-depth queries for Rd values and ICs; compiles error-free |
| Dec 07 17:40 2023 | Completed moved of Rd partitioning from KineticController to ChemicalSystem; compiles error-free |
| Dec 07 16:17 2023 | Moved Rd partitioning from KineticController to ChemicalSystem; compile not checked |
| Nov 11 22:42 2023 | Compile-time errors fixed; need to complete Pozzolanic model |
| Nov 10 17:48 2023 | Fixed several compile-time errors; some need to still be fixed |
| Nov 03 17:14 2023 | Making KineticController handle the models; still no compile check |
| Nov 02 01:34 2023 | Completed ParrotKillohModel.cc; still no compile check |
| Nov 01 11:38 2023 | Completed ParrotKillohModel.h; still need ParrotKillohModel.cc |
| Nov 01 11:00 2023 | Completed KineticModel and KineticController; compile not checked |
| Oct 29 21:13 2023 | Setting up multiple kinetic models; compile not checked |
| Oct 27 17:15 2023 | Distinguishing pozzolanic kinetics from Parrot-Killoh kinetics; compile not checked |
| Oct 27 16:48 2023 | Created branch pozzolan for kinetically modeling pozzolan glasses |
| Aug 10 17:02 2023 | Fixed spelling error in Interface.cc |
| Jul 31 12:46 2023 | Improved calculation of internal RH using Kelvin equation |
| Jul 30 23:28 2023 | Merge DCPorosity branch with master, added output of enthalpy |
| Jun  3 22:55 2023 | Specify and read gas phase composition.  Does not do anything with it yet |
| May 23 10:37 2023 | Fixed bug in handling of spaces in path names |
| May 23 08:05 2023 | Allow path and file names that include spaces |
| May 15 15:41 2023 | Updated test file input after rebase |
| May 15 10:52 2023 | Updated tag to 2.6.1; updated install instructions |
| May 13 14:05 2023 | Fixed minor calculation error in w/c effect of the PK model; cleaned up test cases |
| May  6 16:37 2023 | Fix behavior when GEM_run fail happens on first try |
| Apr 25 21:45 2023 | Fixed error that mistakenly "corrected" capillary pore volume for its porosity |
| Apr 30 20:59 2023 | Fuller implementation of global DEBUG preprocessor define |
| Apr 27 17:47 2023 | Removed debug as class variables and now have a global DEBUG preprocessor define |
| Apr 25 21:17 2023 | Fixed error that mistakenly "corrected" capillary pore volume for its porosity |
| Apr 24 21:45 2023 | Fixed one error in Lattice::writePoreSizeDistribution. Phase porosity still not being calculated |
| Apr 22 21:45 2023 | Fixed more runtime errors. Almost working but won't empty pores |
| Apr 21 17:46 2023 | Fixed multiple runtime errors, but still has some |
| Apr 20 14:19 2023 | Composition-dependent subvoxel porosity compiles; need to test runtime behavior |
| Apr 19 18:21 2023 | Created a branch for composition-dependent subvoxel porosity |
| Apr 14 23:54 2023 | Accounting for subvoxel porosity of microstructure phases |
| Mar 30 16:21 2023 | Adjust microstructure molar volumes based on interhydrate porosity |
| Jan 14 17:12 2023 | Corrected local path for GEMS-3K node.h include file |
| Jan  3 13:52 2023 | Tagged as version 2.6 |
| Jan  3 13:52 2023 | Assume XML schema files are in local working directory |
| Dec 29 23:28 2022 | Made silica fume a kinetic phase with a custom dissolution rate equation |
| Dec 14 13:52 2022 | Minor formatting changes |
| Jul 28 15:16 2022 | Reduced code's dependence on hard-wired phase names |
| Mar 25 19:35 2021 | Improved readability of KineticModel and ChemicalSystem classes |
| Mar 22 22:01 2021 | Added GEMS3K standalone library as a subtree |
| Mar 11 16:28 2021 | Corrected the chemistry.xml file in two of the sample-input examples |
| Mar  9 22:21 2021 | Fixed a bug that causes runtime errors when the chemistry.xml file has kinetically controlled phases separated by other types of phases |
| Mar  5 15:17 2021 | Cleaned up some comments and added new sample-input examples |
| Mar  3 15:17 2021 | Added ability to "tweak" the IC compositions slightly when a GEM run error is encountered, in the hopes of re-running the GEM run method successfully |
| Mar  1 12:02 2021 | Water-cement ratio and scaled masses now inferred directly from the microstructure |
| Feb  6 16:56 2021 | Better exception handling; better interface to new GEMS3K standalone library |
| Jan 14 19:33 2021 | Can now specifiy initial solution composition in input file |
| Jan 11 19:03 2021 | Removed growthtemplate functionality from input |
| Jan  8 20:54 2021 | Improved vcctl2thames program and integrated within cmake |
| Jan  5 20:14 2021 | Added a guide for preparing input files |
| Jan  4 16:40 2021 | Added verbose option, plus better control over output images |
| Jan  1 20:28 2021 | Better handling of void production under sealed conditions |
| Dec 28 15:38 2020 | Simulation should stop if capillary pore water is exhausted |
| Dec 22 11:36 2020 | Under sealed conditions, now emptying water from the largest capillary pores |
| Dec 18 13:22 2020 | Removed hard-wired code for ettringite crystallization pressure |
| Dec 16 13:15 2020 | Minor change to Controller |
| Dec  7 13:25 2020 | Added new input and output examples |
| Dec  6 20:16 2020 | Added ability to do saturated or sealed curing, plus adjustable wc ratio in the chemistry.xml file alone |
| Dec  3 17:44 2020 | Enabling w/c ratio to determine initial water content (still needs work).  Also moved GEMS3K library outside of project |
| Nov 20 17:31 2020 | New input files and modified simulation type flags behavior |
| Nov 20 16:00 2020 | Damage file only created when sulfate attack simulation |
| Nov 20 13:19 2020 | Slight tweak to gitignore file |
| Dec 17 15:23 2019 | Minor changes to DISCLAIMER.md |
| Dec 17 15:22 2019 | Modified gitignore file |
| Dec 17 15:18 2019 | Modified gitignore file |
| Dec 17 15:15 2019 | Added a gitignore file |
| Jun 26 15:32 2019 | Better time logging in output files and more accurate image generation |
| Apr 23 16:52 2019 | Modified lattice dimensions when adding sites (Lattice::addSite) and modified myconfig.h so that it gets customized when cmake is executed |
| Mar 08 17:46 2019 | Added build directory |
| Apr 13 14:55 2017 | Added table markdown for README.md |
| Apr 13 14:48 2017 | Updated formatting of README.md |
| Apr 13 14:45 2017 | Testing markdown formatting of bulleted lists |
| Apr 13 14:37 2017 | Initial committing of THAMES for GitHub remote repository |
| Apr 13 13:12 2017 | Update README.md and corrected name spelling |
| Apr 27 11:22 2015 | Initial commit |
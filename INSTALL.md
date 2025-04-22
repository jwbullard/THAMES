# INSTALL

## INTRODUCTION

This file describes how to install THAMES v4.0.  The instructions in this file
are for the most common use cases, and cover the command line tools.

For further information, or in case of problems, please contact the author,
Jeff Bullard (jeffrey.bullard@nist.gov).

The API documentation of THAMES is available in PDF and HTML formats.  It
is not bundled with the software but can be created during the installation
of the software.

For more information about THAMES, see the API documentation overview, or
the accompanying user guide (coming soon).  More information about THAMES and
its applications can also be found in the following references:

   * Bullard, J.W., Lothenbach, B., Stutzman, P.E., Snyder, K.A., Coupling thermodynamics and digital image models to simulate hydration and microstructure development of portland cement pastes, _Journal of Materials Research_ 26, (2011) 609-622.

   * Feng, P., Miao, C., Bullard, J.W., A model of phase stability, microstructure and properties during leaching of portland cement binders, _Cement and Concrete Composites_ 49, (2014) 9-19.

   * Li, X., Grasley, Z.C., Garboczi, E.J., Bullard, J.W., Modeling the apparent intrinsic viscoelastic relaxation of hydrating cement paste, _Cement and Concrete Composites_ 55, (2014) 322-330.

   * Feng, P., Garboczi, E.J., Miao, C., Bullard, J.W., Microstructural origins of cement paste degradation by external sulfate attack, _Construction and Building Materials_ 96, (2015) 391-403.

   * Li, X., Grasley, Z.C., Bullard, J.W., Garboczi, E.J., Computing the time evolution of the apparent viscoelastic/viscoplastic Poisson's ratio of hydrating cement paste, _Cement and Concrete Composites_, 56 (2015) 121-133.


## PREREQUISITES

* GNU Compiler Collection (gcc/g++ >= 11, REQUIRED)
 * Mac OS no longer uses true gcc/g++, despite the fact that
 Apple provides shortcuts called gcc and g++ to its own Apple Clang
 compiler.  So on a Mac you _must_ install the actual gcc/g++ and
 make it the default compiler, at least long enough to build THAMES.
 Instructions are provided in the section below for building on Mac OS.

* CMake (>= 3.5), the build system used by THAMES
 * Required for building THAMES

* Doxygen (>= 1.8.13), the API documentation software
 * Required for creating the API documentation

* LaTeX 2e, the document preparation system
 * Required only for creating the PDF version of the API documentation

* GEM-Selektor (optional)
 * Needed for producing input data files for thermodynamic calculations.
 * Source code available at https://bitbucket.org/gems4/gems3gui.git
 * Binaries available at https://gems.web.psi.ch

## Building on Mac OS

As already stated, modern Mac OS uses the Apple Clang compiler by default,
but THAMES requires the GNU Compiler Collection (gcc).
Therefore you must install the Gnu compiler suite and then
make it the default C/C++ compiler on your computer. Assuming you
use Homebrew for package management:

* `brew install gcc`
* `cd /opt/homebrew/bin`
* `ln -s gcc-13 gcc`
* `ln -s g++-13 g++`
* Edit your path to ensure that `/opt/homebrew/bin` comes before `/usr/bin`

### Build GEMS3K library

* cd /PathToTHAMES/THAMES/src/GEMS3K-standalone
* Open the file `install.sh` with your favorite text editor.
* Comment out the line that begins with `cmake ..` by placing a `#` in the first column.
* Add a line directly below it that reads

```
cmake .. -DCMAKE_C_COMPILER=/opt/homebrew/bin/gcc -DCMAKE_CXX_COMPILER=/opt/homebrew/bin/g++ -DCMAKE_CXX_FLAGS=-fPIC -DCMAKE_BUILD_TYPE=$BuildType -DCMAKE_OSX_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX14.5.sdk -DCMAKE_INSTALL_PREFIX=$InstallPrefix 
```
* Save the `install.sh` file and close it
* Run the command `./install.sh`

### Build THAMES
Next, build and install THAMES. The recommended way to configure THAMES is to do an out-of-source
build, which means that the original files and directories are left untouched.
Doing this makes the re-compiling and cleaning of the installation files
much simpler.

* cd /PathToTHAMES/THAMES/build
* Run the command

```
cmake -DCMAKE_C_COMPILER=/opt/homebrew/bin/gcc -DCMAKE_CXX_COMPILER=/opt/homebrew/bin/g++ -DCMAKE_OSX_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX14.5.sdk ..
```
* `make`
* `make install`

This will install the "thames" executable in the /PathToTHAMES/bin directory, and the
static libraries in the PathToTHAMES/lib directory.


## Building on Unix or Linux

### Build GEMS3K library

1. cd /PathToTHAMES/THAMES/src/GEMS3K-standalone
2. ./install.sh

### Build THAMES
Next, build and install THAMES. The recommended way to configure THAMES is to do an out-of-source
build, which means that the original files and directories are left untouched.
Doing this makes the re-compiling and cleaning of the installation files
much simpler.

1. cd /PathToTHAMES/THAMES/build
2. `cmake ..`
3. `make`
4. `make install`
5. `make doc`

This will install the "thames" executable in the /PathToTHAMES/bin directory, and the
static libraries in the PathToTHAMES/lib directory.

## Building on Windows

Windows does not come prebuilt with any kind
of system for compiling C/C++ code, but it they have made it easier to get a full Linux environment set up, which is part of these instructions.  Therefore

### Install WSL

- Switch to admin user
- Type `powershell` in the search bar.
- In the powershell window, type `wsl --install`
- Reboot computer, select userid and password

### Install GEMS3K Library

- Start up Ubuntu by typing `ubuntu` in the search bar.
- sudo apt update
- sudo apt install git
- sudo apt install cmake
- sudo apt install build-essential
- git clone https://github.com/jwbullard/THAMES.git
- Wait for the THAMES folder to fully download
- In the Windows file explorer, navigate to Linux/home/THAMES/src/GEMS3K-standalone
- Open the file install.h with Notepad
- Comment out the line that begins with `cmake ..` by placing a `#` in the first column.
- Add a line directly below it that reads

```
cmake .. -DCMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_CXX_COMPILER=/usr/bin/g++ -DCMAKE_CXX_FLAGS=-fPIC -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=../../Resources 
```
- Save the `install.sh` file and close the file explorer
- Back in the powershell, `cd THAMES/src/GEMS3K-standalone`
- ./install.sh
- cd ../../build
- Run this command:
```
cmake .. -DCMAKE_C_COMPILER=/usr/bin/gcc -DCMAKE_CXX_COMPILER=/usr/bin/g++ -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=../bin 
```
- make
- make install

This procedure should install the `thames` and `viz` executables in the Linux/home/THAMES/bin folder

## UNINSTALLING

To uninstall everything except the original source files, simply delete
recursively everything in the build/ directory.

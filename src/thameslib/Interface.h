/**
@file Interface.h
@brief Declaration of the Interface class.

@section Introduction
THAMES reads an input table of the mass fraction of
each phase at each calculated time.  Regardless of how this
table is generated, it must be stored by THAMES to use
to modify the lattice at each time increment.

This document describes a class called `Interface`, which is
primarily used to store the list of sites of each phase that are
at an interface with one or more other phases.

@section Description
The `Interface` class is basically an STL vector data structure with
some functions to access or modify that data.

@todo Add more exception handling besides what is in the constructor,
especially for sorting operations and removing or adding elements to vectors.
*/

#ifndef SRC_THAMESLIB_INTERFACE_H_
#define SRC_THAMESLIB_INTERFACE_H_

#include "global.h"
#include "Exceptions.h"
#include "Isite.h"
#include "Site.h"

/**
@class Declare the Interface class for handling and sorting interface voxels.
The Interface object is a collection of voxels of all the same phase that share
at least one face with a different type of phase voxel.  We have containers for
storing the list of voxels and for sorting the list in descending order of
potential for dissolution.
*/
class Interface {

private:
  int microPhaseId_;               /**< The phase id of the voxels at this
                                        interface */
  ChemicalSystem *chemSys_;        /**< The `ChemicalSystem` object for the
                                        simulation */
  std::vector<Isite> growthSites_; /**< The list of all sites eligible for
                                        adjacent growth */

  std::vector<Isite> dissolutionSites_; /**< The list of sites eligible for
                                             self-dissolution */
  bool verbose_;                        /**< Flag for verbose output */

  std::vector<int> affinityInt_;

public:
  /**
  @brief The default constructor, initializing members to empty or zero values.

  @note NOT USED.
  */
  Interface();

  /**
  @brief Overloaded constructor initializing the random number generator.

  @param rg is a pointer to the random number generator object to assign
  @param verbose is true if verbose output should be produced
  */
  Interface(const bool verbose);

  /**
  @brief Overloaded constructor, initializing all members to prescribed values.

  @param csys is a pointer to the ChemicalSystem object being used in the
  simulation
  @param rg is a pointer to the random number generator
  @param gv is the list of pointers to growth sites adjacent to the interface
  for this phase
  @param dv is the list of pointers to dissolution sites of this interface
  @param pid is the integer id of the phase associated with this interface
  @param verbose is true if verbose output should be produced
  */
  Interface(ChemicalSystem *csys, std::vector<Site *> gv,
            std::vector<Site *> dv, unsigned int pid, const bool verbose);

  /**
  @brief Destructor for the Interface class.

  */
  ~Interface();

  /**
  @brief Gets the integer phase id associated with this interface.

  @note NOT USED?

  @return the integer id for the phase associated with this interface
  */
  int getMicroPhaseId(void) const { return microPhaseId_; }

  // void setMicroPhaseId(int mPhId) { microPhaseId_ = mPhId; }

  /**
  @brief Gets the list of sites where growth of this phase can occur adjacent to
  the interface.

  @return the vector of Isite objects where growth can occur
  */
  std::vector<Isite> getGrowthSites(void) { return growthSites_; }

  /**
  @brief Gets the size of the growthSites_ vector

  @return the size of growthSites_
  */
  // int getGrowthSize(void) { return growthSites_.size(); }

  /**
  @brief Gets the size of the dissolutionSites_ vector

  @return the size of dissolutionSites_
  */
  // int getDissolutionSize(void) { return dissolutionSites_.size(); }

  /**
  @brief Set the growth interface of this microPhase

  @param vect is a vector containing all Isite objects belonging to the growth
  interface oh this microPhase
  */
  void setGrowthSites(std::vector<Isite> vect) { growthSites_ = vect; }

  /**
  @brief Get the isite id (or equivalently the site id) beeing on the position pos
  of the growth interface of this microPhase

  @param pos is the isite position on the growth interface of this microPhase
  @return the isite id (or equivalently the site id) beeing on the position pos
  of the growth interface of this microPhase
  */
  int getGrowthSitesId(int pos) { return growthSites_[pos].getId(); }

  /**
  @brief Get the isite id (or equivalently the site id) beeing on the position pos
  of the dissolution interface of this microPhase

  @param pos is the isite position on the dissolution interface of this microPhase
  @return the isite id (or equivalently the site id) beeing on the position pos
  of the dissolution interface of this microPhase
  */
  int getDissolutionSitesId(int pos) { return dissolutionSites_[pos].getId(); }

  /**
  @brief Get the list of isites, or equivalently the dissolution interface of
  this microPhase

  @return the vector of Isite objects corresponding to the sites where dissolution
  can occur for this microPhase
  */
  std::vector<Isite> getDissolutionSites(void) { return dissolutionSites_; }

  /**
  @brief Set the dissolution interface of this microPhase to the one corresponding
  to a previously saved microStructure configuration.

  @param vect is the vector containing the previously saved dissolution interface
  of this microPhase
  */
  void setDissolutionSites(std::vector<Isite> vect) { dissolutionSites_ = vect; }

  /**
  @brief Add a site to the list of sites where growth can occur adjacent to the
  interface.

  @param loc is a pointer to the site to add to the list of growth sites
  @return true if the site was added successfully, false otherwise
  */
  void addGrowthSite(Site *loc);

  /**
  @brief Add a site to the list of sites where dissolution can occur at the
  interface.

  @param loc is a pointer to the site to add to the list of dissolution sites
  @return true if the site was added successfully, false otherwise
  */
  void addDissolutionSite(Site *loc);

  /**
  @brief Sort the list of growth sites in descending order of potential for
  growth event

  @param ste is the list of sites to sort for growth potential
  @param pid is the phase that could grow at these sites
  @return true if the list was sorted successfully, false otherwise
  */
  // bool sortGrowthSites(std::vector<Site> &ste, unsigned int pid);

  /**
  @brief Sort the list of dissolution sites in descending order of potential for
  dissolution event

  @param ste is the list of sites to sort for dissolution potential
  @param pid is the phase that could dissolve at these sites
  @return true if the list was sorted successfully, false otherwise
  */
  // bool sortDissolutionSites(std::vector<Site> &ste, unsigned int pid);

  /**
  @brief Remove an isite from the growth interface of this microPhase
  (equivalent: remove a site from the growth interface of this microPhase)

  @param pos0 is the position of the isite that must be removed from the
  growth interface of this microPhase
  @param pos1 = size - 1, where size is the growth interface dimension
  of this microPhase
  */
  void removeGrowthSite(int pos0, int pos1);

  /**
  @brief Remove an isite from the dissolution interface of this microPhase
  (equivalent: remove a site from the dissolution interface of this microPhase)

  @param pos0 is the position of the isite that must be removed from the
  dissolution interface of this microPhase
  @param pos1 = size - 1, where size is the dissolution interface dimension
  of this microPhase
  */
  void removeDissolutionSite(int pos0, int pos1);

  /**
  @brief Set the verbose flag

  @param isverbose is true if verbose output should be produced
  */
  void setVerbose(const bool isverbose) { verbose_ = isverbose; }

  /**
  @brief Get the verbose flag

  @return the verbose flag
  */
  bool getVerbose(void) const { return verbose_; }

  /**
  @brief Update the growth affinity of the Isite object placed on the position
  pos of this growth interface (belonging to this microPhase).

  @param pos is the position of the Isite object to be updated
  @param afty is the value that must be added to the already growth affinity
  value of the Isite object
  */
  void updateAffinityInt(int pos, int afty) {
    growthSites_[pos].updateAffinityInt(afty);
  }

  /**
  @brief Get the growth affinity of the Isite object placed on the position
  pos of this growth interface (belonging to this microPhase).

  @param pos is the position of the Isite object on the position pos of this
  growth interface
  @return the growth affinity of the Isite object placed on the positionv pos
  of this growth interface (belonging to this microPhase).
  */
  int getAffinityInt(int pos) { return growthSites_[pos].getAffinityInt(); }

}; // End of Interface class

#endif

///
/// The functions below are used to aid in comparison of one site to another, by
/// which means lists of the sites can be sorted.
///

#ifndef CMPFUNCS
#define CMPFUNCS

/**
@brief Compare two sites, returning true is the first site is "less than" the
second.

The comparison is made on the basis of what THAMES loosely calls the
<i>weighted mean curvature</i>, (wmc).  A site with high wmc is a site where
dissolution of a phase is likely to occur, and growth of another phase is
unlikely to occur. Conversely, a site with a low wmc is a site where growth of a
phase is likely to occur but dissolution of a phase is unlikely to occur.

@param s1 is a pointer to the first site in the comparison
@param s2 is a pointer to the second site in the comparison
@return true if the first site has lower wmc than the second, false otherwise
*/
bool cmp(const Site *s1, const Site *s2);

/**
@brief Sort two sites based on their affinity for a given phase.

The comparison is made on the basis of what THAMES loosely calls the
<i>affinity</i>.  A site with high affinity is a site where growth of a phase
is more likely to occur because of an affinity between it and the interface.

@param s1 is the first site in the comparison
@param s2 is the second site in the comparison
@return true if the first site has <i>greater</i> affinity than the second,
false otherwise
*/
bool affinitySort(const Isite s1, const Isite s2);

#endif // SRC_THAMESLIB_INTERFACE_H_

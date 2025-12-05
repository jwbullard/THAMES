#ifndef THAMESAUX_H
#define THAMESAUX_H
/***
 *	This is the public header file required for
 *	VCCTL programs.  Every VCCTL program that wishes
 *	to operate within the VCCTL system must include
 *	this header file
 *
 *	Programmer:  Jeffrey W. Bullard
 *				 NIST
 *				 100 Bureau Drive Stop 8615
 *				 Gaithersburg, MD  20899-8615
 *
 *				 Phone:	301.975.5725
 *				 Fax:	301.990.6892
 *				 bullard@nist.gov
 *
 *				 15 March 2004
 ***/
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/***
 *	Version number string and version number
 *	for identifying the version under which a
 *	particular file was created
 ***/
#define VERSIONSTRING "#THAMES:Version:"
#define VERSIONNUMBER "5.2"

#define MAXSTRING 500 /* maximum length of strings */

/***
 *	ImageMagick convert command
 ***/
#define CONVERT "/usr/bin/convert"

/***
 *	Shell command
 ***/
#define SHELL "bash"

/*******************************************************
 * Variables related to system size and
 * resolution
 *******************************************************/

#define MAXSIZE 400 /* maximum system size in pixels per dimension */
#define DEFAULTSYSTEMSIZE 100

#define DEFAULTRESOLUTION 1.0

#define XSIZESTRING "#THAMES:X_Size:"
#define YSIZESTRING "#THAMES:Y_Size:"
#define ZSIZESTRING "#THAMES:Z_Size:"
#define IMGRESSTRING "#THAMES:Image_Resolution:"

/***
 *	Pre-defined strings for info files
 ***/
#define AGGTHICKSTRING "Aggregate_thickness:"
#define PFILESTRING "Particle_file:"
#define NUM1PIXSTRING "One_pixel_particles:"
#define VFALITESTRING "Vol_frac_Alite:"
#define VFBELITESTRING "Vol_frac_Belite:"
#define VFALUMINATESTRING "Vol_frac_Aluminate:"
#define VFFERRITESTRING "Vol_frac_Ferrite:"
#define VFARCANITESTRING "Vol_frac_Arcanite:"
#define VFTHENARDITESTRING "Vol_frac_Thenardite:"
#define SFALITESTRING "Surf_frac_Alite:"
#define SFBELITESTRING "Surf_frac_Belite:"
#define SFALUMINATESTRING "Surf_frac_Aluminate:"
#define SFFERRITESTRING "Surf_frac_Ferrite:"
#define SFARCANITESTRING "Surf_frac_Arcanite:"
#define SFTHENARDITESTRING "Surf_frac_Thenardite:"
#define VFGYPSTRING "Vol_frac_Dihydrate:"
#define VFHEMSTRING "Vol_frac_Hemihydrate:"
#define VFANHSTRING "Vol_frac_Anhydrite:"

/******************************************************
 * Define phase identifier for all species
 ******************************************************/

/***
 *	To add a new solid phase, insert its id before
 *	NSPHASES, and adjust the parameter directly
 *	underneath it.
 ***/

/***
 *	These are phases present in unhydrated
 *	blended cements
 ***/

#define VOID 0
#define ELECTROLYTE 1
#define ALITE 2
#define BELITE 3
#define ALUMINATE 4
#define FERRITE 5
#define ARCANITE 6
#define THENARDITE 7

#define FIRSTCLINKER 2
#define LASTCLINKER 7

#define AGGSLAB 8

/* typedefs */

/* A coloured pixel. */

typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} pixel_t;

/* Support for image rendering */

/* A picture. */

typedef struct {
  pixel_t *pixels;
  size_t width;
  size_t height;
} bitmap_t;

/* Different types of arrays */

typedef struct {
  size_t xsize;
  int *val;
} Int1d;

typedef struct {
  size_t xsize;
  short int *val;
} ShortInt1d;

typedef struct {
  size_t xsize;
  long int *val;
} LongInt1d;

typedef struct {
  size_t xsize;
  float *val;
} Float1d;

typedef struct {
  size_t xsize;
  float *val;
} Double1d;

typedef struct {
  size_t xsize;
  pixel_t *val;
} Pixel1d;

typedef struct {
  size_t xsize;
  size_t ysize;
  int *val;
} Int2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  short int *val;
} ShortInt2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  long int *val;
} LongInt2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  float *val;
} Float2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  double *val;
} Double2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  char *val;
} Char2d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  int *val;
} Int3d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  short int *val;
} ShortInt3d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  long int *val;
} LongInt3d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  float *val;
} Float3d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  double *val;
} Double3d;

typedef struct {
  size_t xsize;
  size_t ysize;
  size_t zsize;
  char *val;
} Char3d;

/***
 *	Function declarations needed by MICGEN
 ***/
#include "thamescomplex.h"
#include "thamesfuncs.h"

#endif

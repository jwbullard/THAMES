#include "../include/thamesaux.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/***
 *    Function declarations
 ***/

/***
 *    maketemp
 *
 *    Routine to create a template for the sphere of
 *    interest of radius size to be used in
 *    curvature evaluation
 *
 *    Arguments:  int size (the radius of the sphere)
 *                int pointer to xsph vector
 *                int pointer to ysph vector
 *                int pointer to zsph vector
 *    Returns:    int number of pixels in sphere
 *
 *    Calls:		no other routines
 *    Called by:	runsint
 ***/
int maketemp(int size, int *xsph, int *ysph, int *zsph) {
  int icirc, xval, yval, zval;
  float xtmp, ytmp, dist;

  /***
   *   Determine and store the locations of all
   *   pixels in the 3-D sphere
   ***/

  icirc = 0;
  for (xval = (-size); xval <= size; xval++) {

    xtmp = (float)(xval * xval);
    for (yval = (-size); yval <= size; yval++) {

      ytmp = (float)(yval * yval);
      for (zval = (-size); zval <= size; zval++) {

        dist = sqrt(xtmp + ytmp + (float)(zval * zval));

        if (dist <= ((float)size + 0.5)) {

          xsph[icirc] = xval;
          ysph[icirc] = yval;
          zsph[icirc] = zval;
          icirc++;
        }
      }
    }
  }

  /***
   *   Return the number of pixels contained in
   *   sphere of radius (size+0.5)
   ***/

  return (icirc);
}

/***
*    pix2x
*
*    Convert pixel id number to x coordinate
*    Assumes C-ordering
*
*    Arguments:    int pixel id number
                   int xsize,ysize,zsize are the x,y,z dimensions of the system
*    Returns:      int x coordinate
*
*    Calls:        no other routines
*    Called by:    calcporedist3d
***/
int pix2x(int pid, int xsize, int ysize, int zsize) {
  int x = pid / (ysize * zsize);
  return (x);
}

/***
*    pix2y
*
*    Convert pixel id number to y coordinate
*    Assumes C-ordering
*
*    Arguments:    int pixel id number
                   int xsize,ysize,zsize are the x,y,z dimensions of the system
*    Returns:      int y coordinate
*
*    Calls:        no other routines
*    Called by:    calcporedist3d
***/
int pix2y(int pid, int xsize, int ysize, int zsize) {
  int x, y;
  x = pid / (ysize * zsize);
  y = (pid - (x * ysize * zsize)) / zsize;
  return (y);
}

/***
*    pix2z
*
*    Convert pixel id number to z coordinate
*    Assumes C-ordering
*
*    Arguments:    int pixel id number
                   int xsize,ysize,zsize are the x,y,z dimensions of the system
*    Returns:      int z coordinate
*
*    Calls:        no other routines
*    Called by:    calcporedist3d
***/
int pix2z(int pid, int xsize, int ysize, int zsize) {
  int x, y, z;
  x = pid / (ysize * zsize);
  y = (pid - (x * ysize * zsize)) / zsize;
  z = (pid - (x * ysize * zsize) - (y * zsize));
  return (z);
}

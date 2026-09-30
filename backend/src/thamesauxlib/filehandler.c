/******************************************************************************
 *	Function filehandler does graceful handling of opening
 *	files for various input/output combinations as requested
 *	by function call, and also prints nice message to stdout
 *	if something goes wrong.
 *
 *	Programmer:	Jeffrey W. Bullard
 *				NIST
 *				100 Bureau Drive, Stop 8615
 *				Gaithersburg, Maryland  20899-8615
 *				USA
 *
 *				Phone:	301.975.5725
 *				Fax:	301.990.6891
 *				bullard@nist.gov
 *
 *	16 March 2004
 ******************************************************************************/
#include "../include/thamesaux.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

FILE *filehandler(char *prog, char *filename, char *tocheck) {
  FILE *fptr;

  fptr = NULL;

  /***
   *	A missing name is not a bad name, and "verify the file name" sends the
   *	reader looking for a name that was never there. It normally means the
   *	caller had nothing to build the name from: for micgen and elastic, that
   *	the working directory was not supplied, since every output path is
   *	formed by prepending it.
   ***/

  if (filename == NULL || filename[0] == '\0') {
    printf("\nERROR in %s:", prog);
    printf("\n\tNo file name was supplied for a %s operation.", tocheck);
    printf("\n\tThis usually means a required argument is missing, such as");
    printf("\n\tthe working directory (-w,--workdir), which every output");
    printf("\n\tpath is built from. Program is exiting now.\n\n");
    fflush(stdout);
    return (NULL);
  }

  if (!strcmp(tocheck, "NOCLOBBER")) {
    if ((fptr = fopen(filename, "r")) != NULL) {
      printf("\nERROR in %s:", prog);
      printf("\n\tFile %s already exists.", filename);
      printf("\n\tPlease verify file name. Program is ");
      printf("exiting now.\n\n");
      fflush(stdout);
      fclose(fptr);
      fptr = NULL;
    } else if ((fptr = fopen(filename, "w")) == NULL) {
      printf("\nERROR in %s:", prog);
      printf("\n\tCould not create file %s", filename);
      printf("\n\t(%s)", strerror(errno));
      printf("\n\tPlease verify write permissions. Program is ");
      printf("exiting now.\n\n");
      fflush(stdout);
    }
  } else if (!strcmp(tocheck, "READ")) {

    if ((fptr = fopen(filename, "r")) == NULL) {
      printf("\nERROR in %s:", prog);
      printf("\n\tFile %s could not be opened for ", filename);
      printf("reading.");
      printf("\n\t(%s)", strerror(errno));
      printf("\n\tPlease verify file name. Program is ");
      printf("exiting now.\n\n");
      fflush(stdout);
    }

  } else if (!strcmp(tocheck, "READ_NOFAIL")) {

    fptr = fopen(filename, "r");

  } else if (!strcmp(tocheck, "WRITE")) {

    if ((fptr = fopen(filename, "w")) == NULL) {
      printf("\nERROR in %s:", prog);
      printf("\n\tFile %s could not be created.", filename);
      printf("\n\t(%s)", strerror(errno));
      printf("\n\tPlease verify the path exists and is writable. Program is ");
      printf("exiting now.\n\n");
      fflush(stdout);
    }

  } else if (!strcmp(tocheck, "APPEND")) {

    if ((fptr = fopen(filename, "a")) == NULL) {
      printf("\nERROR in %s:", prog);
      printf("\n\tFile %s could not be opened for ", filename);
      printf("appending.");
      printf("\n\t(%s)", strerror(errno));
      printf("\n\tPlease verify file name. Program ");
      printf("is exiting now.\n\n");
      fflush(stdout);
    }
  }

  return (fptr);
}

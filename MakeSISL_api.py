"""
	Creates a python interface module for the sisl library.
	Only a part of the functions is encapsulated (see header code below in s_declarations)
	see https://github.com/SINTEF-Geometry/SISL
	Must be started manually in folder .../zutils
	If new functions have to be added, edit variable s_declarations below and restart

	Creation of sisl.lib under Windows:
	download as zip from github under "Code"
	install cmake (update windows search path)
	start cmake-gui.exe
		enter sisl source folder (folder containing CMakeLists.txt)
		enter destination folder
		select a compiler that is installed on your machine
		(if you use Visual Studio, do not forget to install C/C++)
		click "generate"
	in destination folder should be e.g. a ...sln file
	open it with the selected compiler and create library (Release might be preferable)
	find the Release\\sisl.lib file (use its folder as  <SISLLIBDIR> below)

	cd to folder .../zutils
	Now start this script: python MakeSISL_api.py <SISLLIBDIR>	(as <SISLLIBDIR> use folder containing sisl.lib from above)
	(warning "inconsistent definition of free()" is ignored by me - seems no problem)

"""


#######################################################
#######################################################

import sys
import os
from cffi import FFI

s_ffi = FFI()
s_sislLibDir = ''
s_sislLib = 'sisl'

s_declarations = """
////////////////////////////////////////////////////////
// general stuff:
////////////////////////////////////////////////////////

void __cdecl free(void*);	// brings a warning, i just ignore it: (be cautious with the backslashes!!!:)
							// conflict with C:\\Program Files (x86)\\Windows Kits\\10\\include\\10.0.19041.0\\ucrt\\corecrt_malloc.h(89)

////////////////////////////////////////////////////////
// SISL stuff:
////////////////////////////////////////////////////////
// dummies:
typedef struct{int c;} SISLdir;
typedef struct{int c;} SISLbox;
typedef struct{int c;} SISLIntcurve;

/////////////////////////////////////////////////////////
// curve stuff:
/////////////////////////////////////////////////////////

typedef struct SISLCurve
{
  int ik;			/* Order of curve.                           */
  int in;			/* Number of vertices.                       */
  double *et;			/* Pointer to the knotvector.                */
  double *ecoef;		/* Pointer to the array containing vertices. */
  double *rcoef;		/*Pointer to the array of scaled vertices if
				  rational.  */
  int ikind;			/* Kind of curve
	                           = 1 : Polynomial B-spline curve.
	                           = 2 : Rational B-spline curve.
	                           = 3 : Polynomial Bezier curve.
	                           = 4 : Rational Bezier curve.             */
  int idim;			/* Dimension of the space in which the curve
				   lies.      */
  int icopy;			/* Indicates whether the arrays of the curve
				   are copied or referenced by creation of the
				   curve.
	                           = 0 : Pointer set to input arrays.
			           = 1 : Copied.
	                           = 2 : Pointer set to input arrays,
				         but are to be treated as copied.   */
  SISLdir *pdir;		/* Pointer to a structur to store curve
				   direction.      */
  SISLbox *pbox;		/* Pointer to a structur to store the
				   surrounded boxes. */
  int cuopen;			/* Open/closed flag.                         */
} SISLCurve;

/////////// curve functions:

void freeCurve(SISLCurve *);
void freeIntcurve(SISLIntcurve *);
void freeIntcrvlist(SISLIntcurve **,int);

SISLCurve *copyCurve(SISLCurve *);

// revert the curve
void s1706(SISLCurve *curve);

// get curve parameter range:
void s1363(SISLCurve *, double *, double *, int *);

// getCurvePoints at all given parameters:
void s1542(SISLCurve *, int, double *, double [], int *);

// getIntersectionWithPlane:
void s1850(SISLCurve *,double [],double [],int,double,double,int *,double **,int *,SISLIntcurve ***,int *);

// subDivideAtParameter
void s1710(SISLCurve *,double,SISLCurve **,SISLCurve **,int *);

// join2Curves
void s1715(SISLCurve *,SISLCurve *,int,int,SISLCurve **,int *);

// createCurveFromStraightLine:
void s1602(double [],double [],int,int,double,double *,SISLCurve **,int *);

// create curve from control points:
void s1630(double [],int,double,int,int,int,SISLCurve **,int *);

// create new curve:
SISLCurve *newCurve(int,int,double *,double *,int,int,int);

//////////////////////////////////////////////////////////////////
/////  surface stuff
//////////////////////////////////////////////////////////////////

// dummies:
typedef struct{int c;} SISLSegmentation;

typedef struct SISLSurf
{
  int ik1;			/* Order of surface in first parameter
				   direction.       */
  int ik2;			/* Order of surface in second parameter
				   direction.      */
  int in1;			/* Number of vertices in first parameter
				   direction.     */
  int in2;			/* Number of vertices in second parameter
				   direction.    */
  double *et1;			/* Pointer to knotvector in first parameter
				   direction.  */
  double *et2;			/* Pointer to knotvector in second parameter
				   direction. */
  double *ecoef;		/* Pointer to array of vertices of surface. */
  double *rcoef;		/* Pointer to the array of scaled vertices
				   if surface is rational. */
  int ikind;			/* Kind of surface
	                           = 1 : Polynomial B-spline tensor-product
				         surface.
	                           = 2 : Rational B-spline tensor-product
				         surface.
	                           = 3 : Polynomial Bezier tensor-product
				         surface.
	                           = 4 : Rational Bezier tensor-product
				         surface.                           */
  int idim;			/* Dimension of the space in which the surface
				   lies.    */
  int icopy;			/* Indicates whether the arrays of the surface
				   are copied or referenced by creation of
				   the surface.
	                           = 0 : Pointer set to input arrays.
			           = 1 : Copied.
	                           = 2 : Pointer set to input arrays,
				         but are to be treated as copied.               */
  SISLdir *pdir;		/* Pointer to a structur to store surface
				   direction.    */
  SISLbox *pbox;		/* Pointer to a structur to store the
				   surrounded boxes. */
  int use_count;                /* use count so that several tracks can share
				   surfaces, no internal use */
 int cuopen_1;                  /* Open/closed flag, 1. par directiion */
 int cuopen_2;                  /* Open/closed flag. 2. par direction  */
  SISLSegmentation *seg1;       /* Segmentation information for use in
				   intersection functionality, 1. par. dir. */
  SISLSegmentation *seg2;       /* Segmentation information for use in
				   intersection functionality, 2. par. dir. */
  int sf_type;        /* SURFACE_TYPE, Flag for special surface information */
} SISLSurf;

///////////// surface functions:

void freeSurf(SISLSurf *);

// get surface parameter range:
void s1603(SISLSurf *,double *,double *,double *,double *,int *);

// get surface points and normals for regular grid
void s1506(SISLSurf *,int,int,double *,int,double *,double [], double [],int *);

// getDerivationAsSurface
void s1386(SISLSurf *,int,int,SISLSurf **,int *);

// findClosestPointSimple
void s1958(SISLSurf *,double [],int,double,double,double [],double *,int *);

// getPointAndDerivativesAndNormalAtParameters
void s1421(SISLSurf *,int,double [],int *,int *,double [],double [],int *);

// pickACurveAtParameter
void s1439(SISLSurf *,double,int,SISLCurve **,int *);

// createLoftedSurfaceFromBSplines:
void s1538(int, SISLCurve *[],int [],double,int,int,int,SISLSurf **, double **,int *);

// create surface from vertices and knots:
SISLSurf *newSurf(int,int,int,int,double *,double *,double *,int,int,int);

// Compute a first derivative continuous blending surface set, 
// over a 3-, 4-, 5- or 6-sided region in space,
// from a set of B-spline input curves.
void s1391(SISLCurve **,SISLSurf ***,int,int [],int *);

"""


argv = sys.argv

if len(argv) != 2:
	print ('usage: python MakeSISL_api.py <sislLibDir>')
	exit(1)
s_sislLibDir = argv[1]
if not os.path.isdir(s_sislLibDir):
	print (s_sislLibDir + ' is not a folder - terminating')
	exit(1)
lib = s_sislLibDir + '/sisl.lib'
if not os.path.isfile(lib):
	print(f'file {lib} does not exist - terminating')
	exit(1)

s_ffi.cdef(s_declarations)

s_ffi.set_source('sisl_adapt', s_declarations, libraries=[s_sislLib], library_dirs=[s_sislLibDir])

s_ffi.compile(verbose=True)

"""
	Contains those classes:
	- SislObjectHolder
	- SislCurveHolder
	- SislSurfaceHolder
	- SislLoftedSurfaceHolder
	- LoftedSurfaceCurveType (enum for creating lofted surfaces)
	The only module that should be used from outside python.
	Encapsulates usage of the SISL functions from within python
	see https://github.com/SINTEF-Geometry/SISL
	Presupposes creation of zutils.sisl_adapt (see zutils.MakeSisl_api.py)
"""


from __future__ import annotations
import math
from enum import IntEnum

from zutils.ZGeom import Point
from zutils.ZMatrix import Matrix, Affine
import zutils.sisl_adapt as sl


########################################################
########################################################


class SislObjectHolder:
	"""
		Common superclass for SislCurveHolder, SislSurfaceHolder, ....
	"""
	s_spaceDimension = 3

	def __init__(self, structPtr):
		self.m_structPtr = structPtr
		self.m_massCenter = None


	def __del__(self):
		"""
			Release my resources. Is automatically called at GC time
		"""
		self.free()


	@classmethod
	def makePointArray(cls, points: list[Point]) -> sl.ffi.cdata:
		"""
			Return an ffi array of doubles, that contains all the coordinates
		"""
		if isinstance(points, Point):
			return cls.makePointArray([points])
		ret = cls.makeDoubleArray(3 * len(points))
		idx = 0
		for p in points:
			for ii in range(3):
				ret[idx] = p[ii]
				idx += 1
		return ret


	@classmethod
	def makeDoubleArray(cls, num: int) -> sl.ffi.cdata:
		"""
			Return a ffi array holding space for num doubles
		"""
		return sl.ffi.new('double[]', num)


	@classmethod
	def makeDoubleArrayWithValues(cls, values: list[float]) -> sl.ffi.cdata:
		"""
			Return a (double) ffi array holding the given floats
		"""
		num = len(values)
		ret = sl.ffi.new('double[]', num)
		for ii in range(num):
			ret[ii] = values[ii]
		return ret


	@classmethod
	def makeIntArray(cls, num: int) -> sl.ffi.cdata:
		"""
			Return a ffi array holding space for num ints
		"""
		return sl.ffi.new('int[]', num)


	@classmethod
	def makeIntArrayWithValues(cls, values: list[int]) -> sl.ffi.cdata:
		"""
			Return a ffi array holding the given ints
		"""
		num = len(values)
		ret = sl.ffi.new('int[]', num)
		for ii in range(num):
			ret[ii] = values[ii]
		return ret



	def getOpenString(self, struct: sl.ffi.cdata, instVar: str) -> str:
		"""
			Preliminary: return 'open' for instVar == 1, else 0 (periodic not handled)
		"""
		val = getattr(struct, instVar)
		return ['closed', 'open'][val]


	@classmethod
	def getOpenValue(cls, value: bool) -> int:
		"""
			Preliminary: return 1 for open == True, else 0 (periodic not handled)
		"""
		return 1 if value else 0


	@classmethod
	def getInterValuesPython(cls, minV: float, maxV:float, numSteps: int) -> list[float]:
		"""
			return a python list with values lying evenly spaced between (and including) minV and maxV
		"""
		ret = []
		diff = (maxV - minV) / (numSteps - 1.0)
		for ii in range(numSteps - 1):
			newV = minV + ii * diff
			ret.append(newV)
		ret.append(maxV)
		return ret


	@classmethod
	def getInterValues(cls, minV, maxV, numSteps) -> sl.ffi.cdata:
		"""
			return a cdata array with numSteps doubles lying evenly spaced between (and including) minV and maxV
		"""
		vals = cls.getInterValuesPython(minV, maxV, numSteps)
		return cls.makeDoubleArrayWithValues(vals)
		


	@classmethod
	def statItem(cls) -> sl.ffi.cdata:
		"""
			Return a pointer to an int, usable for status return value
		"""
		return sl.ffi.new('int[]', 1)


	@classmethod
	def getPointsFromArray(cls, arr: sl.ffi.cdata, num: int) -> list[Point]:
		"""
			Return list of num points read from the ffi double array
		"""
		ret = []
		ii = 0
		while ii < num * 3:
			ret.append(Point(arr[ii], arr[ii+1], arr[ii+2]))
			ii += 3
		return ret


	@classmethod
	def getDoublesFromArray(cls, arr: sl.ffi.cdata, num: int) -> list[float]:
		"""
			Return list of num floats read from the ffi double array
		"""
		ret = []
		ii = 0
		while ii < num:
			ret.append(arr[ii])
			ii += 1
		return ret


	@classmethod
	def checkStat(cls, stat: sl.ffi.cata, msg: str) -> None:
		"""
			If the return status indicates an error, show the message
		"""
		ret = stat[0]
		if ret == 0:
			return
		print(f'Error in {msg} [{ret}] ############################')


###################################################################
###################################################################


class SislCurveHolder(SislObjectHolder):
	def __init__(self, structPtr):
		super().__init__(structPtr)
		self.m_startPar = -1
		self.m_endPar = -1
		if self.m_structPtr	!= sl.ffi.NULL:
			self.getParameterRange()
		else:
			raise Exception('SislCurveHolder: got invalid curve pointer')


	@classmethod
	def createCurveFromStraightLine(cls, start: Point, stop: Point, order: int=4) -> SislCurveHolder:
		"""
			Return a SislCurveHolder described by start and stop. Use given order
		"""
		if order < 2:
			order = 2
		p1 = cls.makePointArray(start)
		p2 = cls.makePointArray(stop)
		startPar = 0.0
		endParPtr = sl.ffi.new('double[]', 1)
		theStruct = sl.ffi.new('SISLCurve*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = cls.statItem()
		
		sl.lib.s1602(p1, p2, order, cls.s_spaceDimension, startPar, endParPtr, theStruct, stat)
		cls.checkStat(stat, 'createCurveFromStraightLine')

		return SislCurveHolder(theStruct[0])


	@classmethod
	def createCurveConstant(cls, value: Point) -> SislCurveHolder:
		"""
			Return a SislCurveHolder with one constant value (needed e.g. as an edge derivative of a surface)
		"""
		# implementation might be a bit overcomplicated, but i do not know a better way

		if value.isSameAs(Point()):
			raise Exception('constant value of curve must not be (0, 0, 0)')

		curve1 = cls.createCurveFromStraightLine(Point(), Point(0, 1))
		curve2 = cls.createCurveFromStraightLine(Point(1), Point(1, 1))
		surf = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([curve1, curve2])
		ret = surf.getDerivationAtEdge(True, False)

		matrix = Matrix.makeOrthonormalTransformation(value) * Matrix(value.length())
		aff = Affine(matrix)
		return ret.transformedBy(aff)


	@classmethod
	def createCurveFromControlPoints(cls, points: list[Point], order: int=4, isOpen: bool=True) -> SislCurveHolder:
		"""
			Return a SislCurveHolder described by the control points
		"""
		#print('len = ' + str(len(points)))
		if len(points) == 2:
			return cls.createCurveFromStraightLine(points[0], points[1])
		coords = cls.makePointArray(points)
		startPar = 0.0
		openFlag = 1 if isOpen else 0
		theStruct = sl.ffi.new('SISLCurve*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = cls.statItem()
		sl.lib.s1630(coords, len(points), startPar, openFlag, cls.s_spaceDimension, order, theStruct, stat)
		cls.checkStat(stat, 'createCurveFromControlPoints')
		structPtr = theStruct[0]
		return SislCurveHolder(structPtr)


	@classmethod
	def createCurveFromBezier3Segement(cls, bez3Segment, order: int=4, isOpen: bool=True) -> SislCurveHolder:
		"""
			Return a SislCurveHolder described by bez3Segment
		"""
		points = bez3Segment.asNurbsDescription()
		return cls.createCurveFromControlPoints(points, order, isOpen)


	@classmethod
	def createCurveFromPath(cls, path, order: int=4, isOpen: bool=True) -> SislCurveHolder:
		"""
			Return a SislCurveHolder described by the given path
			(currently only possible for Bezier3 segments)
		"""
		allControlPoints = path.asNurbsDescription()
		curves = []
		for segDescription in allControlPoints:
			curves.append(cls.createCurveFromControlPoints(segDescription, order, isOpen))
		return cls.joinAllCurves(curves)


	@classmethod
	def createNewCurve(cls, verts: list[Point], order: int, knots: list[float]) -> SislCurveHolder:
		"""
			Return a SISLCurveHolder for a curve described by the vertices and knot vector
		"""
		vertsArray = cls.makePointArray(verts)
		knotsArray = cls.makeDoubleArray(knots)
		structPtr = sl.lib.newCurve(len(verts), order, knotsArray, vertsArray, 1, 3, 1)
		return SislCurveHolder(structPtr)


	@classmethod
	def joinAllCurves(cls, curvesIn: list[SislCurveHolder]) -> SislCurveHolder:
		"""
			Return a new SislCurveHolder that holds the joined curve of all curves in curvesIn in the given order
		"""
		runner = curvesIn[0]
		for ii in range(1, len(curvesIn)):
			curve2 = curvesIn[ii]
			longer = runner.joinedWith(curve2)		# play it safe for GC of (old) ret
			runner = longer
		return runner


	def joinedWith(self, curve2: SislCurveHolder) -> SislCurveHolder:
		"""
			Return a new SislCurveHolder that holds the joined curve of curve2 after myself
		"""
		theStruct = sl.ffi.new('SISLCurve*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = self.statItem()
		sl.lib.s1715(self.m_structPtr, curve2.m_structPtr, 1, 0, theStruct, stat)
		self.checkStat(stat, 'joinTwoCurves')
		structPtr = theStruct[0]
		return SislCurveHolder(structPtr)
	
	#	sislCurve.createOffsetCurve(10.0, 2.0, Point(0, 0, 1))
	def createOffsetCurve(self, offset, epsge, normal, maxD=0.0, dim=3):
		'''
			create a curve that is parallel to me
		'''
		theStruct = sl.ffi.new('SISLCurve*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = self.statItem()
		sl.lib.s1360(self.m_structPtr, offset,  epsge,  self.makePointArray(normal), maxD, dim, theStruct, stat)
		self.checkStat(stat, 'createOffsetCurve')
		structPtr = theStruct[0]
		return SislCurveHolder(structPtr)


#############


	def dump(self, name='') -> None:
		"""
			Dump the contents of the SISLCurve struct in a readable form
		"""
		print (f'Curve: ----------  {name} ---------------')
		#print(f'self.m_structPtr: {self.m_structPtr}')
		if self.m_structPtr	== sl.ffi.NULL:	# is a NULL pointer
			print(f'curve is empty: {name} ###################')
			return
		#print('self.m_structPtr: {self.m_structPtr}')

		curve = self.m_structPtr[0]

		#print(f'*{curve}*')
		curveKinds = ['Unknown', 'Polynomial B-spline curve', 'Rational B-spline curve', 'Polynomial Bezier curve', 'Rational Bezier curve']
		curveKind = curveKinds[curve.ikind]
		print(f'orderOfCurve:	{curve.ik}')
		print('numOfVertices:	' + str(getattr(curve, 'in')))
		print(f'kindOfCurve:	{curveKind}')
		print('open/closed:	' + self.getOpenString(curve, 'cuopen'))
		print(f'startPar:	{self.m_startPar}')
		print(f'endPar:		{self.m_endPar}')


	def free(self) -> None:
		"""
			Release my resources. Is automatically called at GC time
		"""
		if self.m_structPtr is not None:
			sl.lib.freeCurve(self.m_structPtr)
			self.m_structPtr = None


	def getRegularCurvePoints(self, numPoints: int) -> list[Point]:
		"""
			Return an array of curve points at regular parameter values.
		"""
		allVs = self.getInterValuesPython(self.m_startPar, self.m_endPar, numPoints)
		return self.getCurvePointsAt(allVs)


	def getCurvePointsAt(self, paramsPython: list[float]) -> list[Point]:
		"""
			Return an array of curve points at the given (python) parameter values.
		"""
		allVs = self.makeDoubleArrayWithValues(paramsPython)
		numPoints = len(paramsPython)

		arrPointer = self.makeDoubleArray(3 * numPoints)
		stat = self.statItem()
		sl.lib.s1542(self.m_structPtr, numPoints, allVs, arrPointer, stat)
		self.checkStat(stat, 'getCurvePointsAt')

		return self.getPointsFromArray(arrPointer, numPoints)


	def dumpCurvePoints(self, numPoints: int) -> None:
		"""
			Print my curve points for a regular grid of parameters (with numPoints members)
		"""
		points = self.getRegularCurvePoints(numPoints)
		ii = 0
		for point in points:
			point.printComment('p' + str(ii))
			ii += 1


	def dumpNurbs(self) -> None:
		"""
			Print my vertices and knot vector
		"""
		verts, knots, _ = self.getNurbsData()
		print('vertices:')
		for p in verts:
			p.printComment('	')
		print('knots')
		for k in knots:
			print('	' + str(k))


	def getParameterRange(self) -> None:
		"""
			Get my start and stop parameters values and store internally
		"""
		startParPtr = sl.ffi.new('double[]', 1)
		endParPtr = sl.ffi.new('double[]', 1)
		stat = self.statItem()
		sl.lib.s1363(self.m_structPtr, startParPtr, endParPtr, stat)
		self.checkStat(stat, 'Curve:getParameterRange')

		self.m_startPar = startParPtr[0]
		self.m_endPar = endParPtr[0]


	def transformedBy(self, aff) -> SislCurveHolder:
		"""
			Return a new SislCurveHolder which is myself transformed by affine transformation aff
		"""
		verts, knots, order = self.getNurbsData()
		vertsTransformed = [aff * x for x in verts]
		return self.createNewCurve(vertsTransformed, order, knots)


	def getNurbsData(self) -> list:
		"""
			Return an array containing my vertices, my knot vector and my order
		"""
		struct = self.m_structPtr[0]
		numVertices = getattr(struct, 'in')
		verts = self.getPointsFromArray(struct.ecoef, numVertices)
		order = struct.ik
		numKnots = order + numVertices
		knots = self.getDoublesFromArray(struct.et, numKnots)
		return [verts, knots, order]


	def reversed(self) -> SislCurveHolder:
		"""
			Return a new curve that looks like me but goes in the opposite direction
		"""
		newCurve = self.copy()
		sl.lib.s1706(newCurve.m_structPtr)
		newCurve.getParameterRange()		# to play it safe
		return newCurve


	def copy(self) -> SislCurveHolder:
		"""
			Return a copy of myself
		"""
		newPtr = sl.lib.copyCurve(self.m_structPtr)
		theClass = self.__class__
		return theClass(newPtr)


	def getIntersectionPointsWithPlane(self, plane) -> list[list[Point|float]]:
		"""
			Return the intersection  with the given plane.
			Complicated situations are not regarded (like intersection curves)
			Return [listOfPoints, listOfParameters]
		"""
		planePoint = self.makePointArray([plane.m_p1])
		planeNormal = self.makePointArray([plane.m_normal])
		epsco = 1e-9	# not used
		epsge = 1e-6	# tolerance used
		numPointsPtr = sl.ffi.new('int[]', 1)
		numPointsPtr[0] = 0
		pointParamsPtr = sl.ffi.new('double*[]', 1)
		pointParamsPtr[0] = sl.ffi.NULL

		numIntCurves = sl.ffi.new('int[]', 1)
		numIntCurves[0] = 0
		intCurves = sl.ffi.new('SISLIntcurve**[]', 1)
		intCurves[0] = sl.ffi.NULL

		stat = self.statItem()

		sl.lib.s1850(self.m_structPtr, planePoint, planeNormal, 3, epsco, epsge, numPointsPtr, pointParamsPtr, numIntCurves, intCurves, stat)
		self.checkStat(stat, 'getIntersectionPointWithPlane')

		if numIntCurves[0] > 0:
			print('getIntersectionPointWithPlane: unexpected Intcurves found - ignored')
			sl.lib.freeIntcrvlist(intCurves[0], intCurves[0])

		numPoints = numPointsPtr[0]
		if numPoints == 0:
			return [[], []]

		# ok we have at least one point
		pointParamsC = pointParamsPtr[0]
		pointParamsPython = self.getDoublesFromArray(pointParamsC, numPoints)
		pointList = self.getCurvePointsAt(pointParamsPython)
		sl.lib.free(pointParamsPtr[0])
		return [pointList, pointParamsPython]


	def subDivideAtParameter(self, param: float) -> list[SislCurveHolder]:
		"""
			Return a list of 2 partial curves which add to me at the given parameter 
		"""
		curveC1 = sl.ffi.new('SISLCurve*[]', 1)
		curveC1[0] = sl.ffi.NULL
		curveC2 = sl.ffi.new('SISLCurve*[]', 1)
		curveC2[0] = sl.ffi.NULL
		stat = self.statItem()
		sl.lib.s1710(self.m_structPtr, param, curveC1, curveC2, stat)
		self.checkStat(stat, 'subDivideAtParameter')

		curve1 = SislCurveHolder(curveC1[0])
		curve2 = SislCurveHolder(curveC2[0])

		return [curve1, curve2]


#######################################################################
#######################################################################


class SislSurfaceHolder(SislObjectHolder):
	"""
		Encapsulate a Sisl surface
	"""
	def __init__(self, structPtr):
		super().__init__(structPtr)
		self.m_startPar1 = -1
		self.m_endPar1 = -1
		self.m_startPar2 = -1
		self.m_endPar2 = -1
		#self.m_surfacePoints = dict()
		#self.m_normalVectors = dict()
		self.getParameterRanges()


	@classmethod
	def createNewSurface(cls, numU: int, numV: int, verts: list[Point], orderU: int, orderV: int, knotsU: list[float], knotsV: list[float]) -> SislSurfaceHolder:
		"""
			Return a SislSurfaceHolder for the given parameters
		"""
		vertsArray = cls.makePointArray(verts)
		knotsArrayU = cls.makeDoubleArray(knotsU)
		knotsArrayV = cls.makeDoubleArray(knotsV)

		structPtr = sl.lib.newSurf(numU, numV, orderU, orderV, knotsArrayU, knotsArrayV, vertsArray, 1, 3, 1)
		return SislSurfaceHolder(structPtr)


	@classmethod
	def createSurfsFromCurves(cls, curves: list[SislCurveHolder], derivs: list[SislCurveHolder]) -> list[SislSurfaceHolder]:
		"""
			Return a list of first derivative continuous blending surfaces, 
			over a 3-, 4-, 5- or 6-sided region in space,
			from a set of B-spline input curves and their derivatives curves
		"""
		num = len(curves)
		if len(derivs) != num:
			raise Exception('creatSurfsFromCurves: curves and derivs must have same length')
		curvesIn = sl.ffi.new('SISLCurve*[]', num * 2)
		allNumVals = [2] * num
		for ii in range(num):
			curvesIn[2*ii] = curves[ii].m_structPtr
			deriv = derivs[ii]
			curvesIn[2*ii+1] = deriv.m_structPtr
		surfsOut = sl.ffi.new('SISLSurf**[]', 1)
		surfsOut[0] = sl.ffi.NULL
		allNums = cls.makeIntArrayWithValues(allNumVals)
		stat = cls.statItem()
		sl.lib.s1391(curvesIn, surfsOut, num, allNums, stat)
		cls.checkStat(stat, 'createSurfsFromCurves')

		ret = []
		ptrPtr = surfsOut[0]
		for jj in range(num):
			ret.append(SislSurfaceHolder(ptrPtr[jj]))
		return ret

		

	def free(self) -> None:
		"""
			Release my resources. Is automatically called at GC time
		"""
		if self.m_structPtr is not None:
			sl.lib.freeSurf(self.m_structPtr)
			self.m_structPtr = None


	def getParameterRanges(self) -> None:
		"""
			Get the start and stop values for my U and V parameters. Store in myself.
		"""
		startParPtr1 = sl.ffi.new('double[]', 1)
		endParPtr1 = sl.ffi.new('double[]', 1)
		startParPtr2 = sl.ffi.new('double[]', 1)
		endParPtr2 = sl.ffi.new('double[]', 1)
		stat = self.statItem()
		sl.lib.s1603(self.m_structPtr,startParPtr1,startParPtr2,endParPtr1,endParPtr2, stat)
		self.checkStat(stat, 'Surface:getParameterRanges')

		self.m_startPar1 = startParPtr1[0]
		self.m_endPar1 = endParPtr1[0]
		self.m_startPar2 = startParPtr2[0]
		self.m_endPar2 = endParPtr2[0]


	def dump(self, name='') -> None:
		"""
			Print the contents of the SISLSurf struct in a readable form
		"""
		surface = self.m_structPtr[0]
		surfaceKinds = ['Unknown', 'Polynomial B-spline tensor-product', 'Rational B-spline tensor-product', 'Polynomial Bezier tensor-product', 'Rational Bezier tensor-product']
		surfaceKind = surfaceKinds[surface.ikind]
		print (f'Surface: ---------{name}------------------')
		print(f'orderOfSurf.1:	{surface.ik1}')
		print(f'orderOfSurf.2:	{surface.ik2}')
		print(f'numOfVertices1:	{surface.in1}')
		print(f'numOfVertices2:	{surface.in2}')
		print(f'kindOfSurface:	{surfaceKind}')
		print('open/closed1:	' + self.getOpenString(surface, 'cuopen_1'))
		print('open/closed2:	' + self.getOpenString(surface, 'cuopen_2'))
		print(f'startPar1:	{self.m_startPar1}')
		print(f'endPar1:	{self.m_endPar1}')
		print(f'startPar2:	{self.m_startPar2}')
		print(f'endPar2:	{self.m_endPar2}')


	def getSurfacePoints(self, numU, numV=math.nan) -> list[list[Point]]:
		"""
			Return surfacePoints for a regular parameter grid
			Return list of numU lists with all v-points for the respective u value.
		"""
		#if numU is None:
		#	# just return the last created points
		#	keys = list(self.m_surfacePoints.keys())
		#	if len(keys) != 1:
		#		raise Exception('do not know, which points to return')
		#	return self.m_surfacePoints[keys[0]]
		if math.isnan(numV):
			numV = numU
		#key = str(numU) + 'x' + str(numV)
		#if self.m_surfacePoints.get(key, None) is None:
		return self.readRegularSurfacePoints(numU, numV)[0]
		#return self.m_surfacePoints[key]


	def getNormalVectors(self, numU: int=None, numV: int=math.nan) -> list:
		"""
			Return surface normals for a regular parameter grid
			Return list of numV lists with all u-points for the respective v value.
		"""
		#if numU is None:
		#	# just return the last created points
		#	keys = list(self.m_normalVectors.keys())
		#	if len(keys) != 1:
		#		raise Exception('do not know, which normals to return')
		#	return self.m_normalVectors[keys[0]]
		if math.isnan(numV):
			numV = numU
		#key = str(numU) + 'x' + str(numV)
		#if self.m_surfacePoints.get(key, None) is None:
		return self.readRegularSurfacePoints(numU, numV)[1]
		#return self.m_normalVectors[key]


	def readRegularSurfacePoints(self, numU: int, numV: int) -> None:
		"""
			Read the points from sisl for a regular parameter grid
		"""
		#key = str(numU) + 'x' + str(numV)
		derivs = 1
		sizeOfOnePoint = int(3 * (derivs + 1)*(derivs + 2)/2)
		sizeOfPointsArray = int(sizeOfOnePoint * numU * numV)
		pointsAndDerivsPointer = self.makeDoubleArray(sizeOfPointsArray)
		normalsPointer = self.makeDoubleArray(3 * numU * numV)

		uVals = self.getInterValues(self.m_startPar1, self.m_endPar1, numU)
		vVals = self.getInterValues(self.m_startPar2, self.m_endPar2, numV)

		stat = self.statItem()

		sl.lib.s1506(self.m_structPtr, derivs, numU, uVals, numV, vVals, pointsAndDerivsPointer, normalsPointer, stat)
		self.checkStat(stat, 'Surface:readRegularSurfacePoints')

		# in the array pointsAndDerivsPointer we have a mix of surface point coordinates and partial derivatives
		# we extract the point coordinates first
		allPointsCoordinates = []
		for ii in range(numU * numV):
			start = ii * sizeOfOnePoint
			theSlice = slice(start, start + 3)
			allPointsCoordinates.extend(pointsAndDerivsPointer[theSlice])

		allPoints = self.getPointsFromArray(allPointsCoordinates, numU * numV)
		allNormals = self.getPointsFromArray(normalsPointer, numU * numV)

		# now we rearrange the points and normals in sublists
		pointsLists = []
		normalsLists = []
		for ii in range(numU):
			pointList = []
			pointsLists.append(pointList)
			normalsList = []
			normalsLists.append(normalsList)
			for jj in range(numV):
				idx = jj * numU + ii
				pointList.append(allPoints[idx])
				normalsList.append(allNormals[idx])

		# store the lists
		#self.m_surfacePoints[key] = [pointsLists, [numU, numV]]
		#self.m_normalVectors[key] = [normalsLists, [numU, numV]]
		surfacePoints = [pointsLists, [numU, numV]]
		normalVectors = [normalsLists, [numU, numV]]
		return [surfacePoints, normalVectors]
		#self.dumpPoints(numU, numV, pointsLists)


	def dumpPoints(self, numU: int, numV: int, pointsLists: list[Point]):
		"""
			Print all the points from pointsList in senseful order
		"""
		print('-----------------------')
		for ii in range(numU):
			listU = pointsLists[ii]
			for jj in range(numV):
				point = listU[jj]
				point.printComment('[' + str(ii) + ', ' + str(jj) + ']')


	def dumpNurbs(self) -> None:
		"""
			Print my nurbs vertices and knots
		"""
		numU, numV, verts, knotsU, knotsV, _, __ = self.getNurbsData()
		print('knots U: -----------------')
		for knot in knotsU:
			print('	' + str(knot))
		print('knots V: -----------------')
		for knot in knotsV:
			print('	' + str(knot))
		idx = 0
		for ii in range(numU):
			print('Vertices ' + str(ii))
			for _ in range(numV):
				p = verts[idx]
				p.printComment('	p')
				idx += 1


	def allFaces(self, quality: int) -> list[list[Point]]:
		"""
			Create all the OSCAD faces for the surface
		"""
		allPoints, sizes = self.getSurfacePoints(quality+1)
		numU, numV = sizes

		# now make the faces:
		ret = []
		pList1 = allPoints[0]
		for ii in range(1, numU):
			#print('numU=' + str(numU))
			# iterate over u
			pList2 = allPoints[ii]
			for jj in range(numV - 1):
				# iterate over v:
				p11 = pList1[jj]
				p12 = pList1[jj+1]
				p21 = pList2[jj+1]
				p22 = pList2[jj]
				ret.append([p11, p12, p21, p22])

			pList1 = pList2

		return ret


	def getEdgePolygons(self, quality) -> list[list[Point]]:
		"""
			Return a list of 2 point lists. These are the points at my start curve and my end curve
		"""
		allPoints, sizes = self.getSurfacePoints(quality+1)
		numU = sizes[0]
		start = []
		stop = []
		for ii in range(numU):
			start.append(allPoints[ii][0])
			stop.append(allPoints[ii][-1])
		return[start, stop]


	def getSidePolygons(self, quality) -> list[list[Point]]:
		"""
			Return a list of 2 point lists. These are the points at my first side curve and my last side curve
		"""
		allPoints, _ = self.getSurfacePoints(quality+1)
		start = allPoints[0]
		stop = allPoints[-1]
		return[start, stop]




	def findClosestPointSimple(self, point: Point, resolution: float=1e-6) -> Point:
		"""
			Return the point on the surface that is closest to point (use simple SISL algorithm)
		"""
		params = self.findClosestParamsSimple(point, resolution)
		ret = self.getOneSurfacePoint(params[0], params[1])
		return ret


	def findClosestParamsSimple(self, point: Point, resolution: float=1e-6) -> list[float]:
		"""
			Return the parameters of the closest point on surface to point (use simple SISL algorithm)
		"""
		inPnt = self.makePointArray(point)
		params = self.makeDoubleArray(2)
		dist = self.makeDoubleArray(1)
		stat = self.statItem()

		sl.lib.s1958(self.m_structPtr, inPnt, self.s_spaceDimension, resolution, resolution, params, dist, stat)
		self.checkStat(stat, 'Surface:findClosestPointSimple')

		u = params[0]
		v = params[1]

		return [u, v]


	def getOneSurfacePoint(self, u: float, v: float) -> Point:
		"""
			Return only the surface point for the given parameters. No derivation and no normal
		"""
		params = self.makeDoubleArrayWithValues([u, v])
		leftKnot1 = self.makeIntArrayWithValues([0])
		leftKnot2 = self.makeIntArrayWithValues([0])
		pointAndDerivs = self.makePointArray(Point())		# no derivs used!
		normal = self.makePointArray(Point())
		stat = self.statItem()

		sl.lib.s1421(self.m_structPtr, 0, params, leftKnot1, leftKnot2, pointAndDerivs, normal, stat)
		self.checkStat(stat, 'Surface:getOneSurfacePoint')

		ret = self.getPointsFromArray(pointAndDerivs, 1)[0]
		return ret


	def transformedBy(self, aff: Affine) -> SislSurfaceHolder:
		"""
			Return a new SislSurfaceHolder that represents me transformed my vertices by affine transformation aff
		"""
		struct = self.m_structPtr[0]
		numVerticesU = struct.in1
		numVerticesV = struct.in2
		orderU = struct.ik1
		orderV = struct.ik2

		numKnotsU = orderU + numVerticesU
		numKnotsV = orderV + numVerticesV

		knotsU = self.getDoublesFromArray(struct.et1, numKnotsU)
		knotsV = self.getDoublesFromArray(struct.et2, numKnotsV)

		numVertices = numVerticesU * numVerticesV
		verts = self.getPointsFromArray(struct.ecoef, numVertices)

		vertsTransformed = [aff * x for x in verts]
		return self.createNewSurface(numVerticesU, numVerticesV, vertsTransformed, orderU, orderV, knotsU, knotsV)


	def getDerivationAsSurface(self, der1: int, der2: int) -> SislSurfaceHolder:
		"""
			Return a surface that represents the der1, der2 partial derivate of me
		"""
		theStruct = sl.ffi.new('SISLSurf*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = self.statItem()

		sl.lib.s1386(self.m_structPtr, der1, der2, theStruct, stat)
		self.checkStat(stat, 'getDerivationAsSurface')

		return SislSurfaceHolder(theStruct[0])


	def pickACurveAtParameter(self, param: float, direction: int) -> SislCurveHolder:
		"""
			Return a curve for a fixed param in direction (1 is U, 2 is V)
		"""
		theStruct = sl.ffi.new('SISLCurve*[]', 1)
		theStruct[0] = sl.ffi.NULL
		stat = self.statItem()
		sl.lib.s1439(self.m_structPtr, param, direction, theStruct, stat)
		self.checkStat(stat, 'pickACurveAtParameter')
		return SislCurveHolder(theStruct[0])


	def getNurbsData(self) -> list:
		"""
			Return an array describing my vertices, knots and orders
		"""
		surface = self.m_structPtr[0]

		orderU = surface.ik1
		orderV = surface.ik2
		numU = surface.in1
		numV = surface.in2

		verts = self.getPointsFromArray(surface.ecoef, numU * numV)
		knotsU = self.getDoublesFromArray(surface.et1, orderU + numU)
		knotsV = self.getDoublesFromArray(surface.et2, orderV + numV)

		return [numU, numV, verts, knotsU, knotsV, orderU, orderV]




################################################################
################################################################


class SislLoftedSurfaceHolder(SislSurfaceHolder):
	"""
		Holds a surface that is generated by lofting
	"""
	def __init__(self, structPtr, curves, curveTypes, paramsOfCurves):
		super().__init__(structPtr)
		self.m_curves = curves
		self.m_curveTypes = curveTypes
		self.m_paramsOfCurves = paramsOfCurves
		self.m_bePseudoExtrusion = False


	class LoftedSurfaceCurveType(IntEnum):
		"""
			See description of s1538
		"""
		ORDINARY = 1
		KNUCKLE = 2
		TANGENTTONEXT = 3
		TANGENTTOPRIOR = 4
		STARTOFTANGENTTONEXT = 13		# ???? perhaps for a kink?
		ENDOFTANGENTTOPRIOR = 14		# ???? perhaps for a kink?


	@classmethod
	def createLoftedSurfaceFromBSplines(cls, curves: list[SislCurveHolder], curveTypes: list[LoftedSurfaceCurveType]=None, 
		startPar: float=0.0, openFlag: bool=True, maxOrder: int=4, adjustTangentSize: bool=False) -> SislLoftedSurfaceHolder:
		"""
			Return a SislSurfaceHolder which lofts the given curves. For curveTypes see s1538
		"""
		num = len(curves)
		if curveTypes is None:
			curveTypes = [SislLoftedSurfaceHolder.LoftedSurfaceCurveType.ORDINARY] * num
		if num != len(curveTypes):
			raise Exception('createLoftedSurfaceFromBSplines: wrong length of curveTypes')

		curveInput = sl.ffi.new('SISLCurve*[]', num)
		for ii in range(num):
			curveInput[ii] = curves[ii].m_structPtr

		curveTypeArray = cls.makeIntArrayWithValues(curveTypes)

		iOpen = cls.getOpenValue(openFlag)
		iFlag = 1 if adjustTangentSize else 0
		theStruct = sl.ffi.new('SISLSurf*[]', 1)
		theStruct[0] = sl.ffi.NULL
		paramsOfCurves = sl.ffi.new('double *[]', 1)
		paramsOfCurves[0] = sl.ffi.NULL		# will be overwritten by s1538
		stat = cls.statItem()

		sl.lib.s1538(num, curveInput, curveTypeArray, startPar, iOpen, maxOrder, iFlag, theStruct, paramsOfCurves, stat)
		cls.checkStat(stat, 'createLoftedSurfaceFromBSplines')
		structPtr = theStruct[0]
		paramsPtr = paramsOfCurves[0]
		paramsPython = cls.getDoublesFromArray(paramsPtr, num)
		sl.lib.free(paramsPtr)		# hopefully right

		return SislLoftedSurfaceHolder(structPtr, curves, curveTypes, paramsPython)


	def dump(self, name='') -> None:
		"""
			Print the contents of the SISLLoftedSurf struct in a readable form
		"""
		super().dump(name)
		ii = 0
		for param in self.m_paramsOfCurves:
			print('c-param ' + str(ii) +':	' + str(param))
			ii += 1


	def getDerivationAtEdge(self, startFlag: bool, inverted: bool=False) -> SislCurveHolder:
		"""
			Return a curve describing my partial derivation at start (startFlag=True) or at end
		"""
		derivationSurf = self.getDerivationAsSurface(0,1)
		if startFlag:
			param = self.m_paramsOfCurves[0]
		else:
			param = self.m_paramsOfCurves[-1]
		coordinateDirection = 2
		deriveCurve = derivationSurf.pickACurveAtParameter(param, coordinateDirection)
		if inverted:
			affMirror = Affine.makePointMirror()
			return deriveCurve.transformedBy(affMirror)
		return deriveCurve


	def getSurfacePoints(self, numU: int, numV: int=math.nan) -> list[list[Point]]:
		"""
			Return surfacePoints for a regular parameter grid
			Return list of numV lists with all u-points for the respective v value.
			For a PseudoExtrusion make only a 2-grid in the V direction
		"""
		if numV is math.nan and self.m_bePseudoExtrusion:
			numV = 2
		return super().getSurfacePoints(numU, numV)
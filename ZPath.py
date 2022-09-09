"""
	Contains 
	- ZPath, a 2d or 3d path (composed from svg-like segments)
	- ZPathSegment
	- ZLineSegment
	- ZBezier2Segment
	- ZBezier3Segment
	- ZArcSegment
"""


from __future__ import annotations
#from abc import abstractclassmethod
import math
#from scipy.optimize import newton
import xml.etree.ElementTree as ET

from zutils.ZGeom import Point, Polygon, Line, Circle2, Ellipse2, ZGeomItem, Plane
from zutils.ZMatrix import Matrix, Affine
#from zutils.shame import searchForEllipseCenter


#########################################################
#########################################################


class ZPathSegment:
	"""
		Abstract superclass of segments, handles general tasks
	"""
	def __init__(self, start, stop):
		start.checkIsLegal()
		stop.checkIsLegal()

		self.m_start = start
		self.m_stop = stop


	def reverse(self):
		"""
			Change myself, so i am reversed
		"""
		p1 = self.m_start
		p2 = self.m_stop
		self.m_start = p2
		self.m_stop = p1


	def reversed(self):
		"""
			Return a yopy of me that is reversed
		"""
		ret = self.copy()
		ret.reverse()
		return ret


	def makeFlat(self):
		self.m_start.m_z = 0
		self.m_stop.m_z = 0


	def getParameterRange(self):
		"""
			Return an array of 2 values for my parameter range.
			Overridden in subclass ZArcSegment
		"""
		return [0, 1]


	#def copy(self):
	#	raise Exception('not implemented copy() in class: ' + self.__class__.__name__)


	#def transformBy(self, affine):
	#	"""
	#		Transform myself. Return nothing
	#	"""
	#	raise Exception('not implemented transformBy() in class: ' + self.__class__.__name__)


	def transformedBy(self, affine):
		"""
			Return a copy of myself, that describe me transformed
		"""
		val = self.copy()
		val.transformBy(affine)
		return val


	#@classmethod
	def getInterPoints(self, _) -> list:
		raise Exception('not implemented getInterPoints() in class: ' + self.__class__.__name__)


	#@classmethod
	def getInterPointsWithTangent(self, _) -> list:
		raise Exception('not implemented getInterPointsWithTangent() in class: ' + self.__class__.__name__)


	def findMinimalPoint(self, func):
		"""
			Find a point p on me, so that func(p) has a minimal value.
			func must return a number.
			Returns a list: [segment, point, segParameter, value]
		"""
		#raise Exception('not implemented getInterPointsWithTangent() in class: ' + self.__class__.__name__)
		(tStart, tStop) = self.getParameterRange()
		diff = (tStop - tStart) / 100.0
		t = tStart
		fMin = 1000000000
		tMin = math.nan
		#pMin = Point()
		while t < tStop:
			test = self.getInterPointAtParameter(t)
			fTest = func(test)
			if fTest < fMin:
				fMin = fTest
				#pMin = test
				tMin = t
			t += diff
		# also test my stop point:
		fTest = func(self.m_stop)
		if fTest < fMin:
			fMin = fTest
			#pMin = self.m_stop
			tMin = 1
		# finally use interval nesting:
		low = max(0, tMin - diff)
		upp = min(tMin + diff, 1)
		diff = upp - low
		#print('start')
		while diff > 0.0000000001:
			pLow = self.getInterPointAtParameter(low)
			pUpp = self.getInterPointAtParameter(upp)
			fLow = func(pLow)
			fUpp = func(pUpp)
			diff = diff / 2.0
			if fLow < fUpp:
				upp = low + diff
			else:
				low = upp - diff

		return [self, pLow, low, fLow]


	def findNearestPoint(self, point):
		"""
			Reteurn an arrray of points, that are nearest to point
		"""
		myLambda = lambda p: p.distanceOfPoint(point)
		testArr = self.findMinimalPoint(myLambda)
		return testArr


	#def findZeroParameter(self, func):
	#	"""
	#		Find a point p on me, so that func(p) = 0
	#		func must return a number.
	#		Returns a list: [segment, point, segParameter]
	#	"""
	#	func2 = lambda t: abs(func(t))
	#	[_, point, segParameter, value] = self.findMinimalPoint(func2)
	#	print(value)
	#	#newtonParam = newton(func, segParameter)
	#	#return [self, self.getInterPointAtParameter(newtonParam), newtonParam]


	def containsPoint(self, point):
		testArr = self.findNearestPoint(point)
		myPoint = testArr[1]
		return myPoint.isSameAs(point)


	def printTabs(self, tabs):
		for _ in range(tabs):
			print('	', end='')


	def rounded(self, rounded=2):
		ret = self.copy()
		ret.round(rounded)
		return ret


	def round(self, rounded=2):
		self.m_start = self.m_start.rounded(rounded)
		self.m_stop = self.m_stop.rounded(rounded)


	def printComment(self, comment, tabs=1, rounded=2):
		self.printTabs(tabs)
		print(comment + ': ')
		self.printTabs(tabs)
		print(self.__class__.__name__)
		self.m_start.printComment('start', tabs + 1, rounded)
		self.m_stop.printComment('stop', tabs + 1, rounded)


	def xmlAddTo(self, parent):
		node = ET.SubElement(parent, self.__class__.__name__)
		node.set('start', self.m_start.xmlCoords())
		node.set('stop', self.m_stop.xmlCoords())
		self.xmlAddDetailsTo(node)


	def cncFriendlySimple(self):
		"""
			Return an array of Line segments that approximate myself
		"""
		numPoints = 100
		ps = self.getInterPointsWithTangent(1 / numPoints)
		ret = []
		lastPoint = None

		for arr in ps:			#numPoints-1):
			p1 = arr[0]
			if lastPoint is not None:
				line = ZLineSegment(lastPoint, p1)
				ret.append(line)
			lastPoint = p1

		return ret


	def cncFriendly(self, tolerance):
		"""
			Return an array of Line-or-Arc segments that approximate myself
		"""
		if tolerance == 0:
			raise Exception('cncFriendly(): tolerance 0 is not possible')
		numPoints = 1000
		ps = self.getInterPointsAndStop(1 / numPoints)
		ret = []
		segPoints = []
		isInLine = False

		for p1 in ps:
			segPoints.append(p1)
			segLen = len(segPoints)
			if segLen < 3:
				continue
			if segLen == 3:
				currentCircle = Circle2.circleFromThreePoints(segPoints[0], segPoints[1], segPoints[2])
				if currentCircle is None:
					isInLine = True
				continue

			# ok, we have more than 3 points
			if isInLine:
				if ZPathSegment.isStillInLine(segPoints, tolerance):
					continue
				segPoints.pop()
				ZPathSegment.addOneLine(ret, segPoints)
				last = segPoints.pop()
				segPoints = []
				segPoints.append(last)
				segPoints.append(p1)
				isInLine = False
			else:
				newCircle = ZPathSegment.isAcceptableTolerance(segPoints, currentCircle, tolerance)
				if newCircle is not None:
					currentCircle = newCircle
				else:
					# we need a new segment, first finish the current
					segPoints.pop()
					ZPathSegment.addOneSegment(ret, segPoints, currentCircle)
					last = segPoints.pop()			
					segPoints = []
					segPoints.append(last)
					segPoints.append(p1)

		#print('one segment done')
		if len(segPoints) > 1:
			if isInLine:
				ZPathSegment.addOneLine(ret, segPoints)
			else:
				self.addOneSegment(ret, segPoints, currentCircle)
		return ret


	@classmethod
	def addOneSegment(cls, segList, segPoints, currentCircle):
		if len(segPoints) < 2:
			raise Exception('this should never happen: segPoints less than 2')
		if len(segPoints) == 2:
			newSeg = ZLineSegment(segPoints[0], segPoints[1])
		else:
			midIdx = int(len(segPoints) / 2.0)
			poly = Polygon([segPoints[0], segPoints[midIdx], segPoints[-1]])
			area = poly.area()
			if ZGeomItem.almostEqual(area, 0):
				newSeg = ZLineSegment(segPoints[0], segPoints[-1])
			else:
				rad = currentCircle.m_radius
				newSeg = ZArcSegment(rad, rad, 0, segPoints[0], segPoints[-1], False, poly.isClockwise(Point(0, 0, 1)))
		segList.append(newSeg)


	@classmethod
	def addOneLine(cls, segList, segPoints):
		segList.append(ZLineSegment(segPoints[0], segPoints[-1]))


	@classmethod
	def isAcceptableTolerance(cls, points, currentCircle, tolerance, step=1):
		minRad = 1000000000
		maxRad = 0
		center = currentCircle.m_center
		for p in points:
			rad = abs(p.distanceOfPoint(center))
			minRad = min(minRad, rad)
			maxRad = max(maxRad, rad)
			diff = maxRad - minRad

		if diff < tolerance:
			return currentCircle
		if step == 1 and len(points) > 3:
			# make a second try
			midIdx = int(round(len(points) / 2.0))
			newCircle = Circle2.circleFromThreePoints(points[0], points[midIdx], points[-1])
			return cls.isAcceptableTolerance(points, newCircle, tolerance, step=2)
		return None


	@classmethod
	def isStillInLine(cls, segPoints, tolerance):
		line = Line(segPoints[0], segPoints[-1])
		for ii in range(1, len(segPoints) - 1):
			if line.distanceOf(segPoints[ii]) > tolerance:
				return False
		return True


	@classmethod
	def pointString(cls, point, rounded):
		ret = str(round(point.m_x, rounded)) + ',' + str(round(point.m_y, rounded)) + ' '
		return ret

	def getInterPointsWithTangentAndStop(self, offset):
		ret = self.getInterPointsWithTangent(offset)
		last = ret[-1][0]
		if not last.isSameAs(self.m_stop):
			ret.append(self.getInterPointWithTangent(1.0))
		return ret


	def getInterPointsAndStop(self, offset):
		ret = self.getInterPoints(offset)
		last = ret[-1]
		if not last.isSameAs(self.m_stop):
			ret.append(self.m_stop)
		return ret



###########################################################
###########################################################


class ZLineSegment(ZPathSegment):
	"""
		A line between 2 points
	"""

	def copy(self):
		# caution: does not copy the points
		return ZLineSegment(self.m_start, self.m_stop)


	def transformBy(self, affine):
		self.m_start = affine * self.m_start
		self.m_stop = affine * self.m_stop


	def getInterPoints(self, _):
		return [self.m_start, self.m_stop]


	def getInterPointsWithTangent(self, _):
		tang = self.m_stop - self.m_start
		m1 = [self.m_start, -tang]
		m2 = [self.m_stop, -tang]
		return [m1, m2]


	def getInterPointWithTangent(self, _):
		tang = self.m_stop - self.m_start
		return [self.m_start, -tang]


	def printComment(self, comment, tabs=1, rounded=2):
		super().printComment(comment, tabs, rounded)

		print(')')


	def svgCode(self, rounded):
		ret = 'L '
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


	def getInterPointAtParameter(self, t):
		return self.m_start + (self.m_stop - self.m_start).scaledBy(t)


	def xmlAddDetailsTo(self, node):
		pass


	def cncFriendly(self, _):
		"""
			Return an array of Line-or-Arc segments that approximate myself
		"""
		return [self.copy()]


	def getTangentAtStart(self):
		"""
			Return the tangent at my start point
		"""
		return self.m_stop - self.m_start

	def asNurbsDescription(self) -> list[Point]:
		"""
			Return a list of control points that make a nurbs description of me
		"""
		return [self.m_start, self.m_stop]

		

####################################################
####################################################


class ZBezier3Segment(ZPathSegment):
	"""
		a cubic bezier segment
	"""
	s_bernsteinFunctions = {}
	s_bernsteinDerivationsOne = {}

	def __init__(self, p1, p2, h1, h2):
		super().__init__(p1, p2)
		self.m_handleStart = h1
		self.m_handleStop = h2



	@classmethod
	def makeTwoPointsConnection(cls, start: Point, tangentStart: Point, stop: Point, tangentStop: Point, stiffnessStart:float=0.5, stiffnessStop:float= 0.5) ->ZBezier3Segment:
		if stiffnessStart > 0.9 > stiffnessStop > 0.9:
			raise Exception('ZBezier3Segment:makeTwoPointsConnection(): stiffnessess must be <= 0.9')
		dist = start.distanceOfPoint(stop)
		handle1 = start + tangentStart.scaledTo(dist * stiffnessStart)
		handle2 = stop + tangentStop.scaledTo(dist * stiffnessStop)
		return ZBezier3Segment(start, stop, handle1, handle2)


	@classmethod
	def getBernsteinCoefficients(cls, numberOfSteps):

		if numberOfSteps in cls.s_bernsteinFunctions:
			return [cls.s_bernsteinFunctions[numberOfSteps], cls.s_bernsteinDerivationsOne[numberOfSteps]]

		diff = 1.0 / numberOfSteps
		coeffsFunction = []
		coeffsDerivative = []
		for ii in range(numberOfSteps):
			t1 = ii * diff
			t2 = 1.0 - t1

			# first: the function
			coeffs = []
			coeffs.append(t2 * t2 * t2)
			coeffs.append(3 * t1 * t2 * t2)
			coeffs.append(3 * t1 * t1 * t2)
			coeffs.append(t1 * t1 * t1)
			coeffsFunction.append(coeffs)

			# second: the first derivative:
			coeffs = []
			coeffs.append(3 * t2 * t2)
			coeffs.append(6 * t1 * t2)
			coeffs.append(3 * t1 * t1)
			coeffsDerivative.append(coeffs)

		cls.s_bernsteinFunctions[numberOfSteps] = coeffsFunction
		cls.s_bernsteinDerivationsOne[numberOfSteps] = coeffsDerivative
		return [coeffsFunction, coeffsDerivative]


	def makeFlat(self):
		super().makeFlat()
		self.m_handleStart.m_z = 0
		self.m_handleStop.m_z = 0

		
	def svgCode(self, rounded):
		ret = 'C '
		ret += ZPathSegment.pointString(self.m_handleStart, rounded)
		ret += ZPathSegment.pointString(self.m_handleStop, rounded)
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


	def deCasteljau3(self, t):
		# return the cubic bezierpoint for a given t (between 0 and 1)
		pass1Points = self.deCasteljauPass1(t)
		(startToHandle, handleToHandle, handleToStop) = pass1Points
		pass2Handle1 = self.interpolate(startToHandle, handleToHandle, t)
		pass2Handle2 = self.interpolate(handleToHandle, handleToStop, t)
		ret = self.interpolate(pass2Handle1, pass2Handle2, t)
		return ret


	def getInterPointAtParameter(self, t):
		return self.deCasteljau3(t)


	def deCasteljau3WithTangent(self, t):
		# return the cubic bezierpoint for a given t (between 0 and 1)
		# additional return the tangent direction in this point (pointing to greater t)
		pass1Points = self.deCasteljauPass1(t)
		(startToHandle, handleToHandle, handleToStop) = pass1Points
		pass2Handle1 = self.interpolate(startToHandle, handleToHandle, t)
		pass2Handle2 = self.interpolate(handleToHandle, handleToStop, t)
		ret = self.interpolate(pass2Handle1, pass2Handle2, t)
		if pass2Handle1.isSameAs(pass2Handle2):
			# this seems to happen, when the handle and point is identical
			# just take the other handle
			if t <= 0.1:
				return [ret, self.getTangentAtStart()]
				#if self.m_start.isSameAs(self.m_handleStart):
				#	return [ret, self.m_handleStop - self.m_start]
				
			if t > 0.9:
				return [ret, self.getTangentAtStop()]
				#print('return default value in deCasteljau3WithTangent')
				#if self.m_stop.isSameAs(self.m_handleStop):
				#	return [ret, self.m_handleStart - self.m_stop]
			#return [ret, Point(-1, 0, 0)]
			raise Exception('unhandled unknown tangent in deCasteljau3WithTangent')
		return [ret, pass2Handle2 - pass2Handle1]


	def getTangentAtStart(self):
		"""
			handle the degenerated cases
		"""
		if self.m_start.isSameAs(self.m_handleStart):
			if self.m_start.isSameAs(self.m_handleStop):
				return self.m_stop - self.m_start
			return self.m_handleStop - self.m_start
		elif not self.m_start.isSameAs(self.m_stop):
			# this should be the normal case
			return self.m_handleStart - self.m_start
		raise Exception('ZBezier3Segment completely degenerated')


	def getTangentAtStop(self):
		"""
			handle the degenerated case
		"""
		if self.m_stop.isSameAs(self.m_handleStop):
			if self.m_stop.isSameAs(self.m_handleStart):
				return self.m_start - self.m_stop
			return self.m_handleStart - self.m_stop
		elif not self.m_start.isSameAs(self.m_stop):
			# this should be the normal case
			return self.m_handleStop - self.m_stop
		raise Exception('ZBezier3Segment completely degenerated')


	def deCasteljauPass1(self, t):
		startToHandle = self.interpolate(self.m_start, self.m_handleStart, t)
		handleToHandle = self.interpolate(self.m_handleStart, self.m_handleStop, t)
		handleToStop = self.interpolate(self.m_handleStop, self.m_stop, t)
		return [startToHandle, handleToHandle, handleToStop]


	def interpolate(self, p1, p2, t):
		diff = (p2 - p1).scaledBy(t)
		return p1 + diff


	def reverse(self):
		super().reverse()
		h1 = self.m_handleStart
		h2 = self.m_handleStop
		self.m_handleStart = h2
		self.m_handleStop = h1


	def getInterPointsDeCasteljau(self, offset):
		points = []
		fact = 0.0
		while fact < 1:
			points.append(self.deCasteljau3(fact))
			fact = fact + offset
		return points


	def getInterPoints(self, offset):
		"""
			get interpoints with Bernstein coefficients
		"""
		#print('--------------------------------------------------------------')
		points = []
		numPoints = int(1.0 / offset)
		coeffs = ZBezier3Segment.getBernsteinCoefficients(numPoints)[0]
		p0 = self.m_start
		p1 = self.m_handleStart
		p2 = self.m_handleStop
		p3 = self.m_stop
		for co in coeffs:
			p = p0.scaledBy(co[0]) + p1.scaledBy(co[1]) + p2.scaledBy(co[2]) +  p3.scaledBy(co[3])
			points.append(p)
		return points


	def getInterPointsWithTangent(self, offset):
		"""
			get interpoints and tangents with Bernstein coefficients
			Return array of arrays (each one contains point and derivative)
		"""
		#print('--------------------------------------------------------------')
		ret = []
		numPoints = int(1.0 / offset)
		coeffsArr = ZBezier3Segment.getBernsteinCoefficients(numPoints)
		coFunction = coeffsArr[0]
		coDerivative = coeffsArr[1]
		p0 = self.m_start
		p1 = self.m_handleStart
		p2 = self.m_handleStop
		p3 = self.m_stop

		d0 = p1 - p0
		d1 = p2 - p1
		d2 = p3 - p2
		idx = 0
		for coF in coFunction:
			pF = p0.scaledBy(coF[0]) + p1.scaledBy(coF[1]) + p2.scaledBy(coF[2]) +  p3.scaledBy(coF[3])
			coD = coDerivative[idx]
			pD = d0.scaledBy(coD[0]) + d1.scaledBy(coD[1]) + d2.scaledBy(coD[2])
			if pD.isSameAs(Point()):
				# we have a zero derivative, possible at start or end or for degenerated segment
				if idx == 0:
					ret.append([pF, self.getTangentAtStart()])
				else:
					# handle all other degenerate cases (might raise exception)
					ret.append([pF, self.getTangentAtStop()])
			else:
				ret.append([pF, pD])
			idx += 1
		return ret


	def getInterPointsWithTangentDeCasteljau(self, offset):
		"""
			Return array of arrays (each one contains point and derivative)
		"""
		points = []
		fact = 0.0
		while fact < 1:
			points.append(self.deCasteljau3WithTangent(fact))
			fact = fact + offset
		return points


	def getInterPointWithTangent(self, param):
		return self.deCasteljau3WithTangent(param)


	def copy(self):
		# caution: does not copy the points
		return ZBezier3Segment(self.m_start, self.m_stop, self.m_handleStart, self.m_handleStop)


	def transformBy(self, affine):
		"""
			Transform myself. Return nothing
		"""
		self.m_start = affine * self.m_start
		self.m_stop = affine * self.m_stop
		self.m_handleStart = affine * self.m_handleStart
		self.m_handleStop = affine * self.m_handleStop


	def xmlAddDetailsTo(self, node):
		node.set('handleStart', self.m_handleStart.xmlCoords())
		node.set('handleStop', self.m_handleStop.xmlCoords())


	def isClockwise(self):
		# seen from (0, 0, 1)
		points = [self.m_start, self.m_handleStart, self.m_handleStop, self.m_stop]
		poly = Polygon(points)
		return poly.isClockwise(Point(0, 0, 1))


	def asNurbsDescription(self) -> list[Point]:
		"""
			Return a list of control points that make a nurbs description of me
		"""
		return [self.m_start, self.m_handleStart, self.m_handleStop, self.m_stop]
	

########################################################
########################################################


class ZBezier2Segment(ZPathSegment):
	"""
		a cubic bezier segment
	"""
	def __init__(self, p1, p2, h):
		super().__init__(p1, p2)
		self.m_handle = h


	@classmethod
	def makeTwoPointsConnection(cls, start, tangent, stop, stiffness=0.5):
		if stiffness > 0.9:
			raise Exception('ZBezier2Segment:makeTwoPointsConnection(): stiffness must be <= 0.9')
		dist = start.distanceOfPoint(stop)
		handle = start + tangent.scaledTo(dist * stiffness)
		return ZBezier2Segment(start, stop, handle)



	def makeFlat(self):
		super().makeFlat()
		self.m_handle.m_z = 0


	def deCasteljau2(self, t):
		startToHandle = self.interpolate(self.m_start, self.m_handle, t)
		handleToStop = self.interpolate(self.m_handle, self.m_stop, t)
		return self.interpolate(startToHandle, handleToStop, t)


	def getInterPointAtParameter(self, t):
		return self.deCasteljau2(t)


	def interpolate(self, p1, p2, t):
		diff = (p2 - p1).scaledBy(t)
		return p1 + diff


	def getInterPoints(self, offset):
		points = []
		fact = 0.0
		while fact < 1:
			points.append(self.deCasteljau2(fact))
			fact = fact + offset
		return points


	def getInterPointsWithTangent(self, offset):
		points = []
		fact = 0.0
		while fact < 1:
			points.append(self.deCasteljau2WithTangent(fact))
			fact = fact + offset
		return points


	def deCasteljau2WithTangent(self, t):
		# return the quadratic bezierpoint for a given t (between 0 and 1)
		# additional return the tangent direction in this point (pointing to greater t)
		startToHandle = self.interpolate(self.m_start, self.m_handle, t)
		handleToStop = self.interpolate(self.m_handle, self.m_stop, t)
		point = self.interpolate(startToHandle, handleToStop, t)
		return [point, handleToStop - startToHandle]


	def getInterPointWithTangent(self, param):
		return self.deCasteljau2WithTangent(param)


	def copy(self):
		# caution: does not copy the points
		return ZBezier2Segment(self.m_start, self.m_stop, self.m_handle)


	def transformBy(self, affine):
		"""
			Transform myself. Return nothing
		"""
		#self.m_start.printComment('vorher')
		self.m_start = affine * self.m_start
		#self.m_start.printComment('nachher')
		#print('')
		self.m_stop = affine * self.m_stop
		self.m_handle = affine * self.m_handle


	def xmlAddDetailsTo(self, node):
		node.set('handle', self.m_handle.xmlCoords())


	def isClockwise(self):
		# seen from (0, 0, 1)
		points = [self.m_start, self.m_handle, self.m_stop]
		poly = Polygon(points)
		return poly.isClockwise(Point(0, 0, 1))

####################################################
####################################################


class ZArcSegment(ZPathSegment):
	"""
		an svg arc segment. There are basically 2 constructors:
		- oldArc == None: for creation from an svg file (must be in x-y-plane)
		- oldArc != None: for creation from another arc (then the first args may be dummies and are ignored)
	"""
	def __init__(self, rx, ry, axisAngle, p1, p2, largeArcFlag, sweepFlag, oldArc=None, center=None, normalVector=None, focusOffsetVector=None):
		super().__init__(p1, p2)
		self.m_rx = rx
		self.m_ry = ry
		self.m_xAngle = axisAngle
		self.m_largeArcFlag = largeArcFlag
		self.m_sweepFlag = sweepFlag
		self.m_center = None
		self.m_startAngle = math.nan
		self.m_stopAngle = math.nan
		self.m_deltaAngle = math.nan
		self.m_focus1 = None
		self.m_focus2 = None
		self.m_normalVector = None
		self.m_focusOffsetVector = None
		self.m_mapUnitCircleToSelf = None

		if oldArc is None:
			self.m_normalVector = Point(0, 0, 1)	# we are in x-y-plane
			self.adaptSvgValues()
		else:
			self.adaptValuesFromOtherArc(oldArc)
		self.selfTest()


	def getParameterRange(self):
		"""
			Return an array of 2 values for my parameter range.
			Overrides same method in ZPathSegment
		"""
		return [self.m_startAngle, self.m_stopAngle]


	def selfTest(self):
		"""
			Check the internal consistency
		"""
		#stopA1 = ZGeomItem.normalizeAngle(self.m_stopAngle)
		#stopA2 = ZGeomItem.normalizeAngle(self.m_startAngle + self.m_deltaAngle)

		if not ZGeomItem.almostEqualAngles(self.m_stopAngle, self.m_startAngle + self.m_deltaAngle):
			#print('stopA1: ' + str(stopA1))
			#print('stopA2: ' + str(stopA2))
			raise Exception('ZArcSegment:selfTest error: angle problem')

		f1 = self.m_focus1
		f2 = self.m_focus2
		c = self.m_center
		fO = self.m_focusOffsetVector
		# i am not sure, if this is really true:
		#if not f1.isSameAs(c + fO) or not f2.isSameAs(c - fO):
		#	raise Exception('ZArcSegment:selfTest error: focus point problem')

		startA = self.m_startAngle
		pStart = self.getPointForParameter(startA)
		pStop = self.getPointForParameter(self.m_stopAngle)
		if not pStart.isSameAs(self.m_start) or not pStop.isSameAs(self.m_stop):
			raise Exception('ZArcSegment:selfTest error: parameter problem')

		# normalVectoris currently not supported
		#if not self.isACircle():
		#	if not self.m_normalVector.isPerpendicular(self.m_focusOffsetVector):
		#		raise Exception('ZArcSegment:selfTest error: normal vector problem')


	def adaptValuesFromOtherArc(self, otherArc):
		self.m_rx = otherArc.m_rx
		self.m_ry = otherArc.m_ry
		self.m_xAngle = otherArc.m_xAngle
		self.m_largeArcFlag = otherArc.m_largeArcFlag
		self.m_sweepFlag = otherArc.m_sweepFlag
		self.m_center = otherArc.m_center
		self.m_startAngle = otherArc.m_startAngle
		self.m_stopAngle = otherArc.m_stopAngle
		self.m_deltaAngle = otherArc.m_deltaAngle
		self.m_focus1 = otherArc.m_focus1
		self.m_focus2 = otherArc.m_focus2
		self.m_normalVector = otherArc.m_normalVector
		self.m_focusOffsetVector = otherArc.m_focusOffsetVector
		self.m_mapUnitCircleToSelf = otherArc.m_mapUnitCircleToSelf


	def makeFlat(self):
		super().makeFlat()
		self.m_center.m_z = 0
		self.m_focus1.m_z = 0
		self.m_focus2.m_z = 0


	@classmethod
	# create 4 quarter circles
	def createFullCircle(cls, center, radius, clockwise, greatFlag=False):
		diffX = Point(radius)
		diffY = Point(0, radius)
		if not clockwise:
			diffX = - diffX
		p1 = center + diffX
		p3 = center - diffX
		p2 = center + diffY
		p4 = center - diffY
		ret = ZPath()
		ret.addSegment(ZArcSegment(radius, radius, 0, p1, p2, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radius, radius, 0, p2, p3, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radius, radius, 0, p3, p4, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radius, radius, 0, p4, p1, greatFlag, clockwise))
		return ret


	@classmethod
	# create 4 quarter ellipses
	def createFullEllipse(cls, center, radiusX, radiusY, angle, clockwise, greatFlag=False):
		diffX = Point(radiusX)
		diffY = Point(0, radiusY)
		if not clockwise:
			diffX = - diffX
		p1 = center + diffX
		p3 = center - diffX
		p2 = center + diffY
		p4 = center - diffY
		ret = ZPath()
		ret.addSegment(ZArcSegment(radiusX, radiusY, 0, p1, p2, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radiusX, radiusY, 0, p2, p3, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radiusX, radiusY, 0, p3, p4, greatFlag, clockwise))
		ret.addSegment(ZArcSegment(radiusX, radiusY, 0, p4, p1, greatFlag, clockwise))
		rotLine = Line(center, center + Point(0, 0, 1))
		aff = Affine.makeRotationAffine(rotLine, angle)
		ret.transformBy(aff)
		return ret


	@classmethod
	def createFullCircleRing(cls, center, radiusOuter, radiusInner, greatFlag=False):
		path1 = cls.createFullCircle(center, radiusOuter, True, greatFlag=greatFlag)
		path2 = cls.createFullCircle(center, radiusInner, False, greatFlag=greatFlag)
		for seg in path2.m_segments:
			path1.addSegment(seg)
		return path1


	@classmethod
	def createFullEllipseRing(cls, center, radiusOuterX, radiusOuterY, radiusInnerX, radiusInnerY, angle):
		path1 = cls.createFullEllipse(center, radiusOuterX, radiusOuterY, angle, True)
		path2 = cls.createFullEllipse(center, radiusInnerX, radiusInnerY, angle, False)
		for seg in path2.m_segments:
			path1.addSegment(seg)
		return path1


	def svgCode(self, rounded):
		# return a string that is usable as the d-attribute of a path node
		ret = 'A '
		rounded = 5
		ret += str(round(self.m_rx, rounded)) + ' '
		ret += str(round(self.m_ry, rounded)) + ' '
		ret += str(round(self.m_xAngle, rounded)) + ' '
		flag = '0'
		if self.m_largeArcFlag:
			flag = '1'
		ret += flag + ' '
		flag = '0'
		if self.m_sweepFlag:
			flag = '1'
		ret += flag + ' '
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


	def adaptSvgValues(self):

		# calculate my center and focus points
		# i rotate myself around the origin, so i am axis parallel, so center calculation can be done more easyly
		affine = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), - self.m_xAngle)
		self.rotateBy(affine)
		self.getMyCenter()
		self.makeMyReference()
		affInverse = affine.inverted()
		# rotate myself back to my real position:
		self.rotateBy(affInverse)

		# make the affine that transforms a point on the unit circle to the corresponding point on me
		affineRotation = Affine.makeRotationAffine(Line(self.m_center, direction=Point(0, 0, 1)), self.m_xAngle)
		matrixStretch = Matrix([Point(self.m_rx), Point(0, self.m_ry), Point(0, 0, 1)])
		affStretch = Affine(matrixStretch)
		affTranslate = Affine(None, self.m_center)
		affFull = affineRotation * affTranslate * affStretch
		self.m_mapUnitCircleToSelf = affFull


	def copy(self):
		return ZArcSegment(self.m_rx, self.m_ry, self.m_xAngle, self.m_start, self.m_stop, self.m_largeArcFlag, self.m_sweepFlag, oldArc=self)


	def printComment(self, comment, tabs=0, rounded=2):
		super().printComment(comment, tabs, rounded)
		tabs = tabs + 1
		ZGeomItem.printNumRounded('rx', self.m_rx, tabs, rounded)
		ZGeomItem.printNumRounded('ry', self.m_ry, tabs, rounded)
		ZGeomItem.printNumRounded('x-angle', self.m_xAngle, tabs, rounded)
		ZGeomItem.printStringTabbed('large', self.m_largeArcFlag, tabs)
		ZGeomItem.printStringTabbed('clockwise', self.isClockwise(), tabs)
		self.m_center.printComment('center', tabs)
		self.m_focus1.printComment('focus 1', tabs)
		self.m_focus2.printComment('focus 2', tabs)
		ZGeomItem.printNumRounded('startAngle', self.m_startAngle, tabs, rounded)
		ZGeomItem.printNumRounded('stopAngle', self.m_stopAngle, tabs, rounded)
		ZGeomItem.printNumRounded('deltaAngle', self.m_deltaAngle, tabs, rounded)


	def isClockwise(self):
		return not self.m_sweepFlag


	def reverse(self):
		super().reverse()
		self.m_sweepFlag = not self.m_sweepFlag


	def makeMyReference(self):
		# my reference is a Circle2 in the xy plane with radius 1
		# self.m_affineFromReference is an affine, that maps (1,0) and (0, 1) to
		# my respective points

		# create focus points:
		rx = self.m_rx
		ry = self.m_ry
		radicant = rx*rx - ry*ry
		if rx >= ry:
			#useX = True
			#rMax = rx
			angleOffset = 0
		else:
			#useX = False
			#rMax = ry
			radicant *= -1
			angleOffset = 90
		focusDist = math.sqrt(radicant)
		axisDirX = math.cos(math.radians(self.m_xAngle + angleOffset))
		axisDirY = math.sin(math.radians(self.m_xAngle + angleOffset))
		focusOffset = Point(axisDirX, axisDirY).scaledTo(focusDist)
		self.m_focusOffsetVector = focusOffset
		self.m_focus1 = self.m_center + focusOffset
		self.m_focus2 = self.m_center - focusOffset


	def getPointForParameter(self, angle):
		affFull = self.m_mapUnitCircleToSelf
		refPoint = Circle2(Point(), 1).pointForAngle(angle)
		return affFull * refPoint


	def getInterPointAtParameter(self, t):
		return self.getPointForParameter(t)


	def getPointForParameterWithTangents(self, angle):
		affFull = self.m_mapUnitCircleToSelf

		refPoint = Circle2(Point(), 1).pointForAngle(angle)
		refTangent = refPoint.crossProduct(Point(0, 0, 1))
		#if self.m_sweepFlag:
		#	refTangent = - refTangent
		return [affFull * refPoint, affFull * refTangent]


	def containsPoint(self, point):
		# is this really needed? there is a method in superclass!!!
		# does not check, if point.m_z == 0
		f1 = self.m_focus1
		f2 = self.m_focus2
		d = f1.distanceOfPoint(point) + f2.distanceOfPoint(point) - 2*self.getBiggerRadius()
		return ZGeomItem.almostEqual(d, 0)


	def getBiggerRadius(self):
		return max(self.m_rx, self.m_ry)

	# ***********************************************
	# Helper functions for elliptical arc conversion.
	# ***********************************************

	def vector_angle(self, u, v):
		d = math.hypot(*u) * math.hypot(*v)
		if d == 0:
			return 0
		c = (u[0] * v[0] + u[1] * v[1]) / d
		if c < -1:
			c = -1
		elif c > 1:
			c = 1
		s = u[0] * v[1] - u[1] * v[0]
		return math.degrees(math.copysign(math.acos(c), s))


	def getMyCenter(self): 		# , x1, y1, x2, y2, fA, fS, rx, ry, phi=0):
		'''
		See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
		note that we reduce phi to zero outside this routine
		'''

		x1 = self.m_start.m_x
		y1 = self.m_start.m_y
		x2 = self.m_stop.m_x
		y2 = self.m_stop.m_y

		fA = 0
		if self.m_largeArcFlag:
			fA = 1
		fS = 0
		if self.m_sweepFlag:
			fS = 1

		phi = self.m_xAngle

		rx = math.fabs(self.m_rx)
		ry = math.fabs(self.m_ry)

		# step 1
		if phi:
			phi_rad = math.radians(phi)
			sin_phi = math.sin(phi_rad)
			cos_phi = math.cos(phi_rad)
			tx = 0.5 * (x1 - x2)
			ty = 0.5 * (y1 - y2)
			x1d = cos_phi * tx - sin_phi * ty
			y1d = sin_phi * tx + cos_phi * ty
		else:
			x1d = 0.5 * (x1 - x2)
			y1d = 0.5 * (y1 - y2)

		# step 2
		# we need to calculate
		# (rx*rx*ry*ry-rx*rx*y1d*y1d-ry*ry*x1d*x1d)
		# -----------------------------------------
		#     (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
		#
		# that is equivalent to
		#
		#          rx*rx*ry*ry
		# = -----------------------------  -    1
		#   (rx*rx*y1d*y1d+ry*ry*x1d*x1d)
		#
		#              1
		# = -------------------------------- - 1
		#   x1d*x1d/(rx*rx) + y1d*y1d/(ry*ry)
		#
		# = 1/r - 1
		#
		# it turns out r is what they recommend checking
		# for the negative radicand case
		r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
		if r > 1:
			#print('arc radius correction done')
			rr = math.sqrt(r)
			rx *= rr
			ry *= rr
			r = x1d * x1d / (rx * rx) + y1d * y1d / (ry * ry)
			r = 1 / r - 1
		elif r != 0:
			r = 1 / r - 1
		if -1e-10 < r < 0:
			r = 0
		r = math.sqrt(r)
		if fA == fS:
			r = -r
		cxd = (r * rx * y1d) / ry
		cyd = -(r * ry * x1d) / rx

		# step 3
		if phi:
			cx = cos_phi * cxd - sin_phi * cyd + 0.5 * (x1 + x2)
			cy = sin_phi * cxd + cos_phi * cyd + 0.5 * (y1 + y2)
		else:
			cx = cxd + 0.5 * (x1 + x2)
			cy = cyd + 0.5 * (y1 + y2)

		# step 4
		theta1 = self.vector_angle((1, 0), ((x1d - cxd) / rx, (y1d - cyd) / ry))
		dtheta = self.vector_angle(
			((x1d - cxd) / rx, (y1d - cyd) / ry),
			((-x1d - cxd) / rx, (-y1d - cyd) / ry)
		) % 360
		if fS == 0 and dtheta > 0:
			dtheta -= 360
		elif fS == 1 and dtheta < 0:
			dtheta += 360

		self.m_center = Point(cx, cy)
		self.m_rx = rx
		self.m_ry = ry
		self.m_startAngle = theta1
		self.m_deltaAngle = dtheta
		self.m_stopAngle = ZGeomItem.normalizeAngle(self.m_startAngle + self.m_deltaAngle)


	def belongsToSameEllipse(self, other):
		if not self.m_center.isSameAs(other.m_center):
			return False
		if not ZGeomItem.almostEqual(self.m_rx, other.m_rx):
			return False
		if not ZGeomItem.almostEqual(self.m_ry, other.m_ry):
			return False
		if not ZGeomItem.almostEqual(self.m_xAngle, other.m_xAngle):
			return False
		return True


	def rotateBy(self, affine):
		# this is only for affines that mean a rotation around a point!!
		self.m_start = affine * self.m_start
		self.m_stop = affine * self.m_stop

		if self.m_center:
			self.m_center = affine * self.m_center

		if self.m_focus1:
			self.m_focus1 = affine * self.m_focus1

		if self.m_focus2:
			self.m_focus2 = affine * self.m_focus2

		radians = math.radians(self.m_xAngle)
		offset = Point(math.cos(radians), math.sin(radians))
		newOffset = affine * offset - affine * Point()
		deltaAngle =   Affine.fullAngleBetween2d(newOffset, offset)
		self.m_xAngle -= deltaAngle
		self.m_xAngle = ZGeomItem.normalizeAngle(self.m_xAngle)


	def transformBy(self, affine):
		"""
			Transform myself. Return nothing
		"""
		# for now we leave the both flags untouched
		oldStart = self.m_start
		oldStop = self.m_stop
		oldCenter = self.m_center
		# we must recalculate the radii
		oldVertexX = self.m_mapUnitCircleToSelf * Point(1)
		oldVertexY = self.m_mapUnitCircleToSelf * Point(0, 1)

		newStart = affine * oldStart
		newStop = affine * oldStop
		newCenter = affine * oldCenter
		newVertexX = affine * oldVertexX
		newVertexY = affine * oldVertexY

		newRx = newCenter.distanceOfPoint(newVertexX)
		newRy = newCenter.distanceOfPoint(newVertexY)
		newXAngle = Affine.fullAngleBetween2d(Point(1), newVertexX - newCenter)
		if ZGeomItem.almostEqual(newRx, newRy):
			newRx = newRy
		self.m_rx = newRx
		self.m_ry = newRy
		self.m_xAngle = newXAngle

		self.m_start = newStart
		self.m_stop = newStop
		self.m_center = newCenter
		print('recalculation of focus points is questionable')
		self.m_focus1 = affine * self.m_focus1
		self.m_focus2 = affine * self.m_focus2

		matrix = affine.m_matrix
		self.m_normalVector = matrix * self.m_normalVector
		self.m_focusOffsetVector = self.m_focus1 - self.m_center

		self.m_mapUnitCircleToSelf = affine * self.m_mapUnitCircleToSelf

		#self.adaptSvgValues()
		self.selfTest()


	def getInterPoints(self, offset):
		# offset is the step width (0.0 < offset < 1.0)
		# make as many steps as possible before reaching 1.0
		points = []
		angle = self.m_startAngle
		numberOfSteps = 1.0 / offset
		stepAngle = self.m_deltaAngle / numberOfSteps
		stepNo = 0
		while stepNo < numberOfSteps:
			ownPoint = self.getPointForParameter(angle)
			#ownPoint.printComment(str(stepNo))
			points.append(ownPoint)
			angle = angle + stepAngle
			stepNo = stepNo + 1
		return points


	def getMyMiddlePoint(self):
		"""
			Return the point on my graph with the middle parameter (angle) value
		"""
		return self.getPointForParameter(self.m_startAngle + 0.5 * self.m_deltaAngle)


	def getInterPointsWithTangent(self, offset):
		points = []
		angle = self.m_startAngle
		numberOfSteps = 1.0 / offset
		stepAngle = self.m_deltaAngle / numberOfSteps
		stepNo = 0
		while stepNo < numberOfSteps:
			ownPoint, ownTan = self.getPointForParameterWithTangents(angle)
			#ownPoint.printComment('step ' + str(stepNo))
			points.append([ownPoint, ownTan])
			angle = angle + stepAngle
			stepNo = stepNo + 1
		return points


	def getInterPointWithTangent(self, param):
		return self.getPointForParameterWithTangents(param)


	def __str__(self):
		ret = 'ZArcSegment(center=' + str(self.m_center) + ')'
		return ret


	def xmlAddDetailsTo(self, node):
		node.set('center', self.m_center.xmlCoords())
		node.set('focus1', self.m_focus1.xmlCoords())
		node.set('focus2', self.m_focus2.xmlCoords())
		node.set('rx', str(self.m_rx))
		node.set('ry', str(self.m_ry))
		node.set('startAngle', str(self.m_startAngle))
		node.set('stopAngle', str(self.m_stopAngle))
		node.set('deltaAngle', str(self.m_deltaAngle))

		#self.m_largeArcFlag = largeArcFlag
		#self.m_sweepFlag = sweepFlag


	def cncFriendly(self, tolerance):
		"""
			Return an array of Line-or-Arc segments that approximate myself
		"""
		if self.m_rx == self.m_ry:
			return [self.copy()]
		return super().cncFriendly(tolerance)


	def isACircle(self):
		return ZGeomItem.almostEqual(self.m_rx, self.m_ry)



#####################################################
#####################################################


class ZPath:
	"""
		The path class, holding a list of segments
	"""
	def __init__(self, groupId=None):
		self.m_segments = None
		self.m_groupId = groupId


	@classmethod
	def makePolygonPath(cls, points, closed=False):
		ret = ZPath()
		for ii in range(1, len(points)):
			p1 = points[ii-1]
			p2 = points[ii]
			ret.addSegment(ZLineSegment(p1, p2))
		if closed:
			ret.closeByLine()
		return ret


	def setSegments(self, segs):
		self.m_segments = segs


	def addSegment(self, segment):
		if self.m_segments is None:
			self.m_segments = []
		self.m_segments.append(segment)


	def describesAnEllipse(self):
		for seg in self.m_segments:
			if not isinstance(seg, ZArcSegment):
				return False
		return True


	def svgCode(self):
		# return a string that is usable as the d-attribute of a path node
		ret = ''
		if len(self.m_segments) == 0:
			return ret
		rounded = 5
		currPos = Point(0, 0)
		for seg in self.m_segments:
			if not seg.m_start.isSameAs(currPos):
				ret += 'M ' +  ZPathSegment.pointString(seg.m_start, rounded)
			ret += seg.svgCode(rounded)
			currPos = seg.m_stop
		if self.isClosed():
			ret += ' Z'
		return ret
			

	def prependSegment(self, segment):
		self.m_segments.insert(0, segment)
		

	def areSegsConnected(self):
		segs = self.m_segments
		for ii in range(0, len(segs) - 1):
			if not self.areSegsConnectable(segs[ii], segs[ii+1]):
				return False
		return True


	def isClosed(self):
		if not self.areSegsConnected():
			return False
		segs = self.m_segments
		return self.areSegsConnectable(segs[-1], segs[0])


	def areSegsConnectable(self, seg1, seg2):
		stop = seg1.m_stop
		start = seg2.m_start
		return stop.isSameAs(start)


	def reverse(self):
		"""
			Reverse my direction, changes myself
		"""
		self.m_segments.reverse()
		for seg in self.m_segments:
			seg.reverse()


	def reversed(self):
		"""
			Return a copy of me that is myself reversed
		"""
		ret = self.copy()
		ret.reverse()
		return ret


	def isClockwise(self):
		# seen from (0, 0, 1)
		points = [x.m_start for x in self.m_segments]
		if len(points) < 3:
			for seg in self.m_segments:
				if type(seg).__name__ == 'ZArcSegment':
					return seg.m_sweepFlag
				if isinstance(seg, ZBezier3Segment):
					return seg.isClockwise()
			print('cannot get isClockwise() for less than 3 points !!!!!!!!!!!!!!!!!!!!!!!')
			return None
		poly = Polygon(points)
		return poly.isClockwise(Point(0, 0, 1))


	def makeClockwise(self, what=True):
		if self.isClockwise() == what:
			return
		self.reverse()


	def getInterPoints(self, offset):
		points = []
		for seg in self.m_segments:
			newOnes = seg.getInterPoints(offset)
			if len(points) > 0 and points[-1].isSameAs(newOnes[0]):
				points.pop()
			points.extend(newOnes)
		return points


	def getInterPointsWithTangent(self, offset):
		points = []
		for seg in self.m_segments:
			points.extend(seg.getInterPointsWithTangent(offset))
		return points


	def supplementByMirror(self, lineOrPlane=None):
		# mirror all my segments and add to m_sements end in reverse order
		# if line 
		# does not neccessarily close myself
		if self.isClosed():
			self.m_segments.pop()
		if lineOrPlane is None:
			pStart = self.m_segments[0].m_start
			pStop = self.m_segments[-1].m_stop
			lineOrPlane = Line(pStart, pStop)
		copy = self.copy()
		copy.reverse()

		if isinstance(lineOrPlane, Line):
			affine = Affine.makeRotationAffine(lineOrPlane, 180)
		elif isinstance(lineOrPlane, Plane):
			affine = Affine.makeMirror(lineOrPlane)
		copy.transformBy(affine)
		self.m_segments.extend(copy.m_segments)


	def closeByLine(self):
		if self.isClosed():
			return
		lineStart = self.getStop()
		lineStop = self.getStart()
		line = ZLineSegment(lineStart, lineStop)
		self.m_segments.append(line)


	def transformBy(self, affine):
		"""
			Transform all my segments. Return nothing
		"""
		for seg in self.m_segments:
			seg.transformBy(affine)


	def transformedBy(self, affine):
		"""
			Return a copy of myself, that describes me transformed
		"""
		val = self.copy()
		val.transformBy(affine)
		return val


	def copy(self) -> ZPath:
		ret = ZPath(self.m_groupId)
		newSegs = [x.copy() for x in self.m_segments]
		ret.setSegments(newSegs)
		return ret


	def getSimpleBoundingBox(self):
		# just return the bounding box of all my segemnts' start and stop points
		Min = Point(10000000, 10000000, 10000000)
		Max = Point(-10000000, -10000000, -10000000)
		for seg in self.m_segments:
			Min = Min.min(seg.m_start)
			Min = Min.min(seg.m_stop)
			Max = Max.max(seg.m_start)
			Max = Max.max(seg.m_stop)
		return [Min, Max]


	def getStart(self):
		return self.m_segments[0].m_start


	def getSmartStop(self):
		# if i am not closed, return stop of my last segment
		# if i am, return the START of my last segment
		if self.isClosed():
			return self.m_segments[-1].m_start
		return self.m_segments[-1].m_stop


	def getStop(self):
		return self.m_segments[-1].m_stop


	def makeFlat(self):
		"""
			project to the x-y-plane
		"""
		for seg in self.m_segments:
			seg.makeFlat()

	
	def printTabs(self, tabs):
		for _ in range(tabs):
			print('	', end='')


	def printComment(self, comment, tabs=0, rounded=2):
		if not comment:
			comment = 'no_comment '
		if self.m_groupId is not None:
			comment += '(' + self.m_groupId + ')'
		self.printTabs(tabs)
		print(comment + ': ')
		print(self.__class__.__name__)
		ii = 0
		for seg in self.m_segments:
			
			if ii == 0:
				lastSeg = self.m_segments[-1]
			else:
				lastSeg = self.m_segments[ii-1]
			connectible = ' NOT '
			if self.areSegsConnectable(lastSeg, seg):
				connectible = ''
				
			seg.printComment('segment ' + str(ii), tabs + 1, rounded)
			self.printTabs(tabs + 2)
			print(f'segment is {connectible} connected from previous segment')
			ii = ii + 1

		ZGeomItem.printStringTabbed('path is closed', self.isClosed(), tabs)
		ZGeomItem.printStringTabbed('orientation is clockwise', self.isClockwise(), tabs)


	def extractFullEllipses(self):
		# check for closed arc sequences that describe a full ellipse
		# remove them from my segments and return an Ellipse/Circle description for each sequence
		ellipses = []
		toRemove = []
		candidate = []
		for seg in self.m_segments:
			if isinstance(seg, ZArcSegment):
				if len(candidate) > 0:
					# might be the next in an ellipse
					last = candidate[-1]
					if seg.belongsToSameEllipse(last):
						if last.m_stop.isSameAs(seg.m_start):
							# the possible ellipse is getting bigger
							candidate.append(seg)
						if candidate[0].m_start.isSameAs(seg.m_stop):
							# the new segment closes the ellipse
							toRemove.extend(candidate)
							if ZGeomItem.almostEqual(seg.m_rx, seg.m_ry):
								ellipse = Circle2(seg.m_center, seg.m_rx)
							else:
								ellipse = Ellipse2(seg.m_center, seg.m_rx, seg.m_ry, seg.m_xAngle)
							ellipses.append(ellipse)
							candidate = []
					else:
						# the new segment does not fit to the existing candidate
						candidate = []
						candidate.append(seg)
				else:
					# this might be the first arc of an ellipse
					candidate.append(seg)
			else:
				# something different found
				candidate = []
			
		self.m_segments = [x for x in self.m_segments if x not in toRemove]
		return ellipses


	def findMinimalPoint(self, func):
		"""
			Find a point p on me, so that func(p) has a minimal value.
			func must return a number.
			Returns a list: [segment, point, segParameter, value]
		"""
		ret = []
		minF = 1000000000
		for seg in self.m_segments:
			test = seg.findMinimalPoint(func)
			if test[-1] < minF:
				minF = test[-1]
				ret = test
		return ret


	def findNearestPoint(self, point):
		myLambda = lambda p: p.distanceOfPoint(point)
		testArr = self.findMinimalPoint(myLambda)
		return testArr


	def findAllPointsOnPath(self, func):
		"""
			Return a list of points of me, where func(p) is 0 (func(p) must be >= 0)
			Returns a list of lists: [segment, point, segParameter, value]
		"""
		ret = []
		for seg in self.m_segments:
			theList = seg.findMinimalPoint(func)
			if ZGeomItem.almostZero(theList[3]):
				ret.append(theList)
		return ret


	def containsPoint(self, point):
		testArr = self.findNearestPoint(point)
		myPoint = testArr[1]
		return myPoint.isSameAs(point)


	def xmlAddTo(self, parent, tag='path'):
		path = ET.SubElement(parent, tag)
		path.set('closed', str(self.isClosed()))
		path.set('clockwise', str(self.isClockwise()))
		for seg in self.m_segments:
			seg.xmlAddTo(path)


	def cncFriendly(self, tolerance):
		ret = ZPath()
		for seg in self.m_segments:
			cncList = seg.cncFriendly(tolerance)
			for c in cncList:
				ret.addSegment(c)
		return ret


	def cncFriendlySimple(self):
		ret = ZPath()
		for seg in self.m_segments:
			cncList = seg.cncFriendlySimple()
			for c in cncList:
				ret.addSegment(c)
		return ret


	def asNurbsDescription(self) -> list[list[Point]]:
		"""
			Return a list of lists of control points, from which one can make a nurbs curve.
			Currently only implemented for Bezier3 curves.
		"""
		ret = []
		for seg in self.m_segments:
			ret.append(seg.asNurbsDescription())
		return ret
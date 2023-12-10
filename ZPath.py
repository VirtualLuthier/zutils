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

from zutils.ZGeom import Point, Polygon, Line, Circle2, Ellipse3, ZGeomItem, Plane, Cube
from zutils.ZMatrix import Matrix, Affine
#from zutils.ZGeomHelper import vectorAngle2		#, calculateArcEllipse
#from zutils.shame import searchForEllipseCenter


#########################################################
#########################################################


class ZPathSegment:
	"""
		Abstract superclass of segments, handles general tasks
	"""
	def __init__(self, start, stop):
		start.checkIsLegal()	# is it defined?
		stop.checkIsLegal()

		self.m_start = start
		self.m_stop = stop

		self.m_normal = None


	def reverse(self):
		"""
			Change myself, so i am reversed
		"""
		p1 = self.m_start
		p2 = self.m_stop
		self.m_start = p2
		self.m_stop = p1


	def reversed(self):
		'''
			Return a copy of me that is reversed
		'''
		ret = self.copy()
		ret.reverse()
		return ret
	

	def getSimpleBoundingBox(self):
		'''
			return a cube that simply contains my start and stop points. 
		'''
		#Min = self.m_start.min(self.m_stop)
		#Max = self.m_start.max(self.m_stop)
		return Cube.makeCubeFromPoints([self.m_start, self.m_stop])
		#return Cube(Min, Max)


	def setStandardNormal(self):
		tangent = self.tangentAtParam(0)
		second = self.secondDerivativeAtParam(0)
		self.m_normal = tangent.crossProduct(second)


	def isFlat(self):
		if not self.m_start.isFlat():
			return False
		if not self.m_stop.isFlat():
			return False
		return True


	def makeFlat(self):
		'''
			will be overridden by some subclasses
		'''
		self.m_start.m_z = 0
		self.m_stop.m_z = 0


	def getParameterRange(self):
		"""
			Return an array of 3 values for my parameter range, and difference
			no longer overridden in subclass ZArcSegment
		"""
		return [0, 1, 1]


	#def copy(self):
	#	raise Exception('not implemented copy() in class: ' + self.__class__.__name__)


	#def transformBy(self, affine):
	#	"""
	#		Transform myself. Return nothing
	#	"""
	#	raise Exception('not implemented transformBy() in class: ' + self.__class__.__name__)


	def transformedBy(self, affine):
		"""
			Return a copy of myself, that describes me transformed
		"""
		val = self.copy()
		val.transformBy(affine)
		return val


	def getAllInterPoints(self, paramStep, addLast=True):
		"""
			return list of all points with this parameter step
		"""
		#print('--------------------------------------------------------------')
		points = []
		#print('in getAllInterPoints')
		param = 0
		while param <= 1:
			points.append(self.pointAtParam(param))
			param += paramStep
		if addLast and (param < 1 - ZGeomItem.s_wantedAccuracy):
			points.append(self.pointAtParam(1))
		return points



	def getAllInterPointsWithTangent(self, paramStep, addLast=True):
		"""
			get interpoints and tangents
			Return array of tuples (each one contains point and derivative)
		"""
		#print('--------------------------------------------------------------')
		ret = []
		param = 0
		#print('in getAllInterPointsWithTangent')
		while param <= 1:
			point = self.pointAtParam(param)
			tangent = self.tangentAtParam(param)
			ret.append((point, tangent))
			param += paramStep
		if addLast and (param < 1 - ZGeomItem.s_wantedAccuracy):
			ret.append((self.pointAtParam(1), self.tangentAtParam(1)))

		return ret
	
	def getOscilatingCircleAtParam(self, param):
			point = self.pointAtParam(param)
			tangent = self.tangentAtParam(param)
			second = self.secondDerivativeAtParam(param)
			return self.osculatingCircle(point, tangent, second)
	

	def getAllInterPointsAndDerivs(self, paramStep, addLast=True) -> list:
		'''
			get a tuple with (point, tangent, osculatingCircles) at all parameters with step _offset
		'''
		ret = []
		param = 0
		while param <= 1:
			point = self.pointAtParam(param)
			tangent = self.tangentAtParam(param)
			second = self.secondDerivativeAtParam(param)
			oscul = self.osculatingCircle(point, tangent, second)
			ret.append((point, tangent, oscul))
			param += paramStep
		if addLast and (param < 1 - ZGeomItem.s_wantedAccuracy):
			ret.append((self.pointAtParam(1), self.tangentAtParam(1), self.secondDerivativeAtParam(1)))
		return ret
	

	def osculatingCircle(self, point, tangent, second):
		leng = tangent.length()
		k = tangent.crossProduct(second).length() / (leng * leng * leng)
		if ZGeomItem.almostZero(k):
			return None
		if self.m_normal is None:
			normal = self.getOsculatingNormal(tangent, second)
		else:
			normal = self.m_normal
		rad = 1.0 / k
		#print(f'rad: {rad}, must guess the plane, currently works only for flat segments')
		#normal = Point(0, 0, -1)
		toCenter = normal.crossProduct(tangent)
		toCenter = toCenter.scaledTo(rad)
		center = point + toCenter
		return Circle2(center, rad)


	def pointsAreNear(self, p1, p2):
		"""
			Tries to estimate, if the points are near, relative to my own size
		"""
		return self.distanceIsSmall(p1.distanceOf(p2))


	def distanceIsSmall(self, distance):
		"""
			Tries to estimate, if the distance is nectectably small, relative to my own size
		"""
		len = self.m_start.distanceOf(self.m_stop)
		return ZGeomItem.almostZero(distance / len)


	def paramForPoint(self, point, complain=True):
		"""
			Return the parameter that fits to the given point (or math.nan, if point is not on me)
		"""
		arr = self.findNearestPoint(point)
		dist = arr[3]
		error = dist
		if self.distanceIsSmall(error):
			return arr[2]
		if complain:
			raise Exception(f'point does not lie on curve, error = {error}')
		return math.nan



	def findMinimalPoint(self, func):
		"""
			Find a point p on me, so that func(p) has a minimal value.
			func must return a number.
			Returns a list: [segment, point, segParameter, value]
		"""
		(tStart, tStop, tDelta) = self.getParameterRange()
		numSteps = 200
		diff = tDelta / float(numSteps)
		fMin = 1000000000
		tMin = math.nan

		for step in range(numSteps):
			t = tStart + step * diff
			test = self.pointAtParam(t)
			fTest = func(test)
			if fTest < fMin:
				fMin = fTest
				tMin = t

		# also test my "stop" point:
		fTest = func(self.pointAtParam(tStop))
		if fTest < fMin:
			fMin = fTest
			tMin = tStop

		# finally use interval nesting:
		low = max(tStart, tMin - diff)
		upp = min(tMin + diff, tStop)
		diff = upp - low
		pLow = self.pointAtParam(low)
		fLow = func(pLow)
		while abs(diff) > 1e-10:			#	0.0000000001:
			pLow = self.pointAtParam(low)
			pUpp = self.pointAtParam(upp)
			fLow = func(pLow)
			fUpp = func(pUpp)
			diff /= 2.0
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


	def asPolygon(self, numPoints):
		"""
			Return an array of Line segments that approximate myself. No precision given
		"""
		ps = self.getAllInterPoints(1 / numPoints)
		ret = ZPath()
		lastPoint = None

		for p1 in ps:
			if lastPoint is not None:
				line = ZLineSegment(lastPoint, p1)
				ret.addSegment(line)
			lastPoint = p1

		return ret


	def cncFriendly(self, tolerance):
		"""
			Return an array of Line-or-Arc segments that approximate myself
		"""
		if tolerance == 0:
			raise Exception('cncFriendly(): tolerance 0 is not possible')
		numPoints = 1000
		ps = self.getAllInterPointsAndDerivs(1 / numPoints)
		ret = []
		segPoints = []
		isInLine = False

		for (p1, tangent, circle) in ps:
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
				newCircle = ZPathSegment.isAcceptableCncTolerance(segPoints, currentCircle, tolerance)
				if newCircle is not None:
					currentCircle = newCircle
				else:
					# we need a new segment, first finish the current
					segPoints.pop()
					ZPathSegment.addOneCncSegment(ret, segPoints, currentCircle)
					last = segPoints.pop()			
					segPoints = []
					segPoints.append(last)
					segPoints.append(p1)

		#print('one segment done')
		if len(segPoints) > 1:
			if isInLine:
				ZPathSegment.addOneLine(ret, segPoints)
			else:
				self.addOneCncSegment(ret, segPoints, currentCircle)
		return ret
	

	# def cncFriendlyObsolete(self, tolerance):
	# 	"""
	# 		Return an array of Line-or-Arc segments that approximate myself
	# 	"""
	# 	if tolerance == 0:
	# 		raise Exception('cncFriendly(): tolerance 0 is not possible')
	# 	numPoints = 1000
	# 	ps = self.getAllInterPoints(1 / numPoints)
	# 	ret = []
	# 	segPoints = []
	# 	isInLine = False

	# 	for p1 in ps:
	# 		segPoints.append(p1)
	# 		segLen = len(segPoints)
	# 		if segLen < 3:
	# 			continue
	# 		if segLen == 3:
	# 			currentCircle = Circle2.circleFromThreePoints(segPoints[0], segPoints[1], segPoints[2])
	# 			if currentCircle is None:
	# 				isInLine = True
	# 			continue

	# 		# ok, we have more than 3 points
	# 		if isInLine:
	# 			if ZPathSegment.isStillInLine(segPoints, tolerance):
	# 				continue
	# 			segPoints.pop()
	# 			ZPathSegment.addOneLine(ret, segPoints)
	# 			last = segPoints.pop()
	# 			segPoints = []
	# 			segPoints.append(last)
	# 			segPoints.append(p1)
	# 			isInLine = False
	# 		else:
	# 			newCircle = ZPathSegment.isAcceptableCncTolerance(segPoints, currentCircle, tolerance)
	# 			if newCircle is not None:
	# 				currentCircle = newCircle
	# 			else:
	# 				# we need a new segment, first finish the current
	# 				segPoints.pop()
	# 				ZPathSegment.addOneCncSegment(ret, segPoints, currentCircle)
	# 				last = segPoints.pop()			
	# 				segPoints = []
	# 				segPoints.append(last)
	# 				segPoints.append(p1)

	# 	#print('one segment done')
	# 	if len(segPoints) > 1:
	# 		if isInLine:
	# 			ZPathSegment.addOneLine(ret, segPoints)
	# 		else:
	# 			self.addOneCncSegment(ret, segPoints, currentCircle)
	# 	return ret	


	@classmethod
	def addOneCncSegment(cls, segList, segPoints, currentCircle):
		"""
			Adds a line or arc segment, that fits throuh the segPoints list to the given segList
		"""
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
				# only for debugging:
				stPoint = segPoints[0]
				if ZGeomItem.almostZero(stPoint.m_x - 98.86255480000004):
					print ('debug me')
				# end debug statements
				newSeg = ZArcSegment.createZArcFromSvg(rad, rad, 0, segPoints[0], segPoints[-1], False, poly.isClockWise(Point(0, 0, 1)))
		#newSeg.printComment('newly added to cncfriendly')
		segList.append(newSeg)


	@classmethod
	def addOneLine(cls, segList, segPoints):
		segList.append(ZLineSegment(segPoints[0], segPoints[-1]))


	@classmethod
	def isAcceptableCncTolerance(cls, points, currentCircle, tolerance, step=1):
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
			return cls.isAcceptableCncTolerance(points, newCircle, tolerance, step=2)
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


	# def getAllInterPointsAndStop(self, paramStep):
	# 	'''
	# 		return according list and add self.m_stop, if needed
	# 	'''
	# 	ret = self.getAllInterPoints(paramStep)
	# 	last = ret[-1]
	# 	if not last.isSameAs(self.m_stop):
	# 		ret.append(self.m_stop)
	# 	return ret


###########################################################
###########################################################


class ZLineSegment(ZPathSegment):
	"""
		A line between 2 points
	"""

	def __init__(self, p1, p2):
		super().__init__(p1, p2)
		self.m_bernsteinPoints = []
		self.recalculateGeometry()


	def recalculateGeometry(self):
		self.m_bernsteinPoints.append(self.m_stop - self.m_start)
		self.m_bernsteinPoints.append(self.m_start)
		self.setStandardNormal()


	def copy(self):
		# caution: does not copy the points
		return ZLineSegment(self.m_start, self.m_stop)


	def transformBy(self, affine):
		self.m_start = affine * self.m_start
		self.m_stop = affine * self.m_stop


	def getAllInterPoints(self, _):
		return [self.m_start, self.m_stop]


	def getAllInterPointsWithTangent(self, _):
		tang = self.m_stop - self.m_start
		m1 = (self.m_start, -tang)
		m2 = (self.m_stop, -tang)
		return [m1, m2]


	def getInterPointWithTangent(self, _):
		tang = self.m_stop - self.m_start
		return (self.m_start, -tang)
	

	def getAllInterPointsAndDerivs(self, _offset) -> list:
		'''
			get a tuple with (point, tangent, osculatingCircles) at all parameters with step _offset
		'''
		tang = self.m_stop - self.m_start
		m1 = (self.m_start, -tang, None)
		m2 = (self.m_stop, -tang, None)
		return [m1, m2]


	def printComment(self, comment, tabs=1, rounded=2):
		super().printComment(comment, tabs, rounded)

		print(')')


	def svgCode(self, rounded):
		ret = 'L '
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


	def pointAtParam(self, t):
		'''
			return the point that is given by the param
		'''
		#return self.m_start + (self.m_stop - self.m_start).scaledBy(t)
		return self.m_bernsteinPoints[0].scaledBy(t) + self.m_bernsteinPoints[1]
	

	def tangentAtParam(self, _):
		'''
			return the tangent direction through the point that is given by the param
		'''
		#return self.m_stop - self.m_start
		return self.m_bernsteinPoints[0]


	def secondDerivativeAtParam(self, _):
		'''
			return the second derivation direction through the point that is given by the param
		'''
		return Point()


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
	#s_bernsteinFunctions = {}
	#s_bernsteinDerivationsOne = {}

	def __init__(self, p1, p2, h1, h2):
		super().__init__(p1, p2)
		self.m_handleStart = h1
		self.m_handleStop = h2
		self.m_bernsteinPoints = []
		self.recalculateGeometry()


	def recalculateGeometry(self):
		'''
			calcuate the bernstein points for calculation of points and derivatives
			also recalculate my normal
		'''
		self.m_bernsteinPoints = []
		p1 = self.m_start
		p2 = self.m_stop
		h1 = self.m_handleStart
		h2 = self.m_handleStop

		self.m_bernsteinPoints.append((h1 - h2).scaledBy(3) + p2 - p1)			# C0 for t**3
		self.m_bernsteinPoints.append((p1 + h2).scaledBy(3) - h1.scaledBy(6))	# C1 for t**2
		self.m_bernsteinPoints.append((h1 - p1).scaledBy(3))					# C2 for t**1
		self.m_bernsteinPoints.append(p1)										# C4 for t**0
		## quadratic curve between p1, h1, h2:
		#x1 = p1 - h1.scaledBy(2) + h2
		#x2 = (h1 - p1).scaledBy(2)
		## quadratic curve between h1, h2, p2
		#y1 = h1 - h2.scaledBy(2) + p2
		#y2 = (h2 - h1).scaledBy(2)
		## now combine x1, x2, y1, y2 for the cubic bezier
		#self.m_bernsteinPoints.append(y1 - x1)				# for t**3
		#self.m_bernsteinPoints.append(x1 - x2 + y2)			# for t**2
		#self.m_bernsteinPoints.append(x2 - p1 + h1)			# for t
		#self.m_bernsteinPoints.append(p1)					# constant

		# now calculate the normal for the osculating circles (makes only sense, if I am lying in a plane)
		plane = Plane(p1, h1, p2)
		if plane.containsPoint(h2):
			# check, if we have a turning point:
			t1 = self.m_start
			t2 = self.m_handleStart
			t3 = self.m_handleStop
			n1 = (t2 - t1).crossProduct(t3 - t1).unit()
			#print('-----------------')
			#n1.printComment('n1')
			t1, t2, t3 = t2, t3, self.m_stop
			n2 = (t2 - t1).crossProduct(t3 - t1).unit()
			#n2.printComment('n2')
			if n1.isSameAs(n2):
				# ok, we have no turning point:
				self.setStandardNormal()


	def getSimpleBoundingBox(self):
		'''
			return a cube that simply contains my start and stop points and my handles 
		'''
		return Cube.makeCubeFromPoints(
			[self.m_stop,
			self.m_start,
			self.m_handleStart,
			self.m_handleStop])
		# Min = self.m_start.min(self.m_stop)
		# Max = self.m_start.max(self.m_stop)
		# Min = Min.min(self.m_handleStart)
		# Min = Min.min(self.m_handleStop)
		# Max = Max.max(self.m_handleStart)
		# Max = Max.max(self.m_handleStop)
		# return Cube(Min, Max)


	@classmethod
	def makeTwoPointsConnection(cls, start: Point, tangentStart: Point, stop: Point, tangentStop: Point, stiffnessStart:float=0.5, stiffnessStop:float= 0.5) ->ZBezier3Segment:
		if stiffnessStart > 0.9 > stiffnessStop > 0.9:
			raise Exception('ZBezier3Segment:makeTwoPointsConnection(): stiffnessess must be <= 0.9')
		dist = start.distanceOfPoint(stop)
		handle1 = start + tangentStart.scaledTo(dist * stiffnessStart)
		handle2 = stop + tangentStop.scaledTo(dist * stiffnessStop)
		return ZBezier3Segment(start, stop, handle1, handle2)


	def isFlat(self):
		if not super().idFlat():
			return False
		if not self.m_handleStart.isFlat():
			return False
		if not self.m_handleStop.isFlat():
			return False
		return True


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


	def pointAtParam(self, t):
		'''
			return the point that is given by the param
		'''
		a = self.m_bernsteinPoints
		return a[0].scaledBy(t*t*t) + a[1].scaledBy(t*t) + a[2].scaledBy(t) + a[3]
	

	def tangentAtParam(self, t):
		'''
			return the tangent direction through the point that is given by the param
		'''
		a = self.m_bernsteinPoints
		return a[0].scaledBy(3*t*t) + a[1].scaledBy(2*t) + a[2]
	

	def secondDerivativeAtParam(self, t):
		'''
			return the second derivation direction through the point that is given by the param
		'''
		a = self.m_bernsteinPoints
		return a[0].scaledBy(6*t) + a[1].scaledBy(2)
	

	def getOsculatingNormal(self, tangent, second):
		'''
			I must return the normal of the osculation point. Is only called for segments that use several planes or have a turning point
		'''
		#print('ZBezier3Segment::getOsculatingNormal: please test for correctness!')
		return tangent.crossProduct(second)


	def interpolate(self, p1, p2, t):
		diff = (p2 - p1).scaledBy(t)
		return p1 + diff


	def reverse(self):
		super().reverse()
		h1 = self.m_handleStart
		h2 = self.m_handleStop
		self.m_handleStart = h2
		self.m_handleStop = h1
		self.recalculateGeometry()


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
		self.recalculateGeometry()


	def xmlAddDetailsTo(self, node):
		node.set('handleStart', self.m_handleStart.xmlCoords())
		node.set('handleStop', self.m_handleStop.xmlCoords())


	def isClockWise(self):
		# seen from (0, 0, 1)
		points = [self.m_start, self.m_handleStart, self.m_handleStop, self.m_stop]
		poly = Polygon(points)
		return poly.isClockWise(Point(0, 0, 1))


	def asNurbsDescription(self) -> list[Point]:
		"""
			Return a list of control points that make a nurbs description of me
		"""
		return [self.m_start, self.m_handleStart, self.m_handleStop, self.m_stop]
	

########################################################
########################################################


class ZBezier2Segment(ZPathSegment):
	"""
		a quadratic bezier segment
	"""
	def __init__(self, p1, p2, handle):
		super().__init__(p1, p2)
		self.m_handle = handle
		self.m_bernsteinPoints = []
		self.recalculateGeometry()



	def recalculateGeometry(self):
		p1 = self.m_start
		p2 = self.m_stop
		handle = self.m_handle
		self.m_bernsteinPoints = []
		self.m_bernsteinPoints.append(p1 - handle.scaledBy(2) + p2)
		self.m_bernsteinPoints.append((handle - p1).scaledBy(2))
		self.m_bernsteinPoints.append(p1)

		#self.m_normal = Plane(p1, handle, p2).m_normal
		self.setStandardNormal()


	def getSimpleBoundingBox(self):
		'''
			return a cube that simply contains my start and stop points and my handle
		'''
		return Cube.makeCubeFromPoints(
			[self.m_stop,
			self.m_start,
			self.m_handle])
		# Min = Min.min(self.m_handle)
		# Min = self.m_start.min(self.m_stop)
		# Max = self.m_start.max(self.m_stop)
		# Min = Min.min(self.m_handle)
		# Max = Max.max(self.m_handle)
		# return Cube(Min, Max)


	def reverse(self):
		p1 = self.m_start
		p2 = self.m_stop
		self.m_start = p2
		self.m_stop = p1
		self.recalculateGeometry()


	@classmethod
	def makeTwoPointsConnection(cls, start, tangent, stop, stiffness=0.5):
		if stiffness > 0.9:
			raise Exception('ZBezier2Segment:makeTwoPointsConnection(): stiffness must be <= 0.9')
		dist = start.distanceOfPoint(stop)
		handle = start + tangent.scaledTo(dist * stiffness)
		return ZBezier2Segment(start, stop, handle)


	def isFlat(self):
		if not super().idFlat():
			return False
		if not self.m_handle.isFlat():
			return False
		return True


	def makeFlat(self):
		super().makeFlat()
		self.m_handle.m_z = 0
	

	def pointAtParam(self, t):
		'''
			return the point that is given by the param
		'''
		return self.m_bernsteinPoints[0].scaledBy(t*t) + self.m_bernsteinPoints[1].scaledBy(t) + self.m_bernsteinPoints[2]
	

	def tangentAtParam(self, t):
		'''
			return the tangent direction through the point that is given by the param
		'''
		return self.m_bernsteinPoints[0].scaledBy(2*t) + self.m_bernsteinPoints[1]
	

	def secondDerivativeAtParam(self, t):
		'''
			return the second derivation direction through the point that is given by the param
		'''
		return self.m_bernsteinPoints[0].scaledBy(2)


	def interpolate(self, p1, p2, t):
		diff = (p2 - p1).scaledBy(t)
		return p1 + diff


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
		self.recalculateGeometry()


	def xmlAddDetailsTo(self, node):
		node.set('handle', self.m_handle.xmlCoords())


	def isClockWise(self):
		# seen from (0, 0, 1)
		points = [self.m_start, self.m_handle, self.m_stop]
		poly = Polygon(points)
		return poly.isClockWise(Point(0, 0, 1))
	

	def svgCode(self, rounded):
		ret = 'Q '
		ret += ZPathSegment.pointString(self.m_handle, rounded)
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


####################################################
####################################################


class ZArcSegment(ZPathSegment):
	"""
		an svg arc segment. In 2d it matches the svg arc. Can also be used in 3d,
		BUT: it can only be transformed by orthogonal matrixes reliably. 
	"""
	def __init__(self, p1, p2, ellipse3, largeArc, clockWise=None):
		super().__init__(p1, p2)
		
		self.m_largeArc = largeArc
		self.m_clockWise = clockWise
		self.adaptToEllipse(ellipse3)		
		

	def adaptToEllipse(self, ellipse3):
		self.m_ellipse = ellipse3
		self.m_center = ellipse3.m_center
		(rx, ry) = ellipse3.getRadii()
		self.m_rx = rx
		self.m_ry = ry
		self.m_startAngle = self.m_ellipse.angleForPoint(self.m_start)

		self.m_stopAngle = self.m_ellipse.angleForPoint(self.m_stop)
		if self.m_stopAngle is None or self.m_startAngle is None:
			raise Exception('ZArcSegment::adaptToEllipse brings illegal start/stop Angle')
		delta = ZGeomItem.normalizeAngle(self.m_stopAngle - self.m_startAngle)
		self.m_deltaAngle = delta
		largeArc = self.m_largeArc
		if self.isHalfEllipse() and self.m_clockWise is not None:
			self.m_deltaAngle = 180
			if self.isClockWise() != self.m_clockWise:
				delta = -180
		elif (delta < 180 and largeArc) or (delta > 180 and not largeArc):
			delta = 360 - delta
		
		if not ZGeomItem.almostEqualAngles(self.m_startAngle + delta, self.m_stopAngle):
			delta = -delta

		self.m_deltaAngle = delta

		self.setStandardNormal()
		#normal = self.m_ellipse.getNormale()
		#if self.m_deltaAngle < 0:
		#	normal = - normal
		#self.m_normal = normal

		self.selfTest()


	# @classmethod
	# def createZArcFromSvgObsolete(cls, rx, ry, axisAngle, p1, p2, largeArcFlag, sweepFlagClockWise):
	# 	'''
	# 		create a 2-d ZArcSegment from the svg path arguments
	# 	'''
	# 	largeArc = True if largeArcFlag else False
	# 	sweepClockWise = True if sweepFlagClockWise else False

	# 	#affine = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), - axisAngle)
	# 	#p1X = affine*p1
	# 	#p2X = affine*p2
	# 	circle3 = cls.calculateArcEllipse(rx, ry, p1, p2, largeArc, sweepClockWise, phi=axisAngle)

	# 	ret = ZArcSegment(p1, p2, circle3, largeArc, sweepFlagClockWise)
		
	# 	# rotate ret back to real position:
	# 	#affInverse = affine.inverted()
	# 	#ret.transformBy(affInverse)
	# 	return ret
	

	@classmethod
	def createZArcFromSvg(cls, rx, ry, axisAngle, p1, p2, largeArcFlag, sweepFlagClockWise):
		'''
			create a 2-d ZArcSegment from the svg path arguments
		'''
		largeArc = True if largeArcFlag else False
		sweepClockWise = True if sweepFlagClockWise else False

		affine = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), - axisAngle)
		p1X = affine*p1
		p2X = affine*p2
		circle3 = cls.calculateArcEllipse(rx, ry, p1X, p2X, largeArc, sweepClockWise)

		ret = ZArcSegment(p1X, p2X, circle3, largeArc, sweepFlagClockWise)
		
		# rotate ret back to real position:
		affInverse = affine.inverted()
		ret.transformBy(affInverse)
		return ret
	

	def getSimpleBoundingBox(self):
			return Cube.makeCubeFromPoints([
				self.m_start, self.m_stop, self.m_center,
				self.m_ellipse.m_vert1, self.m_ellipse.m_vert2])


	def containsPoint(self, point):
		return self.m_ellipse.containsPoint(point)
	

	def isFlat(self):
		if not super().isFlat():
			return False
		if not self.m_center.isFlat():
			return False
		return True


	# def getParameterRange(self):		# also ZarcSegment uses now 0 <= t <= 1 !!!!!!!!!!!!!!!!!!!!!!!!!!
	# 	"""
	# 		Return an array of 3 values for my parameter range and delta
	#  		Overrides same method in ZPathSegment
	# 	"""
	# 	print('also doch ==================')
	# 	if math.isnan(self.m_startAngle) or math.isnan(self.m_stopAngle):
	#  		# if they are not defined, we search over the whole ellipse
	# 		return [0, 360, 360]
	# 	return [self.m_startAngle, self.m_stopAngle, self.m_deltaAngle]
	

	def isHalfEllipse(self):
		return ZGeomItem.almostEqual(abs(self.m_deltaAngle), 180)


	def selfTest(self):
		"""
			Check the internal consistency
		"""
		if not self.containsPoint(self.m_start) or not self.containsPoint(self.m_stop):
			raise Exception('ZArcSegment:selfTest error: start/stop problem')

		if not ZGeomItem.almostEqualAngles(self.m_stopAngle, self.m_startAngle + self.m_deltaAngle):
			self.printComment('Arc')
			cand = ZGeomItem.normalizeAngle(self.m_startAngle + self.m_deltaAngle)
			msg = f'ZArcSegment:selfTest error: angle problem {self.m_stopAngle} vs. {cand}'
			raise Exception(msg)

		startA = self.m_startAngle
		pStart = self.pointAtAngle(startA)
		pStop = self.pointAtAngle(self.m_stopAngle)
		#if not pStart.isSameAs(self.m_start) or not pStop.isSameAs(self.m_stop):
		if not self.pointsAreNear(pStart, self.m_start) or not self.pointsAreNear(pStop, self.m_stop):
			raise Exception('ZArcSegment:selfTest error: parameter problem')
		
		if self.isHalfEllipse() and self.m_clockWise is None:
			raise Exception('ZArcSegment:selfTest error: for 180 degrees clockWise must be given')


	@classmethod
	def createFullCircle2(cls, center, radius, clockwise):
		'''
			Create a path with a full circle in 2d, made from 4 arcs
		'''
		return cls.createFullEllipse(center, radius, radius, 0, clockwise)


	@classmethod
	def createFullEllipse2(cls, center, radiusX, radiusY, angle, clockwise):	
		'''
			Create a path with a full ellipse in 2d, made from 4 arcs
		'''
		
		diffX = Point(radiusX)
		diffY = Point(0, radiusY)
		if not clockwise:
			diffX = - diffX
		rotLine = Line(center, center + Point(0, 0, 1))
		aff = Affine.makeRotationAffine(rotLine, angle)
		diffX = aff * diffX
		diffY = aff * diffY
		
		p1 = center + diffX
		p3 = center - diffX
		p2 = center + diffY
		p4 = center - diffY

		ellipse = Ellipse3(center, diam1=diffX, diam2=diffY)
		ret = ZPath()
		ret.addSegment(ZArcSegment(p1, p2, ellipse.copy(), False))
		ret.addSegment(ZArcSegment(p2, p3, ellipse.copy(), False))
		ret.addSegment(ZArcSegment(p3, p4, ellipse.copy(), False))
		ret.addSegment(ZArcSegment(p4, p1, ellipse.copy(), False))
		return ret


	@classmethod
	def createFullCircleRing(cls, center, radiusOuter, radiusInner):
		'''
			Return a path that describes a ring of 2 circles
		'''
		path1 = cls.createFullCircle(center, radiusOuter, True)
		path2 = cls.createFullCircle(center, radiusInner, False)
		for seg in path2.m_segments:
			path1.addSegment(seg)
		return path1


	@classmethod
	def createFullEllipseRing(cls, center, radiusOuterX, radiusOuterY, radiusInnerX, radiusInnerY, angle):
		'''
			Return a path that describes a ring of 2 circles
		'''
		path1 = cls.createFullEllipse(center, radiusOuterX, radiusOuterY, angle, True)
		path2 = cls.createFullEllipse(center, radiusInnerX, radiusInnerY, angle, False)
		for seg in path2.m_segments:
			path1.addSegment(seg)
		return path1


	def svgCode(self, rounded):
		'''
			return a string that is usable as the d-attribute of a path node
		'''
		ret = 'A '
		rounded = 5
		ret += str(round(self.m_rx, rounded)) + ' '
		ret += str(round(self.m_ry, rounded)) + ' '
		ret += str(round(self.getXAngle(), rounded)) + ' '
		flag = '0'
		if self.m_largeArc:
			flag = '1'
		ret += flag + ' '
		flag = '0'
		if self.isClockWise():
			flag = '1'
		ret += flag + ' '
		ret += ZPathSegment.pointString(self.m_stop, rounded)
		return ret


	def copy(self):
		return ZArcSegment(self.m_start.copy(), self.m_stop.copy(), self.m_ellipse.copy(), self.m_largeArc, self.m_clockWise)


	def printComment(self, comment, tabs=0, rounded=2):
		super().printComment(comment, tabs, rounded)
		tabs = tabs + 1
		ZGeomItem.printNumRounded('rx', self.m_rx, tabs, rounded)
		ZGeomItem.printNumRounded('ry', self.m_ry, tabs, rounded)
		ZGeomItem.printNumRounded('x-angle', self.getXAngle(), tabs, rounded)
		ZGeomItem.printStringTabbed('x-angle', '???', tabs)
		ZGeomItem.printStringTabbed(f'large', str(self.m_largeArc), tabs)
		ZGeomItem.printStringTabbed('clockwise', self.isClockWise(), tabs)
		ZGeomItem.printNumRounded('startAngle', self.m_startAngle, tabs, rounded)
		ZGeomItem.printNumRounded('stopAngle', self.m_stopAngle, tabs, rounded)
		ZGeomItem.printNumRounded('deltaAngle', self.m_deltaAngle, tabs, rounded)
		self.m_ellipse.printComment('ellipse', tabs)


	def isClockWise(self):
		if ZGeomItem.s_originIsTopLeft:
			return self.m_deltaAngle > 0
		return self.m_deltaAngle < 0


	def reverse(self):
		super().reverse()
		if self.m_clockWise is not None:
			self.m_clockWise = not self.m_clockWise
		self.m_ellipse.reverse()
		self.adaptToEllipse(self.m_ellipse)


	def normalizedAngleForPoint(self, point):
		'''
			return the angle between the positive x-axis and (point - center)
		'''
		angle = self.m_ellipse.angleForPoint(point)
		return Point(1).angleTo(point)
	

	def angleForParam(self, param):
		if abs(param) > 1:
			msg = f'ZArcSegment: suspicious param used {param}'
			raise Exception(msg)
		return self.m_startAngle + self.m_deltaAngle * param


	def pointAtParam(self, param):
		'''
			return the point that is given by the param
		'''
		return self.m_ellipse.pointForAngle(self.angleForParam(param))
	

	def tangentAtParam(self, param):
		'''
			return the tangent direction through the point that is given by the param
		'''
		ret = self.m_ellipse.tangentForAngle(self.angleForParam(param))
		#if self.m_deltaAngle < 0:
		#	ret = -ret
		return ret.scaledBy(self.m_deltaAngle)
	

	def secondDerivativeAtParam(self, param):
		'''
			return the second derivation direction through the point that is given by the param
		'''
		ret = self.m_ellipse.secondDerivativeForAngle(self.angleForParam(param))
		return ret.scaledBy(self.m_deltaAngle*self.m_deltaAngle)
	

	def pointAtAngle(self, angle):
		return self.m_ellipse.pointForAngle(angle)


	def getBiggerRadius(self):
		'''
			return the greater one of my radii
		'''
		return self.m_ellipse.m_a


	def belongsToSameEllipse(self, otherArc):
		if not self.m_ellipse.isSameAs(otherArc.m_ellipse):
			return False
		return self.isClockWise() == otherArc.isClockWise()


	def transformBy(self, affine):
		'''
			transform myself, return nothing
		'''
		self.m_start = affine * self.m_start
		self.m_stop = affine * self.m_stop
		newEllipse = affine * self.m_ellipse
		if self.m_clockWise is not None:
			if not affine.m_matrix.preservesOrientation:
				self.m_clockWise = not self.m_clockWise
		self.adaptToEllipse(newEllipse)


	def getMyMiddlePoint(self):
		"""
			Return the point on my graph with the middle parameter (angle) value
		"""
		return self.pointAtParam(0.5)


	def getInterPointWithTangent(self, param):
		return self.getPointForParameterWithTangent(param)


	def __str__(self):
		ret = 'ZArcSegment(center=' + str(self.m_center) + ')'
		return ret


	def cncFriendly(self, tolerance):
		"""
			Return an array of Line-or-Arc segments that approximate myself
		"""
		if self.m_ellipse.isCircle():
			return [self.copy()]
		return super().cncFriendly(tolerance)
	
	
	@classmethod
	def vectorAngle2(cls, u, v):
		'''
			return the angle (in degrees) between 2 2d vectors
		'''
		#d = math.hypot(*u) * math.hypot(*v)
		#d = math.hypot(u) * math.hypot(v)
		d = u.length() * v.length()
		if d == 0:
			return 0
		c = (u[0] * v[0] + u[1] * v[1]) / d
		if c < -1:
			c = -1
		elif c > 1:
			c = 1
		s = u[0] * v[1] - u[1] * v[0]
		return math.degrees(math.copysign(math.acos(c), s))


	@classmethod
	def calculateArcEllipse(cls, rx, ry, pStart, pStop, largeArc, sweepClocWise, phi=0): 		# , x1, y1, x2, y2, fA, fS, rx, ry, phi=0):
		'''
		Calculate the ellipse of a arc path segment from the svg arguments
		makes only sense in the x-y-plane (2d)
		Note that we have rotated to be axis parallel (so we reduced phi to zero outside)
		Sorry: the case phi not-zero does not work!!
		See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes F.6.5
		'''

		if abs(phi) > 0:
			raise Exception('ZArcSement::calculateArcEllipse() does not work with phi non-zero!!')

		x1 = pStart.m_x
		y1 = pStart.m_y
		x2 = pStop.m_x
		y2 = pStop.m_y

		fA = 1 if largeArc else 0
		fS = 1 if sweepClocWise else 0

		rx = math.fabs(rx)
		ry = math.fabs(ry)

		# step 1
		if abs(phi) > ZGeomItem.s_wantedAccuracy:
			# this should be obsolete, as we have transformed the ellipse to be axis parallel
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
		#elif r != 0:
		# this might be a little problem: (dont know the exact valid range!!)
		elif abs(r) > ZGeomItem.s_wantedAccuracy / 100:
			r = 1 / r - 1
		#if -1e-10 < r < 0:
		if -ZGeomItem.s_wantedAccuracy < r < 0:
			r = 0
		r = math.sqrt(r)
		if fA == fS:
			r = -r
		cxd = (r * rx * y1d) / ry
		cyd = -(r * ry * x1d) / rx

		# step 3
		##if phi:
		if abs(phi) > ZGeomItem.s_wantedAccuracy:
			cx = cos_phi * cxd - sin_phi * cyd + 0.5 * (x1 + x2)
			cy = sin_phi * cxd + cos_phi * cyd + 0.5 * (y1 + y2)
		else:
			cx = cxd + 0.5 * (x1 + x2)
			cy = cyd + 0.5 * (y1 + y2)

		# step 4 - seems obsolete, as phi is always 0
		#theta1Degrees = cls.vectorAngle2(Point(1, 0), Point((x1d - cxd) / rx, (y1d - cyd) / ry))
		#dtheta = cls.vectorAngle2(
		#	((x1d - cxd) / rx, (y1d - cyd) / ry),
		#	((-x1d - cxd) / rx, (-y1d - cyd) / ry)
		#) % 360
		#if fS == 0 and dtheta > 0:
		#	dtheta -= 360
		#elif fS == 1 and dtheta < 0:
		#	dtheta += 360

		diam1 = Point(rx)
		diam2 = Point(0, ry)

		# this does not work !!
		#if not ZGeomItem.almostZero(phi):
		#	aff = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), phi)
		#	diam1 = aff*diam1
		#	diam2 = aff*diam2

		ellipse3 = Ellipse3(Point(cx, cy), diam1=diam1, diam2=diam2)
		return ellipse3
	

	def getXAngle(self):
		'''
			Return the svg angle between the x axis and my main axis (hopefully correct !!)
		'''
		return self.vectorAngle2(Point(1), self.m_ellipse.m_diam1)



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
		currPos = Point(math.nan, math.nan)
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


	def isClockWise(self):
		# seen from (0, 0, 1)
		points = [x.m_start for x in self.m_segments]
		if len(points) < 3:
			for seg in self.m_segments:
				if type(seg).__name__ == 'ZArcSegment':
					return seg.isClockWise()
				if isinstance(seg, ZBezier3Segment):
					return seg.isClockWise()
			print('cannot get isClockWise() for less than 3 points !!!!!!!!!!!!!!!!!!!!!!!')
			return None
		poly = Polygon(points)
		return poly.isClockWise(Point(0, 0, 1))


	def makeClockWise(self, what=True):
		if self.isClockWise() == what:
			return
		self.reverse()


	def getAllInterPoints(self, paramStep):
		"""
			Return a list of [points with given parameter step width
		"""
		points = []
		for seg in self.m_segments:
			newOnes = seg.getAllInterPoints(paramStep)
			if len(points) > 0 and points[-1].isSameAs(newOnes[0]):
				points.pop()
			points.extend(newOnes)
		return points


	def getAllInterPointsWithTangent(self, paramStep):
		"""
			Return a list of tuples with (point, tangent) with given parameter step width
		"""
		points = []
		for seg in self.m_segments:
			points.extend(seg.getAllInterPointsWithTangent(paramStep))
		return points
	
	
	def getAllInterPointsAndDerivs(self, paramStep):
		"""
			Return a list of tuples with (point, tangent) with given parameter step width
		"""
		points = []
		for seg in self.m_segments:
			points.extend(seg.getAllInterPointsAndDerivs(paramStep))
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
		'''
			just return a Cube that contains all my segemnts' start and stop points
		'''
		segs = self.m_segments
		if len(segs) == 0:
			return Cube(Point(), Point())
		ret = segs[0].getSimpleBoundingBox()
		for ii in range(1, len(segs)):
			ret = ret.combinedWith(segs[ii].getSimpleBoundingBox())
		return ret
	

	def getGreaterBoundingBox():
		'''
			return a rect that contains a senseful area containing most of segments
		'''


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
	

	def isFlat(self):
		for seg in self.m_segments:
			if not seg.isFlat():
				return False
		return True


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
			connectible = 'NOT '
			if self.areSegsConnectable(lastSeg, seg):
				connectible = ''
				
			seg.printComment('segment ' + str(ii), tabs + 1, rounded)
			self.printTabs(tabs + 2)
			print(f'segment is {connectible}connected from previous segment')
			ii = ii + 1

		ZGeomItem.printStringTabbed('path is closed', self.isClosed(), tabs)
		ZGeomItem.printStringTabbed('orientation is clockwise', self.isClockWise(), tabs)


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
								ellipse = Ellipse2(seg.m_center, seg.m_rx, seg.m_ry, seg.getXAngle())
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
		path.set('clockwise', str(self.isClockWise()))
		for seg in self.m_segments:
			seg.xmlAddTo(path)


	def cncFriendly(self, tolerance):
		ret = ZPath()
		for seg in self.m_segments:
			cncList = seg.cncFriendly(tolerance)
			for c in cncList:
				ret.addSegment(c)
		if not ret.areSegsConnected():
			raise Exception('ZPath::cncFriendly created non-connected path')
		return ret


	# was formerly named cncFriendlySimple
	def asPolygon(self, num):
		'''
			return a polygon path for me, where every segment has num lines
		'''
		ret = ZPath()
		for seg in self.m_segments:
			partPath = seg.asPolygon(num)
			for c in partPath.m_segments:
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
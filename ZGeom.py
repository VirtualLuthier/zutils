"""
	Contains several 2d-3d related classes
	- ZGeomItem: abstract superclass, handling also metric/imperial setting
	- Point
	- Cube
	- Rect
	- Circle2
	- Ellipse2
	- Ellipse3
	- Line
	- Plane
	- Polygon
	- Circle3
"""


from __future__ import annotations
from typing import List
import math
import random
from scipy.optimize import minimize_scalar
#from typing_extensions import Annotated

import xml.etree.ElementTree as ET

from zutils.ZUnits import ZUnits


class ZGeomItem:
	"""
		Superclass of all the ZGeom classes. Provides some class methods for equality, rounding and printing.
		Also handles metric/imperial setting
	"""
	s_inchWanted = False
	s_mmAccuracy = 0.001
	s_wantedAccuracy = 0.001
	s_wantedSquaredAccuracy = 0.000001

	@classmethod
	def almostEqual(cls, f1, f2) -> bool:
		"""
			f1, f2 are floats
		"""
		return abs(f1 - f2) < ZGeomItem.s_wantedAccuracy


	@classmethod
	def almostEqualAngles(cls, a1, a2) -> bool:
		"""
			a1, a2 are float angles in degrees
		"""
		if cls.almostEqual(cls.normalizeAngle(a1), cls.normalizeAngle(a2)):
			return True
		return cls.almostEqual(360, abs(a1 - a2))


	@classmethod
	def almostZero(cls, num) -> bool:
		return abs(num) < ZGeomItem.s_wantedAccuracy


	@classmethod
	def almostQuadraticEqual(cls, f1, f2) -> bool:
		return abs(f1 - f2) < ZGeomItem.s_wantedSquaredAccuracy


	@classmethod
	def adaptForInches(cls, inchFlag=True):
		"""
			Set the margins for float comparison to be finer, as lengths in inches are much smaller than in mm.
			But do not set the s_wantedSquaredAccuracy to its theoretical value, but a bit bigger
		"""

		if inchFlag:
			# adapt to inches
			ZGeomItem.s_wantedAccuracy = ZGeomItem.s_mmAccuracy / 25.4
		else:
			# adapt to mm
			ZGeomItem.s_wantedAccuracy = ZGeomItem.s_mmAccuracy
		ZGeomItem.s_inchWanted = inchFlag
		ZGeomItem.s_wantedSquaredAccuracy = ZGeomItem.s_wantedAccuracy * ZGeomItem.s_mmAccuracy			# ZGeomItem.s_wantedAccuracy
		ZUnits.s_isMetric = not inchFlag


	@classmethod
	def transformMMs(cls, mms) -> float:
		if cls.s_inchWanted:
			return mms / 25.4
		return mms


	@classmethod
	def printTabs(cls, tabs):
		"""
			Print the given number of tabs and make no line feed at the end.
		"""

		for _ in range(tabs):
			print('	', end='')


	@classmethod
	def printNumRounded(cls, comment, num, tabs=0, rounded=2):
		"""
			Print the tabs, and then the rounded number
		"""
		cls.printTabs(tabs)
		num = round(num, rounded)
		print(f'{comment}: {str(num)}')


	@classmethod
	def printStringTabbed(cls, comment, stringOrSo, tabs=0):
		"""
			Print the tabs, and then the stringified stringOrSo.
		"""
		cls.printTabs(tabs)
		print(f'{comment}: {str(stringOrSo)}')


	@classmethod
	def normalizeAngle(cls, angle) -> float:
		"""
			Return 0 <= something < 360.
		"""
		if cls.almostZero(angle):
			return 0
		if cls.almostEqual(angle, 360):
			return 0
		while angle >= 360:
			angle = angle - 360
		while angle < 0:
			angle = angle + 360
		return angle


	@classmethod
	def findNearestItem(cls, itemList, otherItem):
		"""
			Return the item from itemList, that is nearest to otherItem
			Hopefully works for points, lines and planes
		"""
		dist = 1000000000
		ret = None
		for item in itemList:
			d = item.distanceOf(otherItem)
			if d < dist:
				dist = d
				ret = item
		return ret


	@classmethod
	def findLowestItem(cls, itemList, funcLambda):
		"""
			Return the item from itemList, that is has the lowest funcLamda value
			Hopefully works for points, lines and planes
		"""
		dist = 1000000000
		ret = None
		for item in itemList:
			d = funcLambda(item)
			if d < dist:
				dist = d
				ret = item
		return ret


	@classmethod
	def solveQuadratic(cls, a, b, c):
		"""
			Solve the standard quadratic equation
		"""
		if cls.almostZero(a) and cls.almostZero(b):
			return []
		if cls.almostZero(a):
			return [-c / b]
		disk = b*b - 4*a*c
		if cls.almostZero(disk):
			return [-b / (2.0*a)]
		if disk < 0:
			return []
		root = math.sqrt(disk)
		return [(-b+root) / (2.0*a), (-b-root) / (2.0*a)]


##########################################
##########################################


class Point(ZGeomItem):
	"""
		A point in 3d. Sometimes there is no clear distinction to Vectors.
	"""
	def __init__(self, x=0.0, y=0.0, z=0.0):
		super().__init__()
		self.m_x = x
		self.m_y = y
		self.m_z = z


	@classmethod
	def randomPoint(cls) -> Point:
		"""
			Return a random point with coordinates between -10 and 10
		"""
		x = random.uniform(-10.0, 10.0)
		y = random.uniform(-10.0, 10.0)
		z = random.uniform(-10.0, 10.0)
		return Point(x, y, z)


	@classmethod
	def pointWithAngle(cls, angle) -> Point:
		"""
			Return a point in x-y-plane with length 1 and correct angle to positive x axis
		"""
		ang = math.radians(angle)
		return Point(math.cos(ang), math.sin(ang))


	@classmethod
	def checkMutuallyPerpendicular(cls, pointList) -> list:
		"""
			Return list of 2 vectors found in the pointlist that are not perpendicular, or None.
		"""
		for ii in range(len(pointList) - 1):
			point = pointList[ii]
			for jj in range(ii + 1, len(pointList)):
				point2 = pointList[jj]
				if not point.isPerpendicular(point2):
					return [ii, jj]
		return None


	@classmethod
	def getUnitAlongAxis(cls, axis) -> Point:
		if not axis in 'xyz':
			raise Exception('illegal axis given: (' + str(axis) + ')')
		if axis == 'x':
			return Point(1)
		elif axis == 'y':
			return Point(0, 1)
		return Point(0, 0, 1)


	@classmethod
	def xmlAddPointList(cls, parent, pointArr, tag='points'):
		pointsNode = ET.SubElement(parent, tag)
		for point in pointArr:
			pointNode = ET.SubElement(pointsNode, 'point')
			pointNode.set('coords', point.xmlCoords())



	#def isWellDefined(self):
	#	for ii in range(3):
	#		if math.isnan(self[ii]):
	#			raise Exception('point is not well defined')


	def expandToOrthonormalBase(self) -> List[Point]:
		"""
			Return an arbitrary ortonormal base of R3 that contains me (as unit())
		"""
		ret1 = self.unit()
		line = Line(Point(), ret1)
		otherLine = line.anyPerpendicularLineThrough(Point())
		ret2 = otherLine.m_direction.unit()
		ret3 = ret1.crossProduct(ret2).unit()
		return [ret1, ret2, ret3]


	def xmlCoords(self) -> str:
		st = str(self.m_x) + '|'
		st += str(self.m_y) + '|'
		st += str(self.m_z)
		return st


	def checkIsLegal(self):
		for ii in range(3):
			if math.isnan(self[ii]):
				raise Exception('illegal point')


	def printComment(self, comment, tabs=0, rounded=2):
		"""
			Print a rounded version of myself with a comment
		"""
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(rounded))}')


	def crossProduct(self, other, scaleTo=math.nan) -> Point:
		"""
			Returns a Point, that is orthogonal to me and other - uses orientation
			see https://en.wikipedia.org/wiki/Cross_product#Computing_the_cross_product
		"""
		ax = self.m_x
		ay = self.m_y
		az = self.m_z
		bx = other.m_x
		by = other.m_y
		bz = other.m_z
		ret = Point((ay*bz -az*by), (az*bx - ax*bz), (ax*by - ay*bx))
		if math.isnan(scaleTo):
			return ret
		return ret.scaledTo(scaleTo)


	def unit(self) -> Point:
		"""
			Return a vector in my direction with length 1
		"""
		return self.scaledTo(1.0)


	def length(self) -> float:
		"""
			return the euklidean length of me
		"""
		return math.sqrt(self * self)
		
		
	def lengthSquared(self) -> float:
		"""
			return the square of the length (faster)
		"""
		return self * self


	def __add__(self, other) -> Point:
		"""
			return a point representing the sum of me and other point
		"""
		s = self
		o = other
		return Point(s.m_x + o.m_x, s.m_y + o.m_y, s.m_z + o.m_z)


	def __sub__(self, other) -> Point:
		"""
			return a point representing the difference of me and other point
		"""
		s = self
		o = other
		return Point(s.m_x - o.m_x, s.m_y - o.m_y, s.m_z - o.m_z)


	def __neg__(self) -> Point:
		"""
			return a point representing myself negated
		"""
		return Point(-self.m_x, -self.m_y, -self.m_z)


	def __mul__(self, other) -> float:
		"""
			return a float representing the scalar product of me and other point
		"""
		s = self
		o = other
		return s.m_x * o.m_x + s.m_y * o.m_y + s.m_z * o.m_z


	def __str__(self) -> str:
		"""
			return a string representation of me
		"""
		if self.m_z != 0:
			return 'Point('+str(self.m_x)+', '+str(self.m_y)+', '+str(self.m_z)+')'
		return 'Point('+str(self.m_x)+', '+str(self.m_y)+')'


	def __getitem__(self, key):
		"""
			make myself accessible via index (reading)
		"""
		if key == 0:
			return self.m_x
		if key == 1:
			return self.m_y
		return self.m_z


	def __setitem__(self, key, value):
		"""
			make myself accessible via index (writing)
		"""
		if key == 0:
			self.m_x = value
			return
		if key == 1:
			self.m_y = value
			return
		self.m_z = value


	def __len__(self) -> int:
		"""
			make myself accessible via index (length)
		"""
		return 3


	def flattened(self) -> Point:
		"""
			Return a copy of me with z set to 0
		"""
		ret = self.copy()
		ret.m_z = 0
		return ret


	def rounded(self, num) -> Point:
		"""
			return a point like me, but with rounded coordinates
		"""
		return Point(round(self.m_x, num), round(self.m_y, num), round(self.m_z, num))


	def scaledBy(self, factor) -> Point:
		"""
			return a point like me, but scaled with factor
		"""
		return Point(self.m_x * factor, self.m_y * factor, self.m_z * factor)


	def scaledTo(self, wantedLength) -> Point:
		"""
			return a point like me, but scaled to the wanted length
		"""
		l = self.length()
		if l == 0:
			raise Exception('zero vector has no length')
		return self.scaledBy(wantedLength / l)


	def distanceOf(self, otherItem) -> float:
		return otherItem.distanceOfPoint(self)


	def distanceOfPoint(self, otherItem) -> float:
		return (self - otherItem).length()


	def angleTo(self, otherPoint) -> float:
		"""
			return the angle that I must be rotated, so that the other vector is achieved (positive means CCW)
		"""
		u1 = self.unit()
		u2 = otherPoint.unit()
		cos = u1 * u2
		ret = math.degrees(math.acos(cos))
		return ret



	def isCollinear(self, otherPoint) -> bool:
		return 	ZGeomItem.almostQuadraticEqual(abs(self.unit() * otherPoint.unit()), 1.0)


	def isPerpendicular(self, otherPoint) -> bool:
		return 	ZGeomItem.almostQuadraticEqual(self.unit() * otherPoint.unit(), 0.0)


	def isSameAs(self, otherPoint) -> bool:
		diff = self - otherPoint
		#return 	ZGeomItem.almostQuadraticEqual(diff * diff, 0)
		return 	ZGeomItem.almostZero(diff.length())


	def isZero(self):
		return self.isSameAs(Point())


	def anyPerpendicularPoint(self) -> Point:
		"""
			return any point in the plane that goes through me and is perpendicular to me
		"""
		plane = Plane(Point(), normal=self)
		#now we have to choose one arbitrary point on this plane, that is not = self
		while True:
			while True:
				pt = Point.randomPoint()
				if not self.isCollinear(pt):
					break
			line = Line(self, pt)
			intersect = plane.intersectLine(line)
			if isinstance(intersect, Point):
				return intersect
			if isinstance(intersect, list) and len(intersect) > 0:
				return intersect[0]


	def copy(self) -> Point:
		return Point(self.m_x, self.m_y, self.m_z)


	def mirroredIn(self, idx) -> Point:
		"""
			Return a copy of me, with the coordinate no. idx mirrored
		"""
		w = self[idx]
		ret = self.copy()
		ret[idx] = -w
		return ret


	def max(self, other) -> Point:
		"""
			Return the minimal point that has coordinates >= mine and of other.
		"""
		return Point(max(self.m_x, other.m_x), max(self.m_y, other.m_y), max(self.m_z, other.m_z))


	def min(self, other) -> Point:
		"""
			Return the maximal point that has coordinates <= mine and of other.
		"""
		return Point(min(self.m_x, other.m_x), min(self.m_y, other.m_y), min(self.m_z, other.m_z))


	def __lt__(self, otherPoint) -> bool:
		return self.m_x < otherPoint.m_x and self.m_y < otherPoint.m_y and self.m_z < otherPoint.m_z


	def __le__(self, otherPoint) -> bool:
		return self.m_x <= otherPoint.m_x and self.m_y <= otherPoint.m_y and self.m_z <= otherPoint.m_z


	def __gt__(self, otherPoint) -> bool:
		return otherPoint < self
		#return self.m_x > otherPoint.m_x and self.m_y > otherPoint.m_y and self.m_z > otherPoint.m_z:


	def __ge__(self, otherPoint) -> bool:
		return otherPoint <= self


#############################################################################
#############################################################################


class Cube(ZGeomItem):
	"""
		Cube in 3 dimensions, parallel to axes
	"""
	def __init__(self, p1, p2):
		super().__init__()
		self.m_origin = p1.min(p2)
		self.m_corner = p1.max(p2)


	@classmethod
	def makeCube(cls, origin, width, height, zDiff=0) -> Cube:
		return Cube(origin, origin + Point(width, height, zDiff))


	def containsPoint(self, point) -> bool:
		return self.m_origin <= point <= self.m_corner


	def getHeightY(self) -> float:
		return self.m_corner.m_y - self.m_origin.m_y


	def getWidthX(self) -> float:
		return self.m_corner.m_x - self.m_origin.m_x


	def getDepthZ(self) -> float:
		return self.m_corner.m_z - self.m_origin.m_z


	def __str__(self) -> str:
		return 'Cube(' + str(self.m_origin) + ', ' + str(self.m_corner) + ')'
	

	def printComment(self, comment, tabs=0, num=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(num))}')


	def rounded(self, num=2):

		return Cube(self.m_origin.rounded(num), self.m_corner.rounded(num))


###################################################################
###################################################################


class Rect(Cube):
	"""
		CAUTION: y1 > y2 means: y1 is higher than y2 - this is not normal !!!
		Only useful in x-y-plane. Growing y means higher
		Parallel to axes
		names like "bottom" ... mean "greater y means higher"
	"""
	#def __init__(self, p1, p2):
	#	super().__init__(p1, p2)


	@classmethod
	def makeRect(cls, origin, width, height, zDiff=0) -> Rect:
		return Rect(origin, origin + Point(width, height, zDiff))


	def getBottomLeft(self) -> float:
		return self.m_origin.copy()


	def getBottomRight(self) -> float:
		return self.m_origin + Point(self.getWidthX())


	def getBottomCenter(self) -> float:
		return self.m_origin + Point(self.getWidthX() / 2)


	def getTopCenter(self) -> float:
		return self.m_corner - Point(self.getWidthX() / 2)


	def getTopLeft(self) -> float:
		return Point(self.m_origin.m_x, self.m_corner.m_y)


	def getTopRight(self) -> float:
		return self.m_corner.copy()


	def getTop(self) -> float:
		return self.m_corner.m_y


	def getBottom(self) -> float:
		return self.m_origin.m_y


	def getWidth(self) -> float:
		return abs(self.m_corner.m_x - self.m_origin.m_x)


	def getHeight(self) -> float:
		return abs(self.m_corner.m_y - self.m_origin.m_y)


	def insetBy(self, dist) -> Rect:
		"""
			Return a new Rect that is enlarged by dist
		"""
		return Rect(self.m_origin - Point(dist, dist), self.m_corner + Point(dist, dist))


	def __str__(self) -> str:
		return 'Rect(' + str(self.m_origin) + ', ' + str(self.m_corner) + ')'


##############################################################################
##############################################################################


class Circle2(ZGeomItem):
	"""
		circle in 2-dimensions, x-y
	"""
	def __init__(self, center, radius):
		super().__init__()
		self.m_center = center
		self.m_radius = radius
	

	def printComment(self, comment, tabs=0, num=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(num))}')


	def rounded(self, num=2) -> Circle2:
		return Circle2(self.m_center.rounded(num), round(self.m_radius, num))


	def __str__(self) -> str:
		return f'Circle2({str(self.m_center)}, {str(self.m_radius)})'


	def intersect(self, otherItem) -> list:
		if isinstance(otherItem, Line):
			return self.intersectLine(otherItem)
		return otherItem.intersectCircle(self)

	
	def containsPoint(self, point) -> bool:
		return self.almostEqual(self.m_center.distanceOfPoint(point), self.m_radius)


	def containsInnerPointStrict(self, point) -> bool:
		return self.m_center.distanceOfPoint(point) <= self.m_radius


	def intersectCircle(self, other) -> list:
		"""
			return an array containing 0, 1, or 2 points
		"""
		x1 = self.m_center.m_x
		y1 = self.m_center.m_y
		r1 = self.m_radius
		x2 = other.m_center.m_x
		y2 = other.m_center.m_y
		r2 = other.m_radius
		a = 2*(x2 - x1)
		b = 2*(y2 - y1)
		c = r1*r1 - x1*x1 - y1*y1 - r2*r2 + x2*x2 + y2*y2
		# the intersetion is now on line ax + by = c
		# transform to a line with 2 points p1, p2
		if abs(a) < self.s_wantedAccuracy:
			theY = c/b
			p1 = Point(0, theY)
			p2 = Point(1, theY)
		elif abs(b) < self.s_wantedAccuracy:
			theX = c/a
			p1 = Point(theX, 0)
			p2 = Point(theX, 1)
		else:
			p1 = Point(0, c/b)
			p2 = Point(c/a, 0)
		line = Line(p1, p2)
		#return line.intersectCircle(self)
		return self.intersectLine(line)


	def intersectLine(self, line) -> list:
		#return line.intersectCircle(self)
		r = self.m_radius
		center = self.m_center
		line2 = line.shiftedBy(-center)
		lArr = line2.condenseEquations()
		(_, [c11, c12], _) = lArr

		# we can now assume, that my center is in the origin. The formula is symmetric in x and y. So:
		a = 1 + c11*c11
		b = 2*c11*c12
		c = c12*c12 - r*r

		solutions = ZGeomItem.solveQuadratic(a, b, c)
		points = [line2.getPointForParamSet(lArr, q) for q in solutions]

		return [p + center for p in points]



	def combinedTangentsWith(self, otherCircle):
		# find the 2 tangents, that touch me and otherCircle
		# AND: do not cross between us!
		# return 2 Lines where
		# the first point is the intersection of the tangents
		# the second point is the repective touch point
		c1 = self.m_center
		c2 = otherCircle.m_center
		r1 = float(self.m_radius)
		r2 = float(otherCircle.m_radius)
		factor = r1 / r2
		if  self.almostEqual(factor, 1):
			return None
		distC = c1.distanceOfPoint(c2)
		# distance of tangents intersectionLine from c1:
		x = (distC * r1) / (r2 - r1)
		# tangents intersection point
		tangentsIntersection = c1 + (c1 - c2).scaledTo(x)
		# distance of my tangent points to tangentsIntersection:
		y = math.sqrt(x * x - r1 * r1)
		# now we can calculate the tangent points of me:
		helpCircle = Circle2(tangentsIntersection, y)
		tangentsPoints = self.intersectCircle(helpCircle)
		return [Line(tangentsIntersection, t) for t in tangentsPoints]


	def pointForAngle(self, degrees) -> Point:
		"""
			return a point that is seen from origin in angle degrees from positive x-axis ccw, and my radius
		"""
		radians = math.radians(degrees)
		r = self.m_radius
		x = math.cos(radians) * r
		y = math.sin(radians) * r
		return Point(x, y)


	def isSameAs(self, other) -> bool:
		if not isinstance(other, Circle2):
			return False
		if not other.m_center.isSameAs(self.m_center):
			return False
		return ZGeomItem.almostEqual(self.m_radius, other.m_radius)


	@classmethod
	def circleRadiusFromSegment(cls, segLength, segHeight) -> float:
		# german wikipedia:  https://de.wikipedia.org/wiki/Kreissegment
		#return (4*segHeight*segHeight + segLength*segLength) / (8*segHeight)	

		# english wikipedia: https://en.wikipedia.org/wiki/Circular_segment
		return segHeight / 2 + (segLength * segLength) / (8 * segHeight)


	@classmethod
	def circleSegmentFromRadiusAndHeight(cls, R, d) -> float:
		"""
			return the length c of the secant/Chord
			d is the distance from center to the secant/Chord
		"""
		# english wikipedia: https://en.wikipedia.org/wiki/Circular_segment
		h = R - d
		c = math.sqrt(8*h*R  - 4*h*h)
		return c


	@classmethod
	def circleSegmentHeightFromRadiusAndWidth(cls, R, c) -> float:
		"""
			return the height h of the secant/Chord
			return a value for h between 0 and R
		"""
		# english wikipedia: https://en.wikipedia.org/wiki/Circular_segment
		discrim = 4*R*R - c*c
		if ZGeomItem.almostZero(discrim):
			return R
		if discrim < 0:
			return math.nan
		ret = R - (math.sqrt(discrim) / 2.0)
		return ret
		

	@classmethod
	def segmentHeightFromLength(cls, segLength, radius) -> float:	
		return radius - 0.5 * math.sqrt(4 * radius * radius - segLength * segLength)	# german wikipedia


	@classmethod
	def circleFromThreePoints(cls, p1, p2, p3) -> Circle2:
		"""
			Return a circle that touches the 3 given points.
			Points must be in x-y-plane
		"""
		test = abs(p1.m_z) + abs(p2.m_z) + abs(p3.m_z)
		if test > 3 * ZGeomItem.s_wantedAccuracy:
			raise Exception('circleFromThreePoints(): all 3 points must be in x-y-plane (off by ' + str(test) + ')')
		line1 = Line(p1, p2)
		line2 = Line(p2, p3)
		xyPlane = Plane(Point(), normal=Point(0, 0, 1))
		perp1 = line1.perpendicularLineThroughPointInPlane((p1 + p2).scaledBy(0.5), xyPlane)
		perp2 = line2.perpendicularLineThroughPointInPlane((p2 + p3).scaledBy(0.5), xyPlane)
		center = perp1.intersect(perp2)
		if center is None:
			return None
		radius = center.distanceOfPoint(p1)
		return Circle2(center, radius)



################################################################
################################################################


class Ellipse2(ZGeomItem):
	"""
		Ellipse in x-y plane
	"""
	def __init__(self, center, radiusX, radiusY, rotDegrees=0):
		super().__init__()
		self.m_center = center
		self.m_radiusX = radiusX
		self.m_radiusY = radiusY
		self.m_rotated = rotDegrees			# rotation of the x axis
		if radiusX > radiusY:

			pass
			#pointWithAngle



	def isSameAs(self, other) -> bool:
		if not isinstance(other, Ellipse2):
			return False
		if not other.m_center.isSameAs(self.m_center):
			return False
		if not self.almostEqual(self.m_radiusX, other.m_radiusX):
			return False
		if not self.almostEqual(self.m_radiusY, other.m_radiusY):
			return False
		return self.almostEqual(self.m_rotated, other.m_rotated)


	def printComment(self, comment, tabs=0, rounded=2):
		self.printTabs(tabs)
		print(f'{comment}:\n')
		self.m_center.printComment('center', tabs+1, rounded)
		self.printTabs(tabs + 1)
		print(f'radiusX: {str(round(self.m_radiusX))}, radiusY: {str(round(self.m_radiusY, rounded))}, rot: {str(round(self.m_rotated, rounded))}')


	def intersectLine(self, line):
		if not self.almostZero(self.m_rotated):
			raise Exception('please call ZGeomHelper intersectEllipseAndLine(ellipse, line) for rotated Ellipse')
		


#############################################################
#############################################################


class Ellipse3(ZGeomItem):
	"""
		Ellipse in 3d, diam1 is the longer diameter (or main axis)
	"""
	
	def __init__(self, center, diam1=None, diam2=None, vert1=None, vert2=None):
		super().__init__()
		if (diam1 is None and vert1 is None) or (diam1 is not None and vert1 is not None):
			raise Exception('exactly one of diam1 and vert1 must be not None')
		if (diam2 is None and vert2 is None) or (diam2 is not None and vert2 is not None):
			raise Exception('exactly one of diam2 and vert2 must be not None')

		if diam1 is None:
			diam1 = vert1 - center
		else:
			vert1 = center + diam1
		if diam2 is None:
			diam2 = vert2 - center
		else:
			vert2 = center + diam2

		if diam1.isZero() or diam2.isZero():
			raise Exception('both radii must be > 0')

		if not diam1.isPerpendicular(diam2):
			raise Exception('Ellipse3: diameters must be perpendicular')

		if diam2.length() > diam1.length():
			# sort according length
			diam1, diam2 = diam2, diam1
			vert1, vert2 = vert2, vert1

		self.m_center = center
		self.m_diam1 = diam1
		self.m_diam2 = diam2
		self.m_vert1 = vert1
		self.m_vert2 = vert2

		self.m_a = self.m_diam1.length()
		self.m_b = self.m_diam2.length()		
		self.m_exc = math.sqrt(self.m_a*self.m_a - self.m_b*self.m_b)
		focusOffset = self.m_diam1.scaledTo(self.m_exc)
		self.m_focus1 = self.m_center + focusOffset
		self.m_focus2 = self.m_center - focusOffset

		# ensure, that a 90 degree angle leads to self.m_center + self.m_diam2
		testPoint = self.pointForAngle(90)
		if not testPoint.isSameAs(self.m_vert2):
			self.m_diam2 = - self.m_diam2
			self.m_vert2 = self.m_center + self.m_diam2

		self.m_cachedPoints = None


	def copy(self):
		return Ellipse3(self.m_center.copy(), self.m_diam1.copy(), self.m_diam2.copy())
	

	def printComment(self, comment, tabs=0, rounded=2):
		self.printTabs(tabs)
		print(f'{comment}:\n')
		self.m_center.printComment('center', tabs+1, rounded)
		#self.printTabs(tabs + 1)
		self.m_diam1.printComment('diam1', tabs + 1, rounded)
		self.m_diam2.printComment('diam2', tabs + 1, rounded)
		#print(f'diam1: {str(round(self.m_radiusX))}, radiusY: {str(round(self.m_radiusY, rounded))}, rot: {str(round(self.m_rotated, rounded))}')



	def getNormale(self):
		return self.m_diam1.crossProduct(self.m_diam2).unit()
	

	def getRadii(self):
		return (self.m_diam1.length(), self.m_diam2.length())


	def pointForAngle(self, degrees):
		"""
			Return the point on me with the given angle. Start: my vert1, running over my vert2
		"""
		angle = math.radians(degrees)
		return self.m_center + self.m_diam1.scaledBy(math.cos(angle)) + self.m_diam2.scaledBy(math.sin(angle))


	def tangentForAngle(self, degrees):
		"""
			Return the tangent (not normalized) at a agiven angle
		"""
		angle = math.radians(degrees)
		# this is simply the derivative of the point formula with respect to angle
		return -self.m_diam1.scaledBy(math.sin(angle)) + self.m_diam2.scaledBy(math.cos(angle))


	#def provideCachedPoints(self):
	#	if self.m_cachedPoints is not None:
	#		return
	#	num = 360
	#	step = 360.0 / num
	#	cache = [None] * num
	#	for ii in range(num):
	#		cache[ii] = self.pointForParam(step * ii)
	#	self.m_cachedPoints = cache


	def angleForPoint(self, point):
		'''
			Return the angle between the vector from center to point and my main axis
		'''
		if not self.containsPoint(point):
			print(f'Ellipse3::angleForPoint cannot find angle for wrong point {point}')
			return None
		offset = point - self.m_center
		angle = self.m_diam1.angleTo(offset)
		testPoint = self.pointForAngle(angle)
		if testPoint.isSameAs(point):
			return angle
		dist1 = testPoint.distanceOfPoint(point)
		test1 = testPoint
		angle = 360 - angle
		testPoint = self.pointForAngle(angle)
		test2 = testPoint
		if testPoint.isSameAs(point):
			return angle
		dist2 = testPoint.distanceOfPoint(point)
		#self.printComment('ellipse3')
		numerical = self.tryAngleNumerically(point)
		if numerical is not None:
			angle = ZGeomItem.normalizeAngle(numerical)
			testPoint = self.pointForAngle(angle)
			dist3 = testPoint.distanceOfPoint(point)
			if testPoint.isSameAs(point):
				return angle
		raise Exception(f'Ellipse3::angleForPoint cannot find angle for {point}, dist1={dist1}, test1={test1} dist2={dist2}, test2={test2}')


	def tryAngleNumerically(self, point):
		func = lambda t: point.distanceOfPoint(self.pointForAngle(t))
		found = minimize_scalar(func, bounds=(0,180))
		if found.fun < ZGeomItem.s_wantedAccuracy:
			return found.x
		found = minimize_scalar(func, (180,360))
		if found.fun < ZGeomItem.s_wantedAccuracy:
			return found.x
		#print(found)
		return None

	# def paramForPointObsolete(self, point):
	# 	"""
	# 		Return the parameter value that leads to this point (if exists) in range between 0 and 359.999
	# 	"""
	# 	myLambda = lambda angle: point.distanceOf(self.pointForParam(angle))
	# 	self.provideCachedPoints()
	# 	minDist = 100000000
	# 	minIdx = -1
	# 	idx = 0
	# 	for p in self.m_cachedPoints:
	# 		dist = p.distanceOf(point)
	# 		if dist < minDist:
	# 			minDist = dist
	# 			minIdx = idx
	# 		idx += 1
	# 	print(f'minIdx = {minIdx}, min = {minDist}')

	# 	#result = minimize_scalar(myLambda, bounds=(0, 360), method='bounded')
	# 	result = minimize_scalar(myLambda, bounds=(idx - 1, idx + 1), method='bounded')
	# 	#print(result)
	# 	if self.almostZero(result.fun):
	# 		ret = result.x
	# 		if self.almostEqual(ret, 360):
	# 			ret = 0
	# 		return ret
	# 	return math.nan


	def isSameAs(self, otherEllipse):
		if not self.m_center.isSameAs(otherEllipse.m_center):
			return False
		if not self.getNormale().isCollinear(otherEllipse.getNormale()):
			return False
		if self.isCircle():
			if not otherEllipse.isCircle():
				return False
			if not self.almostEqual(self.m_diam1.length(), otherEllipse.m_diam1.length()):
				return False
			return True
		if not self.m_diam1.isCollinear(otherEllipse.m_diam1):
			return False
		if not self.m_diam2.isCollinear(otherEllipse.m_diam2):
			return False
		return True


	def containsPoint(self, point):
		"""
			return True, if point lies on me, else False, should be reprogrammed!!
		"""
		if not self.getPlane().containsPoint(point):
			return
		return self.almostZero(self.m_focus1.distanceOfPoint(point) + self.m_focus2.distanceOfPoint(point) - 2 * self.m_a)


	def isCircle(self):
		return self.almostEqual(self.m_diam1.length(), self.m_diam2.length())
	

	def getPlane(self):
		'''
			return a Plane that contains me
		'''
		return Plane(self.m_center, self.m_vert1, self.m_vert2)


	def getFocusPoints(self):
		"""
			return an array with my focus points
		"""
		return [self.m_focus1, self.m_focus2]


##############################################################
##############################################################


class Line(ZGeomItem):
	"""
		A line in 3d
		Can be regarded in 2 ways:
		- line through p1 and p2
		- line through p1 and with direction direction
	"""
	def __init__(self, p1, p2=None, direction=None):
		super().__init__()
		if p1 is None:
			raise Exception('illegal arg for Line: p1')
		self.m_p1 = p1
		if p2 is not None:
			if p2.isSameAs(p1):
				raise Exception('degenerate line: points must be different')
			self.m_p2 = p2
			self.m_direction = (p2 - p1).unit()
		elif direction is not None:
			if direction.isSameAs(Point()):
				raise Exception('Line: direction must not be null')
			self.m_direction = direction.unit()
			self.m_p2 = p1 + direction
		else:
			raise Exception('Line: p2 and direction must not be both None')


	def copy(self) -> Line:
		return Line(self.m_p1.copy(), self.m_p2.copy())


	def shiftedBy(self, shift: Point) -> Line:
		"""
			Return a shifted copy of me
		"""
		return Line(self.m_p1 + shift, self.m_p2 + shift)


	def intersect(self, otherItem) -> list:
		return otherItem.intersectLine(self)


	def pointForLambda(self, lambdaValue) -> Point:
		return self.m_p1 + self.m_direction.scaledBy(lambdaValue)
	

	def lambdaForPoint(self, point):
		if not self.containsPoint(point):
			return None
		dist = self.m_p1.distanceOfPoint(point)
		theLambda = dist / self.m_direction.length()
		cand = self.pointForLambda(theLambda)
		return theLambda if cand.isSameAs(point) else -theLambda


	def __str__(self) -> str:
		return 'Line(' + str(self.m_p1) + ', direction=' + str(self.m_direction) + ')'


	def rounded(self, num) -> Line:
		return Line(self.m_p1.rounded(num), direction=self.m_direction.rounded(num))


	def printComment(self, comment, tabs=0, num=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(num))}')


	def containsPoint(self, point) -> bool:
		if point.isSameAs(self.m_p1):
			return True
		return (point - self.m_p1).isCollinear(self.m_direction)


	def isParallel(self, otherLine) -> bool:
		return self.m_direction.isCollinear(otherLine.m_direction)


	def isSameAs(self, otherLine) -> bool:
		if not self.isParallel(otherLine):
			return False
		return otherLine.containsPoint(self.m_p1)


	def intersectPlane(self, plane) -> list:
		return plane.intersectLine(self)


	def perpendicularLineThroughPointInPlane(self, point, plane) -> Line:
		direction = self.m_direction.crossProduct(plane.m_normal)
		return Line(point, direction=direction)


	def parallelLinesInPlane(self, plane, distance) -> List[Line]:
		"""
			return 2 lines on both sides of me
		"""
		perpDirection = self.m_direction.crossProduct(plane.m_normal).scaledTo(distance)
		p1 = self.m_p1 + perpDirection
		p2 = self.m_p2 + perpDirection
		p3 = self.m_p1 - perpDirection
		p4 = self.m_p2 - perpDirection
		return [Line(p1, p2), Line(p3, p4)]


	def anyPerpendicularLineThrough(self, point) -> list:
		# we assume, that point lies on self
		# return a perpendicular line in otherPlane:
		otherPlane = Plane(point, normal=self.m_direction)
		#now we have to choose one arbitrary point on this plane, that is not = point
		#xyPlane = Plane(Point(), normal=Point(0, 0, 1))
		while True:
			pt = Point.randomPoint()
			if not self.containsPoint(pt):
				break
		thirdPlane = Plane(self.m_p1, self.m_p2, pt)
		return otherPlane.intersectPlane(thirdPlane)


	def perpendicular2DLineThrough(self, point):
		# we assume, that point lies on self
		# return a perpendicular line 1. in this plane:
		otherPlane = Plane(point, normal=self.m_direction)
		xyPlane = Plane(Point(), Point(1, 0), Point(0, 1))
		return otherPlane.intersectPlane(xyPlane)


	def isComplanar(self, line) -> bool:
		# are both lines in the same plane?
		plane = Plane(self.m_p1, self.m_p2, line.m_p1)
		return plane.containsPoint(line.m_p2)


	def intersectLine(self, otherLine: Line) -> Point:
		"""
			Return either the intersection point or None
		"""
		p1, p2 = self.nearestPointsToLine(otherLine)
		if p1.isSameAs(p2):
			return p1
		return None


	def nearestPointTo(self, point) -> Point:
		plane = Plane(point, normal=self.m_direction)
		return plane.intersectLine(self)


	def distanceOf(self, something) -> float:
		if isinstance(something, Point):
			test = self.nearestPointTo(something)
			return test.distanceOf(something)
		raise Exception('Line cannot calculate distanceOf: ' + something.__class__.__name__)


	def nearestPointsToLine(self, line2: Line) -> list:
		"""
			Return the points that are closest possible for the 2 lines in D3
			If there are several points, return one pair
		"""
		if self.isSameAs(line2):
			return [self.m_p1, self.m_p1]

		connection = self.m_direction.crossProduct(line2.m_direction)
		if connection.isSameAs(Point()):
			# lines are parallel
			p2 = line2.nearestPointTo(self.m_p1)
			return [self.m_p1, p2]
		helpPlane2 = Plane(self.m_p1, self.m_p2, self.m_p1 + connection)
		f2 = line2.intersect(helpPlane2)
		f1 = self.nearestPointTo(f2)
		return [f1, f2]


	def liesInside(self, point) -> bool:
		# if the point lies on myself and between my p1 and p2, return True
		if not self.containsPoint(point):
			return False
		dEdge = self.m_p1.distanceOfPoint(self.m_p2)
		d1 = point.distanceOfPoint(self.m_p1)
		d2 = point.distanceOfPoint(self.m_p2)
		return d1 + d2 < dEdge + self.s_wantedAccuracy

##########
#	some hardcore intersection stuff:

	def usableAxesForIntersection(self) -> str:
		"""
			Return 'x' or 'y' or 'z' if the according direction component is not 0
		"""
		ret = ''
		dire = self.m_direction
		if not self.almostZero(dire.m_x):
			ret += 'x'
		if not self.almostZero(dire.m_y):
			ret += 'y'
		if not self.almostZero(dire.m_z):
			ret += 'z'
		return ret


	def condenseEquations(self, preferredAxis=None) -> list:
		"""
			Return a list of constants for replacements in the form ['x', [c11, c12], [c21, c22]]
			so that y = c11 * x + c12, and z = c21 * x + c22, if preferred(possible)Axis == 'x'.
			The return value is called a paramSet.
			Usage of preferredAxis is discouraged, only makes sense for tests.
			If the given preferredAxis is impossible, we use any other possible one
		"""
		usableAxes = self.usableAxesForIntersection()
		if not str(preferredAxis) in usableAxes:
			preferredAxis = usableAxes[0]

		[px, py, pz] = [self.m_p1[ii] for ii in range(3)]
		[vx, vy, vz] = [self.m_direction[ii] for ii in range(3)]

		if preferredAxis == 'x':
			# no remapping of the axes required
			pass
		elif preferredAxis == 'y':
			# exchange x and y
			(px, py) = (py, px)
			(vx, vy) = (vy, vx)
		elif preferredAxis == 'z':
			# move z->x, x->y, y->z
			(px, py, pz) = (pz, px, py)
			(vx, vy, vz) = (vz, vx, vy)

		# now calculate, as if preferredAxis = 'x' was used:
		F5 = [vy / vx, py - px * vy / vx]	# y = F5(x)
		F7 = [vz / vx, pz - px * vz / vx]	# z = F7(x)
		return [preferredAxis, F5, F7]


	#def condenseEquationsWorking(self, preferredAxis=None) -> list:
	#	"""
	#		The old version of this method. A bit complicated, because we have a solution for every
	#		axis. Newer Version handles this by just renaming the axes.
	#		Return a list of constants for replacements in the form ['x', [c11, c12], [c21, c22]]
	#		so that y = c11 * x + c12, and z = c21 * x + c22, if preferredAxis == 'x' and x is possible.
	#		Usage of preferredAxis is discouraged, only makes sense for tests
	#	"""
	#	[px, py, pz] = [self.m_p1[ii] for ii in range(3)]
	#	[vx, vy, vz] = [self.m_direction[ii] for ii in range(3)]
#
	#	if not self.almostZero(vx) and preferredAxis in [None, 'x']:
	#		F5 = [vy / vx, py - px * vy / vx]	# y = F5(x)
	#		F7 = [vz / vx, pz - px * vz / vx]	# z = F7(x)
	#		return ['x', F5, F7]

	#	if not self.almostZero(vy) and preferredAxis in [None, 'y']:
	#		F5 = [vx / vy, px - py * vx / vy]	# x = F5(y)
	#		F7 = [vz / vy, pz - py * vz / vy]	# z = F7(y)
	#		return ['y', F5, F7]

	#	if not self.almostZero(vz) and preferredAxis in [None, 'z']:
	#		F5 = [vx / vz, px - pz * vx / vz]	# x = F5(z)
	#		F7 = [vy / vz, py - pz * vy / vz]	# y = F7(z)
	#		return ['z', F5, F7]

	#	print('Line.condenseEquations(): no possible axis found')


	@classmethod
	def getPointForParamSet(cls, paramSet, value):
		"""
			paramSet is gotten by method condenseEquations()
		"""
		axis = paramSet[0]
		o1 = cls.applyParams(paramSet[1], value)
		o2 = cls.applyParams(paramSet[2], value)
		if axis == 'x':
			return Point(value, o1, o2)
		if axis == 'y':
			return Point(o1, value, o2)
		return Point(o1, o2, value)

		
	@classmethod
	def applyParams(cls, params, value):
		return value * params[0] + params[1]




################################################################
################################################################


class Plane(ZGeomItem):
	"""
		A plane in 3d
	"""
	def __init__(self, p1, p2=None, p3=None, normal=None):
		super().__init__()
		self.m_p1 = p1
		if p1 is None:
			raise Exception('incomplete plane definition')
		if normal is not None:
			normal = normal.unit()
			self.m_p2 = None
			self.m_p3 = None
			
		else:
			# no normal given, we need p2 and p3
			if p2 is None or p3 is None:
				raise Exception('incomplete plane definition')
			normal = ((p2-p1).crossProduct(p3-p1, 1)).unit()
		if p1 * normal < 0:
			normal = -normal
		self.m_normal = normal
		self.m_d = p1 * normal


	@classmethod
	def alongAxes(cls, axis1: str, axis2: str) -> Plane:
		"""
			Return a plane that contains the both axes (must be 'x', 'y', 'z')
		"""
		if axis1 == axis2 or not axis1 in  'xyz' or not axis2 in 'xyz':
			raise Exception('illegal axes given: (' + str(axis1) + ')(' + str(axis2) + ')(legal: xyz)')
		if axis1 == 'x':
			if axis2 == 'y':
				normal = Point(0, 0, 1)
			elif axis2 == 'z':
				normal = Point(0, 1)
		elif axis1 == 'y':
			if axis2 == 'x':
				normal = Point(0, 0, 1)
			elif axis2 == 'z':
				normal = Point(1)
		else:
			# axis1 = 'z'
			if axis2 == 'x':
				normal = Point(0, 1)
			elif axis2 == 'y':
				normal = Point(0, 0, 1)
			elif axis2 == 'z':
				normal = Point(1)
		return Plane(Point(), normal=normal)


	def getThreePoints(self) -> List[Point]:
		if self.m_p2 is None:
			p1 = self.m_p1
			normal = self.m_normal
			helpLine = Line(p1, direction=normal)
			helpLine2 = helpLine.anyPerpendicularLineThrough(p1)
			p2 = helpLine2.pointForLambda(1)
			self.m_p2 = p2
		if self.m_p3 is None:
			p3 = self.m_normal.crossProduct(self.m_p1 - self.m_p2)
			self.m_p3 = self.m_p1 + p3
		return [self.m_p1, self.m_p2, self.m_p3]


	def intersect(self, otherItem) -> list:
		return otherItem.intersectPlane(self)
		

	def signedDistanceOfPoint(self, point) -> float:		
		return point * self.m_normal - self.m_d


	def distanceOfPoint(self, point) -> float:		
		return abs(self.signedDistanceOfPoint(point))


	def intersectLine(self, line) -> Point:
		lineDirection = line.m_direction
		numer = lineDirection * self.m_normal
		if self.almostZero(numer):
			return []
		lambdaValue = (self.m_d - self.m_normal * line.m_p1) / numer
		point = line.pointForLambda(lambdaValue)
		return point


	def isSameAs(self, otherPlane):
		if not self.isParallel(otherPlane):
			return False
		return otherPlane.containsPoint(self.m_p1)


	def intersectPlane(self, otherPlane: Plane) -> Line:
		"""
			Return intersection line. If otherPlane is parallel (or the same!) return None.
			See https://de.wikipedia.org/wiki/Schnittgerade#Schnitt_zweier_Ebenen_in_Normalenform

		"""
		if self.isParallel(otherPlane):
			return None

		# note: n1 and n2 have length 1 each
		n1 = self.m_normal
		d1 = self.m_d
		n2 = otherPlane.m_normal
		d2 = otherPlane.m_d

		scalarP = n1 * n2
		fac1 = (d1 - d2 * scalarP) / (1 - scalarP * scalarP)
		fac2 = (d2 - d1 *scalarP) / (1 - scalarP * scalarP)

		pQ = n1.scaledBy(fac1) + n2.scaledBy(fac2)

		direction = self.m_normal.crossProduct(otherPlane.m_normal)

		return Line(pQ, direction=direction)


	def __str__(self) -> str:
		return 'Plane(' + str(self.m_p1) + ', normal='+str(self.m_normal)+', d='+str(self.m_d)+')'


	def printComment(self, comment, tabs=0, rounded=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(rounded))}')


	def rounded(self, num) -> Plane:
		return Plane(self.m_p1.rounded(num), normal=self.m_normal.rounded(num))


	def isParallel(self, otherPlane) -> bool:
		return self.m_normal.isCollinear(otherPlane.m_normal)


	def angleToLine(self, line) -> float:
		"""
			measured in degrees
		"""
		return self.angleToVector(line.m_direction)


	def angleToVector(self, vector: Point) -> float:
		"""
			Return an angle between 0 and 90
		"""
		angle = self.normalizeAngle(90 - vector.angleTo(self.m_normal))
		while angle > 90:
			angle -= 90

		return angle


	def containsPoint(self, point: Point) -> bool:
		return self.almostEqual(point * self.m_normal, self.m_d)


	def nearestPointTo(self, point) -> Point:
		line = Line(point, direction=self.m_normal)
		return self.intersectLine(line)


############################################################
############################################################


class Polygon(ZGeomItem):
	"""
		A polygon in 3d
	"""
	def __init__(self, pointList):
		# the first point must not be repeated at the end,
		# although we consider it closed
		super().__init__()
		self.m_points = pointList
		if pointList[0].isSameAs(pointList[-1]):
			pointList.pop()

		c = Point()
		for point in pointList:
			c = c + point
		self.m_center = c.scaledBy(1.0 / len(pointList))
		self.m_containingPlane = None
		self.planarityChecked = False
		self.m_vectorArea = None


	def __str__(self) -> str:
		ret = 'Polygon('
		for point in self.m_points:
			ret = ret + str(point) + ', '
		ret = ret + ')'
		return ret
		

	def area(self) -> float:
		if self.m_vectorArea is not None:
			return self.m_vectorArea.length() / 2.0
		va = Point()
		oldPoint = None
		for p in self.m_points:
			if not oldPoint is None:
				va += oldPoint.crossProduct(p)
			oldPoint = p
		va += oldPoint.crossProduct(self.m_points[0])
		self.m_vectorArea = va
		if va.isSameAs(Point()):
			return 0
		return va.length() / 2.0
		

	# see https://stackoverflow.com/questions/32274127/how-to-efficiently-determine-the-normal-to-a-polygon-in-3d-space
	# c is a point outside the polygon, from which you look at it to see the orientation
	def isClockwise(self, c) -> bool:
		self.area()
		if self.m_vectorArea.length() == 0:
			print('Polygon: cannot know if isClockwise: area = 0')
			raise Exception('Polygon: cannot know if isClockwise: area = 0')
			return None
		theSum = self.m_vectorArea.unit()
		plane = Plane(self.m_center, normal=theSum)
		# now check, on which half space is c in respect to plane
		dist = plane.distanceOfPoint(c)
		testPoint = c + theSum.scaledBy(dist/2.0)
		testDist = plane.distanceOfPoint(testPoint)
		if testDist < dist:
			return False
		return True


	def makeClockwise(self, pointOutside, direction=True) -> int:
		"""
			returns 0, if the orientation is ok, possibly after removing identical points
			returns 1, if the orientation could be achieved by reversing or by removing identical points
			returns 2, if i am degenerated.
		"""
		if len(self.m_points) < 3:
			return 2
		try:
			test = self.isClockwise(pointOutside)
		except Exception:
			if not self.remove2IdenticalPoints():
				return 2
			return self.makeClockwise(pointOutside, direction) 
		if test == direction:
			return 0
		self.m_points.reverse()
		return 1


	def remove2IdenticalPoints(self) -> bool:
		"""
			Return True, if i could find 2 identical points (and remove one of them)
		"""
		idx = -1
		for ii in range(len(self.m_points) - 1):
			if self.m_points[ii].isSameAs(self.m_points[ii + 1]):
				idx = ii
				break
		if idx < 0:
			return False
		self.m_points.remove(self.m_points[idx])
		return True
		

	def containingPlane(self) -> Plane:
		"""
			Return a plane that contains all my points, or None
		"""
		points = self.m_points
		if self.planarityChecked:
			return self.m_containingPlane
		self.planarityChecked = True
		plane = Plane(points[0], points[1], points[2])
		if len(points) > 3:
			for ii in range(len(points) - 3):
				point = points[ii + 3]
				if not plane.containsPoint(point):
					return None
		self.m_containingPlane = plane
		return plane


	def allLines(self, addLast=True) -> list:
		"""
			Return an array of lines between my consecutive points. If addLast also add last closing line.
		"""
		ret = []
		points = self.m_points
		if len(points) < 2:
			return ret
		for ii in range(1, len(points)):
			ret.append(Line(points[ii-1], points[ii]))
		if addLast and len(points) > 2:
			ret.append(Line(points[-1], points[0]))
		return ret


	def insetBy(self, dist) -> Polygon:
		# return a new Polygon, that is bigger(dist > 0) or smaller
		# throws an error for non-plane polygons
		plane = self.containingPlane()
		if plane is None:
			raise Exception('cannot inset a non-plane polygon')
		center = self.m_center
		oldLines = self.allLines()
		newLines = []
		for oldLine in oldLines:
			p1 = oldLine.m_p1
			perpLine = oldLine.perpendicularLineThroughPointInPlane(p1, plane)
			perpVect = perpLine.m_direction.scaledTo(dist)
			p11 = p1 + perpVect
			if (center.distanceOfPoint(p11) - center.distanceOfPoint(p1)) * dist < 0:
				perpVect = perpVect.scaledBy(-1)
			p11 = p1 + perpVect
			p21 = oldLine.m_p2 + perpVect
			newLines.append(Line(p11, p21))

		newPoints = []
		
		newPoints.append(newLines[-1].intersectLine(newLines[0]))
		for ii in range(1, len(newLines)):
			newPoints.append(newLines[ii-1].intersectLine(newLines[ii]))
		
		ret = Polygon(newPoints)
		#print(ret)
		return ret


	def printComment(self, comment, tabs=0, rounded=2):
		self.printTabs(tabs)
		print(f'{comment}:\n')
		ii = 1
		for p in self.m_points:
			p.printComment('p' + str(ii), tabs + 1, rounded)


	def massCenter(self) -> Point:
		ret = Point()
		for p in self.m_points:
			ret += p
		return ret.scaledBy(1.0 / len(self.m_points))


##########################################################
##########################################################


class Circle3(Plane):
	"""
		A circle in 3d
	"""
	def __init__(self, center, normal, radius):
		super().__init__(center, normal=normal)
		self.m_radius = radius
		self.m_center = center

	
	def center(self) -> Point:
		return self.m_p1


	def containsPoint(self, point) -> bool:
		if not super().containsPoint(point):
			return False
		return ZGeomItem.almostEqual(point.distanceOfPoint(self.m_center), self.m_radius)
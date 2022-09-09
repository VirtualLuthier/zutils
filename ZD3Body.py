"""
	Contains some regular 3d bodies:
	- D3Body (abstract superclass)
	- ZBall3d
	- ZCylinder
	- ZCone
	calculates intersection with 3d line
"""

import math
from numbers import Number

from zutils.ZGeom import ZGeomItem, Point, Line, Plane, Circle2, Circle3
from zutils.ZMatrix import Matrix, Affine


#####################################################################
#####################################################################

class D3Body:
	"""
		Abstract superclass, implements intersectLine()
	"""
	def intersectLine(self, line):
		aff = Affine()
		if self.isSimple():
			doer = self
		else:
			aff = self.makeAffToSimple()
			doer = self.transformedBy(aff)

		line2 = aff * line
		inter = doer.intersectLineSimple(line2)
		affInv = aff.inverted()
		return [affInv * q for q in inter]


	def printTabs(cls, tabs):
		"""
			Print the given number of tabs and make no line feed at the end.
		"""

		for _ in range(tabs):
			print('	', end='')



####################################################################
####################################################################


class ZBall3d(D3Body):
	"""
		A simple ball in 3d
	"""
	def __init__(self, c, r):
		self.m_center = c
		self.m_radius = r


	def containsPoint(self, p: Point) -> bool:
		return ZGeomItem.almostEqual(self.m_center.distanceOfPoint(p), self.m_radius)


	def transformedBy(self, affine):
		"""
			Return a Ball3d that represents me, but transformed with the affine
		"""
		q1 = affine * self.m_center
		return ZBall3d(q1, self.m_radius)


	def makeAffToSimple(self):
		return Affine(None, - self.m_center)


	def isSimple(self):
		return self.m_center.isSameAs(Point())


	def intersectLineSimple(self, line: Line):
		if not self.isSimple():
			raise Exception('intersection works only for simple cylinders')

		r = self.m_radius
		equations = line.condenseEquations()
		[_, [c11, c12], [c21, c22]] = equations

		# x, y and z are exchangable
		# our equation is x^2 + y^2 + z^2 = r^2
		a = 1 + c11*c11 + c21*c21
		b = 2*(c11*c12 + c21*c22)
		c = c12*c12 + c22*c22 - r*r

		solutions = ZGeomItem.solveQuadratic(a, b, c)
		ret = [line.getPointForParamSet(equations, q) for q in solutions]

		return ret


####################################################################
####################################################################


class ZCylinder(D3Body):
	"""
		A 3d cylinder in any direction. p1 and p2 are 2 points ON MY TANGENT (not the center points!)
	"""
	def __init__(self, p1, p2, r2, centerLine):
		self.m_p1 = p1
		self.m_p2 = p2
		self.m_r2 = r2
		
		self.m_centerLine = centerLine

		c1 = self.getCenterPointFor(p1)
		self.m_center = c1
		c2 = self.getCenterPointFor(p2)
		self.m_centerHeight = (c1 - c2).length()


	def printComment(self, comment, tabs=1, rounded=2):
		self.printTabs(tabs)
		print(comment + ': ')
		self.printTabs(tabs)
		print(self.__class__.__name__)
		self.m_p1.printComment('start', tabs + 1, rounded)
		self.printTabs(tabs+1)
		print(f'r1: {self.getRadius1()}')
		self.m_p2.printComment('stop', tabs + 1, rounded)
		self.printTabs(tabs+1)
		print(f'r2: {self.m_r2}')


	def getRadius1(self):
		return self.m_r2


	def enlargedTangentiallyBy(self, d1, d2):
		"""
			Return a new Cylinder which is larger than me in tangential direction(d1, d2 > 0: larger)
		"""
		p1 = self.m_p1
		p2 = self.m_p2
		direction = (p2 - p1).unit()
		p1New = p1 - direction.scaledBy(d1)
		p2New = p2 + direction.scaledBy(d2)
		return ZCylinder(p1New, p2New, self.m_r2, self.m_centerLine.copy())


	def enlargedRadiallyBy(self, d):
		"""
			Return a new Cylinder which is larger than me in tangential direction(d > 0: larger)
		"""
		p1 = self.m_p1
		p2 = self.m_p2
		c1 = self.getCenterPointFor(p1)
		dV = (p1 - c1).scaledTo(d)
		return ZCylinder(p1 + dV, p2 + dV, self.m_r2 + d, self.m_centerLine.copy())


	#def enlargedBy(self, d1, d2):
	#	"""
	#		Return a new Cylinder/Cone which is larger than me (d1, d2 > 0: larger)
	#		Not yet tested!!!
	#	"""
	#	#myClone = self.clone()
	#	c1 = self.getCenterPointFor(self.m_p1)
	#	c2 = self.getCenterPointFor(self.m_p2)
	#	direction = (c2 - c1).unit()
	#	c1New = c1 + direction.scaledBy(d1)
	#	c2New = c2 - direction.scaledBy(d2)
	#	tangent = Line(self.m_p1, self.m_p2)
	#	plane1 = Plane(c1New, normal=direction)
	#	plane2 = Plane(c2New, normal=direction)
	#	p1New = plane1.intersectLine(tangent)
	#	r1New = p1New.distanceOfPoint(c1New)
	#	p2New = plane2.intersectLine(tangent)
	#	r2New = p2New.distanceOfPoint(c2New)


	def ratioInnerToOuter(self):
		"""
			the cos of the opening angle
		"""
		return  1.0


	def getCenterPointFor(self, point) -> Point:
		"""
			Return the point on my centerLine that is nearest to point
		"""
		return self.m_centerLine.nearestPointTo(point)


	def getPerpendicularDistanceFor(self, point) -> float:
		"""
			Return the perpendicular distance of point to my centerline
		"""
		p = self.getCenterPointFor(point)
		return (p - point).length()


	def getCircle(self, point):
		direction = self.m_centerLine.m_direction
		center = self.getCenterPointFor(point)
		radius = self.getPerpendicularDistanceFor(point)
		return Circle3(center, direction, radius)


	def containsPoint(self, point):
		"""
			return True, if point is on my defining surface
		"""
		dist = self.getPerpendicularDistanceFor(point)
		return ZGeomItem.almostEqual(dist, self.m_r2)


	#def enlargedToCenter(self):
	#	"""
	#	Return a version of me, where my center is the p1 point
	#	"""
	#	return self


	def transformedBy(self, affine):
		"""
			Return a ZCylinder that represents me, but transformed with the affine
		"""
		q1 = affine * self.m_p1
		q2 = affine * self.m_p2
		cl = affine * self.m_centerLine
		return ZCylinder(q1, q2, self.m_r2, cl)


	def makeAffToSimple(self):
		return Affine.morphLineToLine(self.m_centerLine, Line(Point(), Point(0, 0, 1)))


	def isSimple(self):
		if not self.m_center.isSameAs(Point()):
			return False
		if not self.m_centerLine.isSameAs(Line(Point(), Point(0, 0, 1))):
			return False
		#if not self.m_center.isSameAs(self.m_p1):
		#	return False
		#if not ZGeomItem.almostEqual(self.m_r1, 0):
		#	return False
		return True


	def intersectLineSimple(self, line: Line):
		if not self.isSimple():
			raise Exception('intersection works only for simple cylinders')

		r = self.m_r2
		equations = line.condenseEquations()
		[axis, [c11, c12], [c21, c22]] = equations
		if axis in 'xy':
			# x and y are exchangable
			# our cone equation is x^2 + y^2 = r^2 in general, or here:
			# x^2 + (x * c11 + c12)^2 = r^2
			a = 1 + c11*c11
			b = 2*c11*c12
			c = c12*c12 - r*r
			#print('a=' + str(a) + ', b=' + str(b) + ', c=' + str(c))

		else:
			# z is handled a bit different
			# cone equation here:
			# (c11*z + c12)^2 + (c21*z + c22)^2 = r^2
			a = c11*c11 + c21*c21
			b = 2*c11*c12 + 2*c21*c22
			c = c12*c12 + c22*c22 - r*r

		solutions = ZGeomItem.solveQuadratic(a, b, c)
		ret = [line.getPointForParamSet(equations, q) for q in solutions]

		return ret


	def clone(self):
		return ZCylinder(self.m_p1, self.m_p2, self.m_r2, self.m_centerLine)

	
	@classmethod
	def makeCylinders(cls, p1, p2, rr2, p3):
		"""
			Create 2 instances of ZCylinder through p1, p2, p3 on the coat with the given radius. 
			p3 is any point on the plane defined by the center line and the points.
		"""
		r2 = rr2
		if ZGeomItem.almostEqual(rr2, 0):
			r2 = 0
		if rr2 == 0:
			raise Exception('ZCylinder with radius == 0 is illegal')
		if rr2 < 0:
			raise Exception('ZCylinder with radius < 0 is illegal')
		if p1.isSameAs(p2):
			raise Exception('ZCylinder points must be different')

		# morph the plane to x-y-plane
		plane = Plane(p1, p2, p3)
		affToXY = Affine.morphPlaneToXY(plane, p1, p2)
		affFromXY = affToXY.inverted()

		# now we can solve the problem for q1, q2 in x-y-plane
		ret = []

		for dist in [r2, -r2]:
			centerLine = Line(Point(0, dist), direction=Point(1))
			ret.append(ZCylinder(p1, p2, r2, affFromXY * centerLine))

		return ret


####################################################################
####################################################################


class ZCone(ZCylinder):
	"""
		A general cone located somewhere in D3.
		p1 and p2 are 2 points ON MY TANGENT (not the center points!)
		This constructor needs not be called directly. Use ZCone.makeCones() instead
	"""
	def __init__(self, p1, r1, p2, r2, center, centerLine):
		super().__init__(p1, p2, r2, centerLine)
		self.m_r1 = r1
		self.m_center = center



	def enlargedTangentiallyBy(self, d1, d2):
		"""
			Return a new Cone which is larger than me in tangential direction(d1, d2 > 0: larger)
		"""
		p1 = self.m_p1
		p2 = self.m_p2
		direction = (p2 - p1).unit()
		p1New = p1 - direction.scaledBy(d1)
		p2New = p2 + direction.scaledBy(d2)
		r1 = self.getPerpendicularDistanceFor(p1New)
		r2 = self.getPerpendicularDistanceFor(p2New)
		return ZCone(p1New, r1, p2New, r2, self.m_center.copy(), self.m_centerLine.copy())


	def enlargedRadiallyBy(self, d):
		"""
			Return a new Cone which is larger than me in radial direction(d > 0: larger)
		"""
		p1 = self.m_p1
		p2 = self.m_p2
		c1 = self.getCenterPointFor(p1)
		dV = (p1 - c1).scaledTo(d)
		p1New = p1 + dV
		p2New = p2 + dV
		tangentNew = Line(p1New, p2New)
		cNew = tangentNew.intersectLine(self.m_centerLine)
		if cNew is None:
			raise Exception('cannot find new cone center')
		return ZCone(p1New, self.m_r1 + d, p2New, self.m_r2 + d, cNew, self.m_centerLine.copy())


	def getRadius1(self):
		return self.m_r1


	def containsPoint(self, point):
		"""
			return True, if point is on my defining surface
		""" 
		# ok, I am a real cone
		zeroCenter = self.m_center
		if zeroCenter.isSameAs(point):
			return True
		pointLine = Line(zeroCenter, point)
		#centerLine = self.m_centerLine
		center2Plane = Plane(self.m_p2, normal=self.m_centerLine.m_direction)
		intersect = center2Plane.intersect(pointLine)
		if intersect is None:
			return False
		return ZGeomItem.almostEqual(self.getPerpendicularDistanceFor(intersect), self.m_r2)


	def ratioInnerToOuter(self):
		"""
			the cos of the opening angle
		"""
		return  self.m_centerHeight / self.m_p1.distanceOf(self.m_p2)


	def openingAngle(self):
		"""
			Currently only the half angle is returned
		"""
		return math.acos(self.ratioInnerToOuter())


	def makeAffToSimple(self):
		return Affine.morphLineToLine(self.m_centerLine, Line(Point(), Point(0, 0, 1)), self.m_center)


	#def enlargedToCenter(self):
	#	"""
	#	Return a version of me, where my center is the p1 point
	#	"""
	#	return ZCone(self.m_center, 0, self.m_p2, self.m_r2, self.m_center, self.m_centerLine)


	def transformedBy(self, affine):
		"""
			Return a ZCone that represents me, but transformed with the affine
		"""
		q1 = affine * self.m_p1
		q2 = affine * self.m_p2
		c = affine * self.m_center
		cl = affine * self.m_centerLine
		return ZCone(q1, self.m_r1, q2, self.m_r2, c, cl)


	def intersectLineSimple(self, line: Line):
		if not self.isSimple():
			raise Exception('intersection works only for simple cones')

		k = math.tan(self.openingAngle())

		equations = line.condenseEquations()
		[axis, [c11, c12], [c21, c22]] = equations
		if axis in 'xy':
			# x and y are exchangable
			# our cone equation is x^2 + y^2 = k^2 * z^2 in general, or here:
			# x^2 + (x * c11 + c12)^2 = k^2 * (x * c21 + c22)^2
			a = 1 + c11*c11 - k*k*c21*c21
			b = 2*c11*c12 - 2*k*k*c21*c22
			c = c12*c12 - k*k*c22*c22
			#print('a = ' + str(a) + ', b = ' + str(b) + ', c = ' + str(c) + ', axis = ' + axis)

		else:
			# z is handled a bit different
			# cone equation here:
			# (c11*z + c12)^2 + (c21*z + c22)^2 = k^2*z^2
			a = c11*c11 + c22*c22 - k*k
			b = 2*c11*c22 + 2*c21*c22
			c = c12*c12 + c22*c22

		solutions = ZGeomItem.solveQuadratic(a, b, c)
		ret = [line.getPointForParamSet(equations, q) for q in solutions]

		return ret


	def isSimple(self):
		if not self.m_center.isSameAs(Point()):
			return False
		if not self.m_centerLine.isSameAs(Line(Point(), Point(0, 0, 1))):
			return False
		#if not self.m_center.isSameAs(self.m_p1):
		#	return False
		#if not ZGeomItem.almostEqual(self.m_r1, 0):
		#	return False
		return True


	def clone(self):
		return ZCone(self.m_p1, self.m_r1, self.m_p2, self.m_r2, self.m_center, self.m_centerLine)


	@classmethod
	def makeCones(cls, p1: Point, rr1: Number, p2: Point, rr2: Number, p3: Point):
		"""
			Create 2 instances of ZCone with p1, p2 ON THE COAT(!) with the given radii. 
			p3 is only used to determine the plane for the center line and the points
		"""
		if ZGeomItem.almostEqual(rr1, 0):
			r1 = 0
		if ZGeomItem.almostEqual(rr2, 0):
			r2 = 0
		if ZGeomItem.almostEqual(rr1, rr2):
			rr2 = rr1
		if rr1 == 0 and rr2 == 0:
			raise Exception('ConeNew with 2 radii == 0 is illegal')
		if rr1 < 0 or rr2 < 0:
			raise Exception('ConeNew with radius < 0 is illegal')
		if p1.isSameAs(p2):
			raise Exception('cone points must be different')

		if rr1 == rr2:
			return ZCylinder.makeCylinders(p1, p2, rr2, p3)

		# first sort the points according to the radius size:
		if rr1 > rr2:
			(p1, p2) = (p2, p1)
			(r1, r2) = (rr2, rr1)
		else:
			(r1, r2) = (rr1, rr2)
		# now p1 has radius r1, and r1 < r2

		# morph the plane to x-y-plane
		plane = Plane(p1, p2, p3)
		affToXY = Affine.morphPlaneToXY(plane, p1, p2)
		affFromXY = affToXY.inverted()

		# so we mapped p1 -> Point() and p2 -> somewehere on the x axis!
		q1 = Point()
		q2 = (affToXY * p2).flattened()

		# now we can solve the problem for q1, q2 in x-y-plane
		ret = []
		pointLine = Line(q1, q2)

		# a general cone
		dR = r2 - r1
		dQ1Q2 = (q2 - q1).length()
		dQ1QX = math.sqrt(dQ1Q2 * dQ1Q2 - dR * dR)

		circle1 = Circle2(Point(), dQ1QX)
		circle2 = Circle2(q2, dR)

		pointsX = circle1.intersect(circle2)
		
		for inter in pointsX:
			connection = (inter - q2).unit()
			center1 = q1 + connection.scaledTo(r1)
			center2 = q2 + connection.scaledTo(r2)
			centerLine = Line(center1, center2)
			mainCenter = pointLine.intersect(centerLine)
			if r1 == r2:
				ret.append(ZCylinder(p1, p2, r1, affFromXY * centerLine))
			ret.append(ZCone(p1, rr1, p2, rr2, affFromXY * mainCenter, affFromXY * centerLine))

		return ret


##################################################################
##################################################################


class ZConeOld:
# our cones are located around the z axis:
# r1 is around the origin, the other point is on the positive Z axis (in distance self.m_height)
	def __init__(self, r1, r2, height=math.nan, distanceOutside=math.nan):
		self.m_r1 = r1
		self.m_r2 = r2
		dr = r1 - r2
		if ZGeomItem.almostEqual(self.m_r1, 0):
			self.m_r1 = 0
		if ZGeomItem.almostEqual(self.m_r1, self.m_r2):
			self.m_r2 = self.m_r1
		if self.m_r1 == 0 and self.m_r2 == 0:
			raise Exception('Cone with 2 radii == 0 is illegal')
		if not math.isnan(height):
			if height < 0 or ZGeomItem.almostEqual(height, 0): 
				raise Exception('Cone with height 0 is illegal')
			self.m_height = height
			self.m_distanceOutside = math.sqrt(height * height + dr * dr)
		elif not math.isnan(distanceOutside):
			if distanceOutside < 0 or ZGeomItem.almostEqual(distanceOutside, 0): 
				raise Exception('Cone with distanceOutside 0 is illegal')
			self.m_distanceOutside = distanceOutside
			dO = distanceOutside
			self.m_height = math.sqrt(dO * dO - dr * dr)
		else:
			raise Exception('ZCone: height and distanceOutside cannot both be None')
		self.m_center1 = Point()
		self.m_center2 = Point(0, 0, self.m_height)

	def smoothToLine(self, line, point, planeVector):
		# point must lie on line
		# move myself, so that the line is a "vertical" tangent i.e. 
		# my center1 and center2 are on the plane defined by line and planeVector
		# let center2 - center1 be a normal of plane1 through center1
		# then point lies on this plane (and distance is r1)
		# let direction = point - center1
		# then the line defined by center2 with direction will intersect argument line
		# and the distance from center2 to intersection point is r2
		if not line.containsPoint(point):
			raise Exception('input point must lie on input line')
		if planeVector.isCollinear(line.m_direction):
			raise Exception('planeVector vector must not be collinear with line')
		# first define the plane where center1 and center2 must be in
		lineDirection = line.m_direction
		point2 = point + lineDirection.scaledTo(self.m_distanceOutside)
		plane = Plane(point, point2, point + planeVector)
		aff = Affine.morphPlaneToXY(plane, point, point2)
		pp1 = point
		pp2 = point2
		r1 = self.m_r1
		r2 = self.m_r2
		circle1 = Circle2(aff * pp1, r1)
		circle2 = Circle2(aff * pp2, r2)
		tangents = circle1.combinedTangentsWith(circle2)
		if tangents is not None:
			tangent = tangents[0]
		else:
			# the radii are equal, we create a dummy
			dummy1 = circle1.m_center + Point(-10, r1)
			dummy2 = circle1.m_center + Point(0, r2)
			tangent = Line(dummy1, dummy2)

		# get the new centers in x-y-Plane
		center1 = tangent.m_p2
		center2 = circle2.intersect(tangent)[0]

		# transform the centers:
		aff = aff.inverted()
		self.m_center1 = aff * center1
		self.m_center2 = aff * center2

		
	def getAffine(self):
		# return an affine that transforms me from initial position
		# (as described in constructor) to my current position (and direction)
		translation = self.m_center1
		direction = self.m_center2 - self.m_center1
		matrix = Matrix.makeOrthonormalTransformation(pz=direction)
		aff = Affine(matrix, translation)
		return aff


	def getCircle(self, useFirst):
		direction = self.m_center2 - self.m_center1
		center = self.m_center1
		radius = self.m_r1
		if not useFirst:
			center = self.m_center2
			radius = self.m_r2
		return Circle3(center, direction, radius)


	def containsPoint(self, point):
		"""
			return True, if point is on my defining surface
		""" 
		if self.m_r1 == self.m_r2:
			# we have a cylinder
			centerLine = Line(self.m_center1, self.m_center2)
			nearestPoint = centerLine.nearestPointTo(point)
			dist = point.distanceOfPoint(nearestPoint)
			return ZGeomItem.almostEqual(dist, self.m_r1)
		# ok, we have a real cone
		zeroCenter = self.getZeroCenter()
		if zeroCenter.isSameAs(point):
			return True
		pointLine = Line(zeroCenter, point)
		center1Plane = Plane(self.m_center1, normal=self.m_center1 - self.m_center2)
		intersect = center1Plane.intersect(pointLine)
		if intersect is None:
			return False
		return ZGeomItem.almostEqual(self.m_center1.distanceOfPoint(intersect), self.m_r1)



	def getZeroCenter(self):
		# return the point, where I get radius 0
		r1 = self.m_r1
		r2 = self.m_r2
		if r1 == r2:
			return None

		c1 = self.m_center1
		c2 = self.m_center2
		h = self.m_height
		
		if r1 == 0:
			return c1
		if r2 == 0:
			return c2

		if r1 > r2:
			r1, r2 = r2, r1
			c1, c2 = c2, c1

		# now r1 < r2
		#centerLine = Line(c1, c2)
		factor = h / (r2 - r1)
		centerUnit = (c1 - c2).unit()

		return c2 + centerUnit.scaledBy(r2 * factor)
		

	def ratioInnerToOuter(self):
		"""
			the cos of the opening angle
		"""
		return  self.m_height / self.m_distanceOutside


	def openingAngle(self):
		return math.acos(self.ratioInnerToOuter())


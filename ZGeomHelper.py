"""
	Contains only the class with the same name
"""

import math
from scipy.optimize import newton

#	several helping functions concerning geometry and paths

from zutils.ZGeom import ZGeomItem, Point, Line, Plane, Circle2, Circle3
from zutils.ZMatrix import Affine, Matrix
from zutils.ZPath import ZBezier3Segment, ZLineSegment
from zutils.ZD3Body import ZCone, ZCylinder


####################################################
####################################################


class ZGeomHelper:
	"""
		Some utility functions that use both ZGeom and ZMatrix.
		Only class functions are provided.
	"""
	@classmethod
	def angleBetween2(cls, center, point1, point2, cw):
		"""
			return a positive angle between 0 and 360
			How many degrees must i go from center->p1 to center->p2 clockwise (or ccw)
			All 3 points must be in x-y-plane
		"""
		p1 = (point1 - center)
		p2 = (point2 - center)

		angle = Affine.fullAngleBetween2d(p1, p2)
		if ZGeomItem.s_originIsTopLeft:
			angle = - angle
		if cw:
			return ZGeomItem.normalizeAngle(-angle)
		if angle == 0:
			return 0
		return ZGeomItem.normalizeAngle(angle)


	@classmethod
	def perpendicularToPointInPlane(cls, vect, plane=None):
		"""
			return a vector that is perpendicular to point and lies in plane
			default plane is x-y
		"""
		if plane is None:
			plane = Plane.alongAxes('x', 'y')
		line = Line(Point(), vect)
		ret = line.perpendicularLineThroughPointInPlane(vect, plane)
		return ret.m_direction


	@classmethod
	def findCommonPlaneAxisParallel(cls, pointList):
		"""
			find a plane that is axis parallel and contains all points of pointList (or None)
		"""
		# first find one coordinate that is equal for all points
		foundIdx = -1
		for ii in range(3):
			val = pointList[0][ii]
			foundIdx = ii
			for p in pointList:
				if not ZGeomItem.almostEqual(p[ii], val):
					foundIdx = -1
					break
			if foundIdx >= 0:
				break
		if foundIdx < 0:
			return None
		normal = Point()
		normal[foundIdx] = 1
		return Plane(pointList[0], normal=normal)


	@classmethod
	def findSuitableCenters(cls, p1, p2, r):
		"""
			find 2 points c1, c2 that have distance r from p1 and p2.
			p1 and p2 must lie in a plane that is axis parallel
		"""
		if p1.distanceOfPoint(p2) > (2 * r):
			raise Exception('distance of points is too large')
		plane = cls.findCommonPlaneAxisParallel([p1, p2])
		if plane is None:
			return None
		aff = Affine.morphPlaneToXY(plane, p1, p2)
		p1A = aff * p1
		p2A = aff * p2
		circle1 = Circle2(p1A, r)
		circle2 = Circle2(p2A, r)
		inter = circle1.intersect(circle2)
		affInverse = aff.inverted()
		return [affInverse * x for x in inter]


	@classmethod
	def makePseudoCirclePath(cls, points, theDistance, rad) -> list:
		"""
			Create a list of segments that approximates a circle with a bezier path going through the points.
			theDistance is the outerDistance that must also be met on the outer area
			(i.e. we must add 2 points that are on the outer area, but also on the approximated circle)
			and simulates the respective tangents
			Must be at least 3 points
			All points must lie in x-y-plane
			Returns an array of path segments.
		"""
		# check parameters
		for point in points:
			if not ZGeomItem.almostEqual(point.m_z, 0):
				point.printComment('not in x-y-plane')
				raise Exception('makePseudoCirclePath: all points must be in x-y-plane!')
			point.m_z = 0

		p1 = points[0]
		p2 = points[-1]
		if rad == 0:
			# non-rounded fretboard, just provide a simple dummy
			start = Point(theDistance, p1.m_y)
			if ZGeomItem.findNearestItem([p1, p2], start) == p2:
				start = Point(-start.m_x, p2.m_y)
			stop = Point(-start.m_x, p2.m_y)
			seg = ZLineSegment(start, stop)
			return [seg]

		# ok, we have a rounded fretboard
		# calulate the center of the circle
		p3 = points[round((len(points)-1)/2)]
		c1 = Circle2(p1, rad)
		c2 = Circle2(p2, rad)
		inter = c1.intersect(c2)
		# chose the intersection point, which makes sense for p3
		distances = [abs(x.distanceOfPoint(p3) - rad) for x in inter]
		center = inter[0] if distances[0] < distances[1] else inter[1]
		c3 = Circle2(center, rad)
		
		# now calculate the additional outer (dummy) points
		centerCirclePoint = (p1 + p2).scaledBy(0.5)
		centerLine = Line(center, centerCirclePoint)
		plane = Plane.alongAxes('x', 'y')
		parallelLines = centerLine.parallelLinesInPlane(plane, theDistance)

		line1 = ZGeomItem.findNearestItem(parallelLines, p1)
		inter = line1.intersect(c3)
		dummy1 = ZGeomItem.findNearestItem(inter, p1)
		
		line2 = ZGeomItem.findNearestItem(parallelLines, p2)
		inter = line2.intersect(c3)
		dummy2 = ZGeomItem.findNearestItem(inter, p2)

		# now we have all points on the segments:
		approxPoints = [dummy1]
		approxPoints.extend(points)
		approxPoints.append(dummy2)

		# now find the handle points between the approxPoints:
		handles = []
		for ii in range(len(approxPoints) - 1):
			app1 = approxPoints[ii]
			app2 = approxPoints[ii + 1]
			middle = (app1 + app2).scaledBy(0.5)
			line = Line(center, middle)
			inter = line.intersect(c3)
			handle = ZGeomItem.findNearestItem(inter, middle)
			handles.append(handle)

		# now we can create the bezier segments
		segs = []
		for ii in range(len(handles)):
			app1 = approxPoints[ii]
			app2 = approxPoints[ii + 1]
			handle = handles[ii]
			seg = ZBezier3Segment(app1, app2, handle, handle)
			segs.append(seg)

		return segs


	@classmethod
	def circle3FromThreePoints(cls, q1, q2, q3) -> Circle3:
		"""
			Return a circle that touches the 3 given points.
			Points need not be in x-y-plane (but must not be collinear)
		"""
		plane = Plane(q1, q2, q3)
		aff = Affine.morphPlaneToXY(plane, q1, q2)
		p1 = aff * q1
		p2 = aff * q2
		p3 = aff * q3
		circleXY = Circle2.circleFromThreePoints(p1, p2, p3)
		return Circle3(aff.inverted() * circleXY.m_center, plane.m_normal, circleXY.m_radius)


	@classmethod
	def intersectPlanes(cls, firstPlane, otherPlane) -> Line:
		# first check, if we are parallel:
		if firstPlane.m_normal.isSameAs(otherPlane.m_normal):
			return None
		if firstPlane.m_normal.isSameAs(-otherPlane.m_normal):
			return None
		# the resulting line is orthogonal to self and plane:
		lineDirection = firstPlane.m_normal.crossProduct(otherPlane.m_normal, 1)
		# now we need to find ONE point in the intersection:
		# we try to find one on one "x-y-z" plane:
		#test = [1, 1, 1]
		zeroableIdx = -1
		for ii in range(3):
			if abs(lineDirection[ii]) > 0.33:
				#test[ii] = 0
				zeroableIdx = ii
				break
		ll1 = firstPlane.m_normal
		ll2 = otherPlane.m_normal
		target = Point(firstPlane.m_d, otherPlane.m_d)

		if zeroableIdx == 0:
			# a value of x=0 is possible
			l1 = Point(ll1.m_y, ll1.m_z)
			l2 = Point(ll2.m_y, ll2.m_z)
			matrix = Matrix([l1, l2])
			solved = matrix.solve(target)
			onePoint = Point(0, solved.m_x, solved.m_y)
		elif zeroableIdx == 1:
			# a value of y=0 is possible
			l1 = Point(ll1.m_x, ll1.m_z)
			l2 = Point(ll2.m_x, ll2.m_z)
			matrix = Matrix([l1, l2])
			solved = matrix.solve(target)
			onePoint = Point(solved.m_x, 0, solved.m_y)
		else:
			# a value of z=0 is possible
			l1 = Point(ll1.m_x, ll1.m_y)
			l2 = Point(ll2.m_x, ll2.m_y)
			matrix = Matrix([l1, l2])
			solved = matrix.solve(target)
			onePoint = Point(solved.m_x, solved.m_y, 0)
		return Line(onePoint, onePoint + lineDirection)
	

	@classmethod
	def findCircle2FromPointLineCircle2(cls, point, line, circle2, startPoint=None) -> Circle2:
		'''
			return a Circle2, so that
			- it contains point
			- its center is on line
			- it touches circle2 from the outside
		'''
		if startPoint is None:
			startPoint = circle2.m_center
		startPoint = line.nearestPointTo(startPoint)
		startLambda = line.lambdaForPoint(startPoint)
		# use the parametric line description:
		p1 = line.m_p1
		dire = line.m_direction
		c2 = circle2.m_center
		rad = circle2.m_radius
		direSquared = dire.lengthSquared()
		

		factor1 = 2*(p1.m_x*dire.m_x - dire.m_x*point.m_x + p1.m_y*dire.m_y - dire.m_y*point.m_y)
		factor2 = 2*(p1.m_x*dire.m_x - dire.m_x*c2.m_x + p1.m_y*dire.m_y - dire.m_y*c2.m_y)
		const1 = p1.lengthSquared() + point.lengthSquared() - 2*(p1.m_x*point.m_x + p1.m_y * point.m_y)
		const2 = p1.lengthSquared() + c2.lengthSquared() - 2*(p1.m_x*c2.m_x + p1.m_y * c2.m_y)

		#	let t be the searched parameter on the line
		func = lambda t: (
			math.sqrt(t*t*direSquared + t*factor1 + const1) -
			math.sqrt(t*t*direSquared + t*factor2 + const2) -
			rad
		)

		newtonT = newton(func, startLambda)
		if newtonT is None:
			return None
		
		# now make the solution
		foundCenter = line.pointForLambda(newtonT)
		foundRadius = foundCenter.distanceOfPoint(point)

		# check the solution:
		dist1 = foundCenter.distanceOfPoint(point)
		dist2 = foundCenter.distanceOfPoint(c2) + rad
		if not ZGeomItem.almostEqual(dist1, dist2):
			raise Exception(f'findCircle2FromPointLineCircle2: solution wrong by {dist1 - dist2}')
			print(f'findCircle2FromPointLineCircle2: solution wrong by {dist1 - dist2} ===========================')
			print(f'func() value: {func(newtonT)} ================================')

		return Circle2(foundCenter, foundRadius)
	

##############################################################



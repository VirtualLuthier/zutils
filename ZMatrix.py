"""
	Contains classes
	- Matrix
	- Affine
"""

from __future__ import annotations
import numbers
import math


from zutils.ZGeom import ZGeomItem, Point, Line, Plane, Circle2, Ellipse3


##########################################


class Matrix(ZGeomItem):
	def __init__(self, pointList=None):
		"""
			Return a matrix with the given line vectors.
			If no argument is given return the identity matrix
			If argument is a number, return a scaling matrix
		"""
		# the points are the lines
		factor = math.nan
		if pointList is None:
			factor = 1
		if isinstance(pointList, numbers.Number):
			factor = pointList
		if not math.isnan(factor):
			pointList = []
			for ii in range(3):
				p = Point()
				p[ii] = factor
				pointList.append(p)
				#print(p)
		self.m_lines = pointList
		self.m_determinant = math.nan


	@classmethod
	def makeEulerRotation(cls, angleDegrees, rotAxisName) -> Matrix:
		"""
			Return a rotation matrix in one main plane.
			rotAxisName is the name  of the rotation axis (use x, y, or z)
		"""
		if math.isnan(angleDegrees):
			raise Exception('math.nan is an illegal angle')
		radians = math.radians(angleDegrees)
		cos = math.cos(radians)
		sin = math.sin(radians)
		if rotAxisName == 'x':
			# rotate around x axis
			points = [Point(1, 0, 0), Point(0, cos, -sin), Point(0, sin, cos)]
		elif rotAxisName == 'y':
			# rotate around y axis
			points = [Point(cos, 0, sin), Point(0, 1, 0), Point(-sin, 0, cos)]
		elif rotAxisName == 'z':
			# rotate around z axis
			points = [Point(cos, -sin, 0), Point(sin, cos, 0), Point(0, 0, 1)]
		return Matrix(points)


	@classmethod
	def makeOrthonormalTransformation(cls, px: Point=None, py: Point=None, pz: Point=None) -> Matrix:
		"""
			Return a orthonormal matrix that transforms (1, 0, 0) to px (normalized),  ...
			If only 1 or 2 argument is given, random rest args are created.
		"""
		done = ''
		found = []
		if px is not None:
			tx = px.unit()
			done = done + 'x'
			found.append(tx)
		if py is not None:
			ty = py.unit()
			done = done + 'y'
			found.append(ty)
		if pz is not None:
			tz = pz.unit()
			done = done + 'z'
			found.append(tz)
		if len(done) == 0:
			raise Exception('at least one target vector must be given')
		falseOnes = Point.checkMutuallyPerpendicular(found)
		if falseOnes is not None:
			raise Exception('input points are not perpendicular:' + str(falseOnes))
		if len(done) == 1:
			line = Line(Point(), found[0])
			otherLine = line.anyPerpendicularLineThrough(Point())
			otherPoint = otherLine.m_direction.unit()
			if done.find('x') < 0:
				tx = otherPoint
				done = done + 'x'
			elif done.find('y') < 0:
				ty = otherPoint
				done = done + 'y'
			else:
				tz = otherPoint
				done = done + 'z'

		# so we have 2 vectors set
		if done in ('xy', 'yx'):
			tz = tx.crossProduct(ty).unit()
		elif done in ('xz', 'zx'):
			ty = tz.crossProduct(tx).unit()
		else:
			# done in ('yz', 'zy')
			tx = ty.crossProduct(tz).unit()

		return Matrix([tx, ty, tz]).inverted()


	@classmethod
	def makeBaseTransformation(cls, src1: Point, src2: Point, src3: Point, trg1: Point, trg2: Point, trg3: Point) -> Matrix:
		"""
			Return a Matrix that transforms the src points to the trg points.
			Both groups must be linearly independent, but not neccessarily orthonormal.
		"""
		m1I = Matrix([src1, src2, src3]).transposed()
		m1 = m1I.inverted()
		m2 = Matrix([trg1, trg2, trg3]).transposed()
		return m2 * m1


	@classmethod
	def makeScaleMatrix(cls, fx: float, fy: float, fz: float) -> Matrix:
		"""
			Returns a Matrix that scales the x-y-z coordinates with the given factors
		"""
		px = Point(1)
		py = Point(0, 1)
		pz = Point(0, 0, 1)
		return cls.makeBaseTransformation(px, py, pz, px.scaledBy(fx), py.scaledBy(fy), pz.scaledBy(fz))


	def getDeterminant(self) -> float:
		# caution: determinant is cached.
		# after changing any value it is obsolete!
		if not math.isnan(self.m_determinant):
			return self.m_determinant
		line = self.m_lines[0]
		a, b, c = line.m_x, line.m_y, line.m_z
		line = self.m_lines[1]
		d, e, f = line.m_x, line.m_y, line.m_z
		line = self.m_lines[2]
		g, h, i = line.m_x, line.m_y, line.m_z
		det = a*e*i + b*f*g + c*d*h - c*e*g - b*d*i - a*f*h
		self.m_determinant = det
		return det


	def preservesOrientation(self) -> bool:
		return self.getDeterminant() > 0


	def isInvertible(self) -> bool:
		return self.getDeterminant() != 0
		

	def printComment(self, comment, tabs=0, num=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(num))}')


	def rounded(self, num=2) -> Matrix:
		ps = []
		for line in self.m_lines:
			ps.append(line.rounded(num))
		return Matrix(ps)


	def numLines(self) -> int:
		return len(self.m_lines)


	def numColumns(self) -> int:
		return len(self.m_lines[0])


	def isSameAs(self, other) -> bool:
		for ii in range(self.numLines()):
			if not self.m_lines[ii].isSameAs(other.m_lines[ii]):
				return False
		return True


	def solve(self, target) -> Point:
		if self.numLines() == 2:
			ret = self.solve2(target)
		self.checkResult(target, ret)
		return ret


	def solve2(self, target) -> Point:
		l1 = self.m_lines[0]
		l2 = self.m_lines[1]
		l11 = l1.m_x
		l12 = l1.m_y
		l21 = l2.m_x
		l22 = l2.m_y
		deter = l11 * l22 - l21 * l12
		if abs(deter) < 0.01:
			return None
		d1 = target.m_x
		d2 = target.m_y
		y = (l11 * d2 - l21 * d1) / deter
		if l11 != 0:
			x = (d1 - l12 * y) / l11
		else:
			x = (d2 - l22 * y) / l21
		return Point(x, y)


	def __mul__(self, other):
		numLines = self.numLines()
		if isinstance(other, numbers.Number):
			factor = other
			retLines = []
			for ii in range(numLines):
				p = self.m_lines[ii].scaledBy(factor)
				retLines.append(p)
			ret = Matrix(retLines)
			return ret
		if isinstance(other, Point):
			vector = other
			ret = Point()
			for ii in range(numLines):
				theSum = self.m_lines[ii] * vector
				ret[ii] = theSum
			return ret
		if isinstance(other, Matrix):
			matrix = other
			retLines = []
			for ii in range(numLines):
				p = Point()
				line = self.m_lines[ii]
				for jj in range(matrix.numColumns()):
					p[jj] = line * matrix.column(jj)
				retLines.append(p)
			ret = Matrix(retLines)
			return ret


	def __add__(self, other) -> Matrix:
		numLines = self.numLines()
		retLines = []
		for ii in range(numLines):
			p = self.m_lines[ii] + other.m_lines[ii]
			retLines.append(p)
		ret = Matrix(retLines)
		return ret


	def __sub__(self, other) -> Matrix:
		return self + (other*-1)


	def __str__(self) -> str:
		ret = 'Matrix('
		for ii in range(self.numLines()):
			ret = ret + str(self.m_lines[ii]) + ', '
		ret = ret + ')'
		return ret			


	def column(self, idx) -> Point:
		ret = Point()
		for ii in range(self.numLines()):
			ret[ii] = self.m_lines[ii][idx]
		return ret


	def checkResult(self, target, solution) -> bool:
		test = self * solution
		if not target.isSameAs(test):
			print('matrix resolve test')


	def inverse2D(self) -> Matrix:
		l = self.m_lines[0]
		m00 = l[0]
		m10 = l[1]
		l = self.m_lines[1]
		m01 = l[0]
		m11 = l[1]
		det = m00*m11 - m01*m10
		if det == 0:
			print('matrix is not invertible')
			return None

		i11 = m11 / det
		i12 = -m01 / det
		p1 = Point(i11, i12)
		i21 = m10 / det
		i22 = m11 / det
		p2 = Point(i21, i22)

		inverse = Matrix([p1, p2])
		return inverse


	def inverted(self) -> Matrix:
		l = self.m_lines[0]
		m00 = l[0]
		m10 = l[1]
		m20 = l[2]
		l = self.m_lines[1]
		m01 = l[0]
		m11 = l[1]
		m21 = l[2]
		l = self.m_lines[2]
		m02 = l[0]
		m12 = l[1]
		m22 = l[2]
		det = m00*m11*m22 + m01*m12*m20 + m02*m10*m21 - m00*m12*m21 - m01*m10*m22 - m02*m11*m20
		if det == 0:
			print('matrix is not invertible')
			return None
		i11 = (m11*m22 - m12*m21) / det
		i12 = (m12*m20 - m10*m22) / det
		i13 = (m10*m21 - m11*m20) / det
		p1 = Point(i11, i12, i13)

		i21 = (m02*m21 - m01*m22) / det
		i22 = (m00*m22 - m02*m20) / det
		i23 = (m01*m20 - m00*m21) / det
		p2 = Point(i21, i22, i23)

		i31 = (m01*m12 - m02*m11) / det
		i32 = (m02*m10 - m00*m12) / det
		i33 = (m00*m11 - m01*m10) / det
		p3 = Point(i31, i32, i33)

		inverse = Matrix([p1, p2, p3])
		return inverse


	def transposed(self) -> Matrix:
		lines = []
		for ii in range(self.numColumns()):
			lines.append(self.column(ii))
		return Matrix(lines)


	def isOrthonormal(self) -> bool:
		return (self * self.transposed()).isSameAs(Matrix())


	def getEulerAngles(self) -> list:
		"""
			we assume, that I am orthonormal
			for x-rotation, then y-rotation, then z-rotation
			see https://www.geometrictools.com/Documentation/EulerAngles.pdf
		"""
		p0 = self.m_lines[0]
		r00 = p0.m_x
		r01 = p0.m_y		# not used ??
		r02 = p0.m_z		# not used ??
		p1 = self.m_lines[1]
		r10 = p1.m_x
		r11 = p1.m_y
		r12 = p1.m_z
		p2 = self.m_lines[2]
		r20 = p2.m_x
		r21 = p2.m_y
		r22 = p2.m_z
		
		if r20 < 0.9999:
			if r20 > -0.9999:
				ay = math.degrees(math.asin(-r20))
				az = math.degrees(math.atan2(r10, r00))
				ax = math.degrees(math.atan2(r21, r22))
			else:
				# r20 = -1
				ay = 90
				az = math.degrees(-math.atan2(-r12, r11))
				ax = 0
		else:
			# r20 =-1
			ay = -90
			az = math.degrees(math.atan2(-r12, r11))
			ax = 0
		
		return [ax, ay, az]


#########################################################
#########################################################


class Affine(ZGeomItem):
	"""
		Represents an affine transformation (a matrix and a shift)
	"""
	def __init__(self, matrix=None, point=Point()):
		if matrix is None:
			matrix = Matrix()
		self.m_matrix = matrix
		self.m_shift = point


	@classmethod
	def makeRotationAffine(cls, line, angleDegrees) -> Affine:
		"""
			Return an Affine, that describes a rotation around line.
			Caution: depends on the orientation of line direction  !!!
		"""
		#	- shift the line through the origin
		#	- make base transform to map line direction to z-Axis
		#	- rotate around z-axis
		#	- revert base transformation
		#	- shift the line back to its real position

		point = line.m_p1
		affineShift = Affine(None, -point)
		matrix = Matrix.makeOrthonormalTransformation(pz=line.m_direction).inverted()
		affineBaseTransform = Affine(matrix)
		ret = affineBaseTransform * affineShift
		rotMatrixXY = Matrix.makeEulerRotation(angleDegrees, 'z')	# rotation in x-y plane
		affineRot = Affine(rotMatrixXY)
		ret = affineRot * ret
		affineBaseTransformInverse = affineBaseTransform.inverted()
		ret = affineBaseTransformInverse * ret
		affineShiftBack = Affine(None, point)
		ret = affineShiftBack * ret
		return ret

	@classmethod
	def morphPlaneToXY(cls, plane, point0, pointX) -> Affine:
		"""
			Return an Affine that transforms (orthonormally) the plane to the 
			X-Y-plane (point0 and pointX must lie on plane!), so that point0 goes to the origin.
			pointX goes onto the X axis somewhere. To avoid rounding errors on z, use of Point.flattened() is recommended.
		"""
		if not plane.containsPoint(point0) or not plane.containsPoint(pointX):
			raise Exception('illegal point given for morphPlaneToXY()')
		offsetX = (pointX - point0).unit()
		normal = plane.m_normal.unit()
		matrix = Matrix.makeOrthonormalTransformation(px=offsetX, pz=normal)
		matrix = matrix.inverted()
		affTrans = Affine(None, -point0)
		affOrtho = Affine(matrix)
		return affOrtho * affTrans


	@classmethod
	def fullAngleBetween2d(cls, p1, p2) -> float:
		"""
			Which angle is from p1 to p2?
			is not really signed, but it returns a value between 0 and 360
			positive angles mean ccw
			could surely be more elegant
			works only in x-y-plane
		"""
		a = p1.angleTo(p2)
		p1 = p1.unit()
		p2 = p2.unit()
		line = Line(Point(), Point(0, 0, 1))
		testAngles = [a, 180 - a, 180 + a, 360 - a]
		for angle in testAngles:
			aff = cls.makeRotationAffine(line, angle)
			p1_ = aff * p1
			if p1_.isSameAs(p2):
				return angle
		raise Exception('could not find angle')


	@classmethod
	def makeMirror(cls, plane: Plane) -> Affine:
		"""
			Return an Affine that mirrors by the given plane.
		"""
		p1, p2, _ = plane.getThreePoints()
		morph = Affine.morphPlaneToXY(plane, p1, p2)
		# make a matrix that mirrors in z
		mat = Matrix()
		mat.m_lines[2][2] = -1
		affMirror = Affine(mat)
		return morph.inverted() * (affMirror * morph)


	@classmethod
	def morphLineToLine(cls, line1: Line, line2: Line, p1: Point=None, p2: Point=None) -> Affine:
		"""
			Returns an Affine that transforms line1 to line2.
			p1 is transformed to p2 (both must lie on their respective line)
			If p1 or p2 are None, the lines' m_p1 points are used
		"""
		if p1 is None:
			p1 =line1.m_p1
		if p2 is None:
			p2 = line2.m_p1
		if not line1.containsPoint(p1) or not line2.containsPoint(p2):
			raise Exception('both points must lie on their Line')

		# make the point shift:
		trans = Affine(None, p2 - p1)

		if line1.isParallel(line2):
			return trans

		dir1 = line1.m_direction
		dir2 = line2.m_direction
		angle = dir1.angleTo(dir2)
		rotLine = Line(p2, direction=dir1.crossProduct(dir2))
		testP1 = p2 + dir1

		rotAff = cls.makeRotationAffine(rotLine, angle)
		if line2.containsPoint(rotAff * testP1):
			return rotAff * trans

		rotAff = cls.makeRotationAffine(rotLine, -angle)
		if line2.containsPoint(rotAff * testP1):
			return rotAff * trans

		raise Exception('cannot find rotation angle')


	@classmethod
	def makePointMirror(cls, point=None) -> Affine:
		"""
			Return an Affine that mirrors through the given point.
			If point is None, use the zero point
		"""
		ret = Affine(Matrix(-1))
		if point is None:
			return ret
		return Affine(None, point) * ret * Affine(None, -point)


	def isOrthonormal(self) -> bool:
		return self.m_matrix.isOrthonormal()


	def getFloatListString(self, numFormat, numArray) -> list:
		"""
			used to get rid of the -0.00 stuff
		"""
		arr = []
		for x in numArray:
			if round(x, 3) == 0:
				x = 0
			arr.append(x)
		return numFormat % tuple(arr)


	def xmlCoords(self, formatString='[%f, %f, %f, %f]') -> str:
		m = self.m_matrix
		s = self.m_shift
		val = ''
		for ii in range(3):
			p = m.m_lines[ii]
			val += self.getFloatListString(formatString, [p.m_x, p.m_y, p.m_z, s[ii]])
			val += ', '
		val += '[0, 0, 0, 1]'
		return val


	def printComment(self, comment, tabs=0, num=2):
		self.printTabs(tabs)
		print(f'{comment}: {str(self.rounded(num))}')


	def isInvertible(self) -> bool:
		return self.m_matrix.isInvertible()


	def rounded(self, num=2) -> Affine:
		return Affine(self.m_matrix.rounded(num), self.m_shift.rounded(num))


	def apply(self, point) -> Point:
		return self.m_matrix * point + self.m_shift


	def applyLine(self, line) -> Line:
		return Line(self * line.m_p1, self * line.m_p2)


	def applyPlane(self, plane) -> Plane:
		(p1, p2, p3) = plane.getThreePoints()
		return Plane(self * p1, self * p2, self * p3)


	def applyCircle2(self, circle2) -> Circle2:
		c = circle2.m_center
		p = c + Point(circle2.m_radius)
		c2 = self.apply(c)
		p2 = self.apply(p)
		r2 = c2.distanceOfPoint(p2)
		return Circle2(c2, r2)


	#def applyEllipse3(self, ellipse3) -> Ellipse3:
	#	wrong implementation!!!
	#	c = ellipse3.m_center
	#	p1 = ellipse3.m_vert1
	#	p2 = ellipse3.m_vert2
	#	cn = self.apply(c)
	#	p1n = self.apply(p1)
	#	p2n = self.apply(p2)
	#	return Ellipse3(cn, vert1=p1n, vert2=p2n)


	def inverted(self) -> Affine:
		inv = self.m_matrix.inverted()
		point = - (inv * self.m_shift)
		return Affine(inv, point)


	def __mul__(self, other):
		if isinstance(other, Point):
			return self.apply(other)
		if isinstance(other, Line):
			return self.applyLine(other)
		if isinstance(other, Plane):
			return self.applyPlane(other)
		if isinstance(other, Circle2):
			return self.applyCircle2(other)
		#if isinstance(other, Ellipse3):
		#	return self.applyEllipse3(other)
		if isinstance(other, Affine):
			return self.concat(other)
		raise Exception('illegal argument for Affine multiplication: ' + str(other))


	def __str__(self):
		ret = 'Affine('
		ret = ret + str(self.m_matrix) + ', shift='
		ret = ret + str(self.m_shift)
		ret = ret + ')'
		return ret	


	def concat(self, other) -> Affine:
		mat = self.m_matrix * other.m_matrix
		shift = self .m_matrix * other.m_shift + self.m_shift
		return Affine(mat, shift)


	def isSameAs(self, other) -> bool:
		return self.m_matrix.isSameAs(other.m_matrix) and self.m_shift.isSameAs(other.m_shift)


	def isTranslation(self) -> bool:
		return self.m_matrix.isSameAs(Matrix())
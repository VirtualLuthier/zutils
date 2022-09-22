
import math
import unittest
#import sys
#sys.path.append('.')

from context import zutils		#, testInFolder, testOutFolder


from zutils.ZGeom import ZGeomItem, Point, Plane, Line, Polygon, Circle2, Ellipse3
from zutils.ZGeomHelper import ZGeomHelper
from zutils.ZMatrix import Matrix, Affine
from zutils.ZD3Body import  ZCylinder, ZCone, ZBall3d


class TestZGeom(unittest.TestCase):

	@classmethod
	def exampleMatrixInvertible(cls):
		# matrix and inverse
		m = Matrix([Point(0, -3, -2), Point(1, -4, -2), Point(-3, 4, 1)])
		i = Matrix([Point(4, -5, -2), Point(5, -6, -2), Point(-8, 9, 3)])
		return [m, i]


	@classmethod
	def exampleMatrixOrthogonal(cls):
		#return Matrix([Point(0, -3, -2), Point(1, -4, -2), Point(-3, 4, 1)])
		p1 = Point(0.96, -0.00, 0.29).unit()
		p3 = Point(-0.29, 0.00, 0.96).unit()
		return Matrix([p1, Point(0.00, 1.00, 0.00), p3])


######################################################


	def test_unit(self):
		p = Point(3, 5, 7)
		l = p.unit().length()
		self.assertAlmostEqual(l, 1.0)


	def test_angleBetweenPoints(self):
		p1 = Point(1, 0, 0)
		p2 = Point(1, 1, 0)
		angle = p1.angleTo(p2)
		self.assertAlmostEqual(angle, 45)


	def test_isCollinear(self):
		p1 = Point(2, 4, 6)
		p2 = Point(4, 8, 12)
		p3 = Point(-4, -8, -12)
		self.assertTrue(p1.isCollinear(p1))
		self.assertTrue(p1.isCollinear(p2))
		self.assertTrue(p1.isCollinear(p3))


	def test_isPerpendicular(self):
		p1 = Point(2, 0, 0)
		p2 = Point(0, 8, 1)
		self.assertTrue(p1.isPerpendicular(p2))


	def test_orientation(self):
		px = Point(1, 0, 0)
		py = Point(0, 1, 0)
		pz = Point(0, 0, 1)
		self.assertTrue(px.crossProduct(py).isSameAs(pz))
		self.assertTrue(py.crossProduct(pz).isSameAs(px))
		self.assertTrue(pz.crossProduct(px).isSameAs(py))


	def test_containsPointLine(self):
		line = Line(Point(), Point(1))
		p1 = Point(8)
		self.assertTrue(line.containsPoint(p1))


	def test_planeConstructor(self):
		plane = Plane(Point(1, 1, 1), normal=Point(1, 0, 0))
		(_, p2, p3) = plane.getThreePoints()
		self.assertTrue(plane.containsPoint(p2))
		self.assertTrue(plane.containsPoint(p3))



	def test_isParallelLines(self):
		line1 = Line(Point(0, 0, 0), Point(1, 0, 0))
		line2 = Line(Point(1, 1, 1), Point(-2, 1, 1))
		self.assertTrue(line1.isParallel(line2))


	def test_isParallelPlanes(self):
		plane1 = Plane(Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0))
		plane2 = Plane(Point(1, 1, 1), Point(2, 1, 1), Point(1, 2, 1))
		self.assertTrue(plane1.isParallel(plane2))


	def test_containsPointPlane(self):
		plane = Plane(Point(1, 0, 0), Point(1, 1, 0), Point(1, 0, 1))
		p1 = Point(1, 8, 16)
		self.assertTrue(plane.containsPoint(p1))


	def test_matrix2(self):
		matrix2 = Matrix([Point(0, 1), Point(1, 0)])
		target = Point(2, 1)
		solv = matrix2.solve(target)
		test = matrix2 * solv
		self.assertTrue(target.isSameAs(test))


	def test_nearestPointsOf2Lines1(self):
		l1 = Line(Point(), direction=Point(1))
		l2 = Line(Point(0, 0, 1), Point(0, 1))
		nearest1 = l1.nearestPointsToLine(l2)
		dist1 = (nearest1[0] - nearest1[1]).length()
		nearest2 = l2.nearestPointsToLine(l1)
		dist2 = (nearest2[0] - nearest2[1]).length()
		self.assertTrue(dist1 > 0.1)
		self.assertAlmostEqual(dist1, dist2)
		for p in nearest1:
			found = False
			for p2 in nearest2:
				if p.isSameAs(p2):
					found = True
					break
			self.assertTrue(found)


	def test_nearestPointsOf2Lines2(self):
		"""
			https://www.mathematik-oberstufe.de/vektoren/a/abstand-gerade-ws-lot-hilfsebene.html
		"""
		l1 = Line(Point(-7, 2, -3), direction=Point(0, 1, 2))
		l2 = Line(Point(-3, -3, 3), direction=Point(1, 2, 1))
		nearest1 = l1.nearestPointsToLine(l2)
		dist1 = (nearest1[0] - nearest1[1]).length()
		self.assertAlmostEqual(dist1, math.sqrt(56))
		nearest2 = [Point(-7, 5, 3), Point(-1, 1, 5)]
		for p in nearest1:
			found = False
			for p2 in nearest2:
				if p.isSameAs(p2):
					found = True
					break
			self.assertTrue(found)


	def test_lineLineIntersection(self):
		line1 = Line(Point(0, 1, 1), direction=Point(1, 1, 0))
		line2 = Line(Point(2, 3, 1), direction=Point(3, 4, 0))
		inter = line1.intersect(line2)
		self.assertFalse(inter is None)
		self.assertTrue(line1.containsPoint(inter))
		self.assertTrue(line2.containsPoint(inter))


	def test_lineParams(self):
		line = Line(Point(1, 2, 3), Point(4, 3, 2))
		for axis in 'xyz':
			params = line.condenseEquations(axis)
			#print('axis: ' + params[0])
			p = line.getPointForParamSet(params, 100)
			#p.printComment('params')
			self.assertTrue(line.containsPoint(p))


	def test_planeLineIntersection(self):
		plane = Plane(Point(1, 1, 1), normal=Point(1.0, 0, 0))
		line = Line(Point(5, 5, 5), direction=Point(-1, 1, 1))
		inter = line.intersect(plane)
		self.assertFalse(inter is None)
		self.assertTrue(line.containsPoint(inter))
		self.assertTrue(plane.containsPoint(inter))


	def test_planePlaneIntersection(self):
		# example from Wikipedia: https://de.wikipedia.org/wiki/Schnittgerade
		p11 = Point(1, -1, 1)
		d11 = Point(2, 1, -1)
		d12 = Point(-1, 1, 0)
		plane1 = Plane(p11, p11 + d11, p11 + d12)

		p21 = Point(1, 1, 1)
		d21 = Point(2, 2, -1)
		d22 = Point(1, 0, 1)
		plane2 = Plane(p21, p21 + d21, p21 + d22)

		inter = plane1.intersect(plane2)	# own calculation
		solP = Point(-3, -3, 3)
		solD = Point(-7, -8, 5)
		solution = Line(solP, solP + solD)	# according to wikipedia

		self.assertTrue(inter.isSameAs(solution))


	def test_Polygon(self):
		p1 = Point()
		p2 = Point(1)
		p3 = Point(0, 1)
		poly = Polygon([p1, p2, p3, p1])
		self.assertEqual(len(poly.m_points), 3)
		self.assertEqual(poly.area(), 0.5)
		poly2 = poly.insetBy(1)
		self.assertEqual(len(poly2.m_points), 3)
		self.assertGreater(poly2.area(), poly.area())
		#print(poly2)
		p4 = Point(1, 1)
		poly = Polygon([p1, p2, p4, p3])
		self.assertEqual(poly.area(), 1.0)
		self.assertEqual(len(poly.m_points), 4)
		poly2 = poly.insetBy(-0.1)
		#print(poly2)
		self.assertEqual(len(poly2.m_points), 4)
		self.assertLess(poly2.area(), poly.area())


	def test_matrixAddMult(self):
		ide = Matrix()
		theSum = ide + ide
		theSum = theSum * 0.5
		self.assertTrue(theSum.isSameAs(ide))
		ide2 = ide * ide
		self.assertTrue(ide2.isSameAs(ide))
		ide2 = ide + Matrix(0)
		self.assertTrue(ide2.isSameAs(ide))


	def test_matrixInversion1(self):
		(m, realInverse) = TestZGeom.exampleMatrixInvertible()
		myInverse = m.inverted()
		self.assertTrue(myInverse.isSameAs(realInverse))
		p = m * myInverse
		self.assertTrue(p.isSameAs(Matrix()))
		detM = m.getDeterminant()
		detI = myInverse.getDeterminant()
		self.assertAlmostEqual(detM, (1.0 / detI))


	def test_matrixInversion2(self):
		m = Matrix()
		mI = m.inverted()
		self.assertTrue(mI.isSameAs(m))
		m = Matrix([Point(1, 0, 0), Point(0, 1, 1), Point(0, 0, 1)])
		mI = m.inverted()
		p = m * mI
		self.assertTrue(p.isSameAs(Matrix()))


	def test_matrixTranspose(self):
		m = TestZGeom.exampleMatrixOrthogonal() #Matrix([Point(0, -3, -2), Point(1, -4, -2), Point(-3, 4, 1)])
		m2 = m.transposed().transposed()
		self.assertTrue(m.isSameAs(m2))
		m = Matrix()
		m2 = m.transposed()
		self.assertTrue(m.isSameAs(m2))


	def testMatrixBaseTransform(self):
		src1 = Point(1, 2)
		src2 = Point(1, -3)
		src3 = Point(2, 3, 10)
		trg1 = Point(0, 3)
		trg2 = Point(2, 4, 8)
		trg3 = Point(0, -1, -3)
		m = Matrix.makeBaseTransformation(src1, src2, src3, trg1, trg2, trg3)
		self.assertTrue((m * src1).isSameAs(trg1))
		self.assertTrue((m * src2).isSameAs(trg2))
		self.assertTrue((m * src3).isSameAs(trg3))


	def test_matrixOrtogonal(self):
		m = TestZGeom.exampleMatrixOrthogonal()
		self.assertTrue(m.isOrthonormal())


	def test_affineInverse(self):
		(m, _) = TestZGeom.exampleMatrixInvertible()
		shift = Point(1, 2, 3)
		affin = Affine(m, shift)
		inverseAffin = affin.inverted()
		mult = inverseAffin * affin
		ide = Affine()
		self.assertTrue(mult.isSameAs(ide))
		shift2 = affin * shift
		shift3 = inverseAffin * shift2
		self.assertTrue(shift.isSameAs(shift3))


	def test_makeOrthonormalTransformation(self):
		px = Point(1, 1, 1)
		m = Matrix.makeOrthonormalTransformation(px=px)
		self.assertTrue(m.isOrthonormal())
		self.assertTrue(m * Point(1).isSameAs(px.unit()))

		py = px.anyPerpendicularPoint()
		m = Matrix.makeOrthonormalTransformation(px=px, py=py)
		self.assertTrue(m.isOrthonormal())
		self.assertTrue(m * Point(1).isSameAs(px.unit()))
		self.assertTrue(m * Point(0, 1).isSameAs(py.unit()))

		pz = px.crossProduct(py)
		m = Matrix.makeOrthonormalTransformation(px=px, py=py, pz=pz)
		self.assertTrue(m.isOrthonormal())
		self.assertTrue(m * Point(1).isSameAs(px.unit()))
		self.assertTrue(m * Point(0, 1).isSameAs(py.unit()))
		self.assertTrue(m * Point(0, 0, 1).isSameAs(pz.unit()))


	def test_lineRotation(self):
		p = Point(1, 1)
		dire = Point(1, 0, 2)
		line = Line(p, direction=dire)
		rot = Affine.makeRotationAffine(line, 30)
		pout = Point(5, 5, 5)
		self.assertFalse(line.containsPoint(pout))		
		pout2 = rot * pout
		nearest = line.nearestPointTo(pout)
		v1 = pout - nearest
		v2 = pout2 - nearest
		angle = v1.angleTo(v2)
		self.assertAlmostEqual(angle, 30)


	def test_eulerAngles(self):
		self.tryEulerAngles(32, 15, 27)


	def testSignedAngle(self):
		rad = math.radians(30)
		s = math.sin(rad)
		c = math.cos(rad)

		p1 = Point(0, 1)
		p2 = Point(c, s)
		p3 = Point(-s, -c)
		self.assertAlmostEqual(Affine.fullAngleBetween2d(p1, p2), 300)
		self.assertAlmostEqual(Affine.fullAngleBetween2d(p2, p1), 60)
		self.assertAlmostEqual(Affine.fullAngleBetween2d(p1, p3), 150)


	def test_AffinemorphPlaneToXY(self):
		p0 = Point(1, 1, 1)
		plane = Plane(p0, normal=p0)
		pDiffx = Point(1, -1)
		pX = p0 + pDiffx
		aff = Affine.morphPlaneToXY(plane, p0, pX)
		p0t = aff * p0
		self.assertTrue(p0t.isSameAs(Point()))
		pXt = (aff * pX).unit()
		#pXt.printComment('pXt')
		self.assertTrue(pXt.isSameAs(Point(1)))


	def test_affineApplyLine(self):
		p1 = Point(1, 1, 1)
		p2 = Point(2, 3, 4)
		line = Line(p1, p2)
		(m, _) = TestZGeom.exampleMatrixInvertible()
		shift = Point(1, 2, 3)
		affine = Affine(m, shift)
		line2 = affine * line
		p1X = affine * p1
		p2X = affine * p2
		self.assertTrue(line2.containsPoint(p1X))
		self.assertTrue(line2.containsPoint(p2X))


	def test_affineApplyPlane(self):
		p1 = Point(1, 1, 1)
		normal = Point(2, 3, 4)
		plane = Plane(p1, normal=normal)
		(m, _) = TestZGeom.exampleMatrixInvertible()
		shift = Point(1, 2, 3)
		affine = Affine(m, shift)
		plane2 = affine * plane
		(_, p2, p3) = plane.getThreePoints()

		p1X = affine * p1
		p2X = affine * p2
		p3X = affine * p3
		self.assertTrue(plane2.containsPoint(p1X))
		self.assertTrue(plane2.containsPoint(p2X))
		self.assertTrue(plane2.containsPoint(p3X))


	def test_circle3FromThreePoints(self):
		p1 = Point(1)
		p2 = Point(2, 3)
		p3 = Point(4, 5, 6)
		circle3 = ZGeomHelper.circle3FromThreePoints(p1, p2, p3)
		self.assertTrue(circle3.containsPoint(p1))
		self.assertTrue(circle3.containsPoint(p2))
		self.assertTrue(circle3.containsPoint(p3))


	def test_CircleCombinedTangentsWith(self):
		circ1 = Circle2(Point(), 1)
		circ2 = Circle2(Point(4), 2)
		self.tryCircleCombinedTangentsWith(circ1, circ2)
		self.tryCircleCombinedTangentsWith(circ2, circ1)


	def test_Ball3d(self):
		p1 = Point(3, 3, 3)
		ball = ZBall3d(p1, 5)
		line = Line(Point(), Point(1, 2, 3))
		inter = ball.intersectLine(line)
		self.assertEqual(len(inter), 2)
		for p in inter:
			self.assertTrue(ball.containsPoint(p))
			self.assertTrue(line.containsPoint(p))


	def test_quadraticSolution(self):
		a = 1.4081632653061225
		b = 1.134872755770182e-15
		c = -6.25
		self.checkQuadratic(a, b, c)

		a = 0.999067171702237
		b = 0.1251426555239512
		c = -4.1970972228067165
		self.checkQuadratic(a, b, c)

		a = 529.9994123048668
		b = -9.213884297523057
		c = -35584.81950413315
		self.checkQuadratic(a, b, c)

		
	def test_ZCone(self):

		p1 = Point(3, 3, 3)
		p2 = Point(3, 3, 4)
		p3 = Point()

		cones = ZCone.makeCones(p1, 1, p2, 1.1, p3)

		for cone in cones:
			self.assertTrue(cone.containsPoint(p1))
			self.assertAlmostEqual(cone.getPerpendicularDistanceFor(p1), 1)
			self.assertTrue(cone.containsPoint(p2))
			self.assertAlmostEqual(cone.getPerpendicularDistanceFor(p2), 1.1)


	def test_SimpleCone(self):
		p1 = Point(1, 2, 3)
		p2 = Point(-1, 2, 4)
		rr1 = 2
		rr2 = 2.5
		cones = ZCone.makeCones(p1, rr1, p2, rr2, Point())
		for cone in cones:
			aff = cone.makeAffToSimple()
			transformed = cone.transformedBy(aff)
			self.assertTrue(transformed.isSimple())


	def test_cylinderLineIntersection(self):
		p1 = Point(1, 2, 3)
		p2 = Point(-1, 2, 4)
		rr2 = 2.5
		cyls = ZCone.makeCylinders(p1, p2, rr2, Point())
		line = Line(Point(), Point(1, 2, 3))
		for cyl in cyls:
			inter = cyl.intersectLine(line)
			for point in inter:
				#self.assertTrue(cyl.containsPoint(point))
				self.assertTrue(line.containsPoint(point))


	def test_coneLineIntersection(self):
		p1 = Point(1, 2, 3)
		p2 = Point(-1, 2, 4)
		rr1 = 2
		rr2 = 2.5
		cones = ZCone.makeCones(p1, rr1, p2, rr2, Point())
		line = Line(Point(), Point(1, 2, 3))
		for cone in cones:
			inter = cone.intersectLine(line)
			for point in inter:
				self.assertTrue(line.containsPoint(point))
				self.assertTrue(cone.containsPoint(point))


	def test_coneLineIntersection2(self):
		p1 = Point(0, 0, 10)
		p2 = Point(0, 325, 10)
		rr1 = 180
		rr2 = 230
		cones = ZCone.makeCones(p1, rr1, p2, rr2, Point())
		line = Line(Point(23, 36), direction=Point(0, 0, 1))
		for cone in cones:
			aff = cone.makeAffToSimple()
			self.assertTrue(aff.isOrthonormal())
			affInvers = aff.inverted()
			self.assertTrue((aff * affInvers).isSameAs(Affine()))
			inter = cone.intersectLine(line)
			for point in inter:
				self.assertTrue(cone.containsPoint(point))
				self.assertTrue(line.containsPoint(point))


	def test_coneLineIntersection3(self):
		"""
			Tests the validity even of a simple Cone!
		"""
		p1 = Point(0, 0, 10)
		p2 = Point(0, 325, 10)
		rr1 = 180
		rr2 = 230
		cones = ZCone.makeCones(p1, rr1, p2, rr2, Point())
		line = Line(Point(23, 36), direction=Point(0, 0, 1))
		for cone in cones:
			aff = cone.makeAffToSimple()
			self.assertTrue(aff.isOrthonormal())
			affInvers = aff.inverted()
			self.assertTrue((aff * affInvers).isSameAs(Affine()))
			cone2 = cone.transformedBy(aff)
			self.assertTrue(cone2.isSimple())
			line2 = aff * line
			inter = cone2.intersectLineSimple(line2)
			for point in inter:
				self.assertTrue(cone2.containsPoint(point))
				self.assertTrue(line2.containsPoint(point))


	def test_simpleCylinder(self):
		p1 = Point(1, 2, 3)
		p2 = Point(-1, 2, 4)
		rr2 = 2.5
		cyls = ZCylinder.makeCylinders(p1, p2, rr2, Point())
		for cyl in cyls:
			aff = cyl.makeAffToSimple()
			transformed = cyl.transformedBy(aff)
			self.assertTrue(transformed.isSimple())


	def test_morphLineToLine(self):
		line1 = Line(Point(), direction=Point(1))
		point1 = Point(5)
		line2 = Line(Point(), direction=Point(0, 1))
		point2 = Point(0, 5)
		aff = Affine.morphLineToLine(line1, line2, point1, point2)
		self.comparePoints(aff * point1, point2)
		self.comparePoints((aff * line1.m_direction).unit(), line2.m_direction)
		self.assertTrue(aff.m_matrix.isOrthonormal())


	def xtest_ZCone(self):
		height = 3
		cone1 = ZConeOld(1, 2, height)
		distOutside = cone1.m_distanceOutside
		cone2 = ZConeOld(1, 2, distanceOutside=distOutside)
		self.assertAlmostEqual(distOutside, cone2.m_distanceOutside)
		self.assertAlmostEqual(height, cone2.m_height)

		p1 = Point(3, 3, 3)
		p2 = Point(3, 3, 4)
		line = Line(p1, p2)
		planeDirection = Point(1, 1, 1)
		cone1.smoothToLine(line, p1, planeDirection)
		self.assertTrue(cone1.containsPoint(p1))
		self.assertTrue(cone1.containsPoint(p2))
		direction = cone1.m_center1 - p1
		self.assertAlmostEqual(direction.length(), cone1.m_r1)
		line2 = Line(cone1.m_center2, direction=direction)
		intersect = line.intersect(line2)
		self.assertTrue(intersect is not None)
		offset = intersect - cone1.m_center2
		self.assertAlmostEqual(offset.length(), cone1.m_r2)

		coneDirection = cone1.m_center2 - cone1.m_center1
		plane1 = Plane(cone1.m_center1, normal=coneDirection)
		self.assertTrue(plane1.containsPoint(p1))
		plane2 = Plane(cone1.m_center2, normal=coneDirection)
		self.assertTrue(plane2.containsPoint(intersect))

		aff = cone1.getAffine()
		self.assertTrue((aff * Point()).isSameAs(cone1.m_center1))
		ppp = Point(0, 0, height)
		self.assertTrue((aff * ppp).isSameAs(cone1.m_center2))


	def test_Ellipse3(self):
		c = Point(1, 2, 3)
		diam1 = Point(0, 6, 7)	# the longer one
		diam2 = diam1.expandToOrthonormalBase()[1]					#	Point(0, 6)


		#c = Point()
		#diam1 = Point(0, 1)
		#diam2 = Point(1)
		
		ell = Ellipse3(c, diam1= diam1, diam2=diam2)
		v1 = c + diam1
		v2 = c + diam2
		v3 = c - diam1
		v4 = c - diam2
		self.comparePoints(v1, ell.pointForParam(0))
		self.comparePoints(v2, ell.pointForParam(90))
		self.comparePoints(v3, ell.pointForParam(180))
		self.comparePoints(v4, ell.pointForParam(270))

		#num = 20
		#for ii in range(num):
		#	par = (359 / num) * ii
		#	pt = ell.pointForParam(par)
		#	par2 = ell.paramForPoint(pt)
		#	if math.isnan(par2):
		#		ell.paramForPoint(pt)
		#	#print(f'par: {par}, pt: {pt}, par2: {par2}')
		#	#self.assertTrue(par2 is not None)
		#	self.assertAlmostEqual(par, par2, 4)

		##p = 


########################################################
# the instance helping functions

	def checkQuadratic(self, a, b, c):
		sol = ZGeomItem.solveQuadratic(a, b, c)
		for num in sol:
			test = a*num*num + b*num + c
			self.assertAlmostEqual(test, 0)


	def tryCircleCombinedTangentsWith(self, circle1, circle2):
		tangents = circle1.combinedTangentsWith(circle2)
		self.assertTrue(len(tangents) == 2)
		for circle in [circle1, circle2]:
			for tang in tangents:
				inter = circle.intersect(tang)
				self.assertTrue(len(inter) == 1)
				touchPoint = inter[0]
				self.assertTrue(circle.containsPoint(touchPoint))
		for tang in tangents:
			inter = circle1.intersect(tang)
			touchPoint = inter[0]
			# check, that the second line point is the touch point!
			self.assertTrue(tang.m_p2.isSameAs(touchPoint))
		# check, that the first line point is the intersection of the 2 tangents
		self.assertTrue(tangents[0].m_p1.isSameAs(tangents[1].m_p1))


	def makeEulerCombination(self, ax, ay, az):
		mx = Matrix.makeEulerRotation(ax, 'x')		
		self.assertTrue(mx.isOrthonormal())
		my = Matrix.makeEulerRotation(ay, 'y')
		#my.printComment('my')
		self.assertTrue(my.isOrthonormal())
		mz = Matrix.makeEulerRotation(az, 'z')
		self.assertTrue(mz.isOrthonormal())
		mCombined = mz * (my * mx)
		return mCombined


	def tryEulerAngles(self, ax, ay, az):
		mCombined = self.makeEulerCombination(ax, ay, az)
		#(mCombined * mCombined.transposed()).printComment('combined')
		self.assertTrue(mCombined.isOrthonormal())
		angles = mCombined.getEulerAngles()
		#print(angles)
		self.assertAlmostEqual(angles[0], ax)
		self.assertAlmostEqual(angles[1], ay)
		self.assertAlmostEqual(angles[2], az)


	def comparePoints(self, p1: Point, p2: Point):
		if not p1.isSameAs(p2):
			print('different points: ---------')
			p1.printComment('p1')
			p2.printComment('p2')
		self.assertTrue(p1.isSameAs(p2))


#######################################################


if __name__ == '__main__':
    unittest.main(verbosity=1)

print('----------------------------------')


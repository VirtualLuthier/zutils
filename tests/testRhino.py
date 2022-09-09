"""
	A basic test file for the Rhino-3dm file handling.
"""

##############################################

import os
import math

import unittest

from context import zutils, testInFolder, testOutFolder

from zutils.ZGeom import Point, Plane
from zutils.ZMatrix import Affine
from zutils.SvgReader import SvgPathReader
from zutils.ZRhino3dm import ZRhinoFile

from zutils.ZD3Body import ZCone
from zutils.ZPath import ZArcSegment, ZPath, ZLineSegment, ZBezier3Segment, ZBezier2Segment


##############################################


dirInFolder = os.path.join(testInFolder, 'rhino3d')
if not os.path.exists(dirInFolder):
	raise Exception('folder with test input does not exist: ' + dirInFolder)
	
dirOutFolder = os.path.join(testOutFolder, 'rhino3d')
if not os.path.exists(dirOutFolder):
	os.mkdir(dirOutFolder)




###########################################
###########################################


class TestRhino(unittest.TestCase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if not os.path.isdir(dirOutFolder):
			os.mkdir(dirOutFolder)
		self.m_dump = False
		self.m_rh = None
		self.m_affSymm = None


	def makeSymmBeziers(self, curve, nameRoot):
		self.m_rh.addBezierCurve(curve, name=nameRoot + '1')
		curve2 = curve.transformedBy(self.m_affSymm)
		self.m_rh.addBezierCurve(curve2, name=nameRoot + '2')


	def test_fileRead(self):
		"""
			Simple basic test of reading a 3dm file
		"""
		# see https://free3d.com/de/3d-model/detersivo-bottle-472893.html
		fName = os.path.join(dirInFolder, 'CurveTest.3dm')
		rh = ZRhinoFile.readFile(fName)
		if rh is None:
			print('testFileRead: could not read ' + fName)
			return
		if self.m_dump:
			rh.dump()
		#rh.dumpToTextLog(dirName + 'textLog.txt')

		o = rh.findUniqueObjectNamed('Straight-Lower')
		self.assertIsNotNone(o)
		o = rh.findUniqueObjectNamed('Straight-Lower', objectType='ObjectType.Curve')
		self.assertIsNotNone(o)
		o = rh.findUniqueObjectNamed('Straight-Lower', objectType='ObjectType.Curve', layerName='Main::Curves')
		self.assertIsNotNone(o)

		o = rh.findUniqueObjectNamed('Straight-Upper')
		self.assertIsNotNone(o)

		o = rh.findUniqueObjectNamed('Straight-Lower')
		#points = o.getPoints()
		#num = 0
		#for p in points:
		#	p.printComment(str(num))
		#	num += 1

		#knots = o.getKnots()
		#num = 0
		#for k in knots:
		#	print('K' + str(num) + ': ' + str(k))
		#	num += 1


	def test_layers(self):
		"""
			Create several layers
		"""
		fName = os.path.join(dirOutFolder,'WriteLayers.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.addLayer('LayerTest1', color='red')
		rh.addLayer('LayerTest2')
		rh.getLayerWithFullPath('LayerTest2::SubLayer1')
		rh.getLayerWithFullPath('LayerTest2::SubLayer2')
		rh.getLayerWithFullPath('l1::l2::l3::l4')
		rh.getLayerWithFullPath('LayerTest2::SubLayer3')
		rh.write()


	def test_groups(self):
		"""
			Create two groups with 2 lines each. Add another 2 lines without a group.
		"""
		fName = os.path.join(dirOutFolder,'WriteGroups.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		self.makeGroup(rh, 'group1', Point())
		self.makeGroup(rh, 'group2', Point(30))
		self.makeGroup(rh, None, Point(50))

		rh.write()


	@classmethod
	def makeGroup(cls, rh, name, start):
		rh.getGroup(name)
		diff = Point(0, 0, 10)
		stop = start + Point(0, 20)
		rh.addLine(start, stop)
		rh.addLine(start + diff, stop + diff)


	def test_bezier(self):
		"""
			Create a cubic and a quadratic bezier curve in a certain layer
		"""
		fName = os.path.join(dirOutFolder, 'WriteBezier.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.addLayer('BezierCurves')
		rh.addLayer('OtherLayer')
		p1 = Point(20)
		p2 = Point(10, 15)
		p3 = Point(-10, 15)
		p4 = -p1
		rh.addBezierCurve([p1, p2, p3, p4], name='Bezier3')
		diff = Point(0, 30)
		p5, p6, p7 = [x + diff for x in [p1, p2, p4]]
		rh.addBezierCurve([p5, p6, p7], name='Bezier2')
		rh.write()


	def test_line(self):
		"""
			Create a line curve in a certain layer
		"""
		fName = os.path.join(dirOutFolder, 'WriteLine.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		#rh.addLayer('BezierCurves')
		#rh.addLayer('GroupLayer')
		p1 = Point(20)
		p2 = Point(10, 15)
		rh.addLine(p1, p2, name='Line1')
		rh.write()


	def test_fretboard(self):
		"""
			Create a polyline curve and 2 circles simulating a fretboard
		"""
		fName = os.path.join(dirOutFolder, 'WriteFretBoard.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.getLayerWithFullPath('FretBoard::Curves')

		wU = 15
		wL = 20
		l = 200
		p1 = Point(wU)
		p2 = Point(wL, l)
		p3 = Point(-wL, l)
		p4 = Point(-wU)
		rh.addPolyLine([p1, p2, p3, p4, p1], name='fretboard-base')
		rh.addListOfNamedPoints([Point(), Point(0, 0, 12)], 'fretboard-base-extrusion-' )

		r = 100
		c = Point(0, -10, -r + 10)
		rh.addCylinderCurvesOld(c, r, c + Point(0, l + 20) , name='fretboard-rounding')

		rh.getLayerWithFullPath('FretBoard::solids')
		rh.write()


	def test_writeENeckUpperSmart(self):
		"""
			Create the upper part of a smart neck (straight part and the transition part to the end)
			Has configurable number of internal segments (numOfNonLinear)
		"""
		fName = os.path.join(dirOutFolder, 'WriteENeckUpperSmart.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.getLayerWithFullPath('ENeck::solids')
		rh.getLayerWithFullPath('ENeck::Curves')

		# the upper bezier curve of the straight part
		p1 = Point(20)
		p2 = Point(10, 0, -15)
		p3 = Point(-10, 0, -15)
		p4 = -p1
		bezUpper = ZBezier3Segment(p1, p4, p2, p3)
		rh.addBezierCurve(bezUpper, name='Neck-Straight-1')

		# the lower bezier segment of the straight part
		bezLower = bezUpper.copy()
		diff = Point(0, 100)
		bezLower.transformBy(Affine(None, diff))
		rh.addBezierCurve(bezLower, name='Neck-Straight-2')

		linearPart = 0.2
		numOfNonLinear = 12
		curveParamDist = (1 - 2 * linearPart) / numOfNonLinear
		curvePartPoints = [bezLower.getInterPointAtParameter(linearPart)]
		curveParamDist = (1 - 2 * linearPart) / numOfNonLinear
		for ii in range(numOfNonLinear - 1):
			curvePartPoints.append(bezLower.getInterPointAtParameter(linearPart + (ii + 1) * curveParamDist))

		curvePartPoints.append(bezLower.getInterPointAtParameter(1 - linearPart))
		
		rh.addListOfNamedPoints(curvePartPoints, 'Neck-Lower-Path-Separators-')

		# the transition part
		lastY = 110
		q1 = Point(20, lastY)
		q2 = Point(20, lastY, -20)
		q3 = Point(-20, lastY, -20)
		q4 = Point(-20, lastY)
		rh.addPolyLine([q1, q2, q3, q4], name='Neck-Lower-End')

		straightPartPoints = [q2]
		straightDiff = (q3 - q2).scaledBy(1 / (numOfNonLinear))
		for ii in range(numOfNonLinear - 1):
			straightPartPoints.append(q2 + straightDiff.scaledBy(ii + 1))
		straightPartPoints.append(q3)
		
		rh.addListOfNamedPoints(straightPartPoints, 'Neck-Lower-End-Separators-')

		# finally the connection curves of the curves network

		rh.addLine(bezLower.m_start, q1, 'Neck-Lower-End-Connectors-1')
		tangent = Point(0, 1)

		#connect1 =  ZBezier2Segment.makeTwoPointsConnection(t1, tangent, q2, stiffness=0.5)
		#rh.addBezierCurve(connect1, 'Neck-Lower-End-Connectors-2')

		for ii in range(len(straightPartPoints)):
			bezPoint = curvePartPoints[ii]
			linePoint = straightPartPoints[ii]
			connect =  ZBezier2Segment.makeTwoPointsConnection(bezPoint, tangent, linePoint, stiffness=0.5)
			rh.addBezierCurve(connect, 'Neck-Lower-End-Connectors-' + str(2 + ii))

		rh.addLine(bezLower.m_stop, q4, 'Neck-Lower-End-Connectors-' + str(2 + len(straightPartPoints)))


		# now must >blend< the surfaces


		rh.write()


	def test_writeENeckUpperSimple(self):
		"""
			Create the upper part of a simple neck (straight part and the transition part to the end)
		"""
		fName = os.path.join(dirOutFolder, 'WriteENeckUpperSimple.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.getLayerWithFullPath('ENeck::solids')
		rh.getLayerWithFullPath('ENeck::Curves')

		# the upper bezier curve of the straight part
		p1 = Point(20)
		p2 = Point(10, 0, -15)
		p3 = Point(-10, 0, -15)
		p4 = -p1
		bezUpper = ZBezier3Segment(p1, p4, p2, p3)
		rh.addBezierCurve(bezUpper, name='Neck-Straight-1')

		# the lower bezier segment of the straight part
		bezLower = bezUpper.copy()
		diff = Point(0, 100)
		bezLower.transformBy(Affine(None, diff))
		rh.addBezierCurve(bezLower, name='Neck-Straight-2')

		t1 = bezLower.getInterPointAtParameter(0.3)
		t2 = bezLower.getInterPointAtParameter(0.7)
		rh.addListOfNamedPoints([t1, t2], 'Neck-Lower-Path-Separators-')

		# the transition part
		lastY = 110
		q1 = Point(20, lastY)
		q2 = Point(20, lastY, -20)
		q3 = Point(-20, lastY, -20)
		q4 = Point(-20, lastY)
		rh.addPolyLine([q1, q2, q3, q4], name='Neck-Lower-End')

		rh.addListOfNamedPoints([q2, q3], 'Neck-Lower-End-Separators-')

		# finally the connection curves of the curves network

		rh.addLine(bezLower.m_start, q1, 'Neck-Lower-End-Connectors-1')
		tangent = Point(0, 1)
		connect1 =  ZBezier2Segment.makeTwoPointsConnection(t1, tangent, q2, stiffness=0.5)
		rh.addBezierCurve(connect1, 'Neck-Lower-End-Connectors-2')
		connect1 =  ZBezier2Segment.makeTwoPointsConnection(t2, tangent, q3, stiffness=0.5)
		rh.addBezierCurve(connect1, 'Neck-Lower-End-Connectors-3')

		rh.addLine(bezLower.m_stop, q4, 'Neck-Lower-End-Connectors-4')

		rh.write()


	def test_writeENeck(self):
		"""
			Create a dummy straight part ofa E-neck
		"""
		fName = os.path.join(dirOutFolder, 'WriteENeck.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		rh.getLayerWithFullPath('ENeck::solids')
		rh.getLayerWithFullPath('ENeck::Curves')

		l = 80
		r = 6
		p1 = Point(25)
		p2 = Point(25, l)
		p3 = p2 + Point(-r, r)
		p4 = Point(-p3.m_x, p3.m_y)
		p5 = Point(-p2.m_x, p2.m_y)
		p6 = Point(-p1.m_x)

		endPath = ZPath()
		endPath.addSegment(ZLineSegment(p1, p2))
		endPath.addSegment(ZArcSegment(r, r, 0, p2, p3, False, True))
		endPath.addSegment(ZLineSegment(p3, p4))
		endPath.addSegment(ZArcSegment(r, r, 0, p4, p5, False, True))
		endPath.addSegment(ZLineSegment(p5, p6))

		rh.addSvgPath(endPath, 'ENeck-End-1')

		aff = Affine(None, Point(0, 0, 10))
		endPath.transformBy(aff)
		rh.addSvgPath(endPath, 'ENeck-End-2')

		rh.addLine(p6, p1, 'ENeck-End-Bottom-Connector')
		rh.addLine(aff*p6, aff*p1, 'ENeck-End-Top-Connector')

		rh.write()



	def test_writeCNeckHeel(self):
		"""
			Crreate a very schematic classical neck (width is constant)
		"""
		fName = os.path.join(dirOutFolder, 'WriteCNeckHeel.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		self.m_rh = rh
		rh.getLayerWithFullPath('CNeck::solids')
		rh.getLayerWithFullPath('CNeck::Curves')

		affMirror = Affine.makeMirror(Plane.alongAxes('y', 'z'))
		self.m_affSymm = affMirror

		# the lower Z of the straightPart center
		lowerStraightCenterZ = -12
		straightWidthHalf = 20
		# the upper bezier curve of the straight part
		p1 = Point(straightWidthHalf)
		p2 = Point(0, 0, lowerStraightCenterZ)
		#p3 = -p1

		#self.makeSymmBeziers(ZBezier3Segment.makeTwoPointsConnection(p1, Point(0, 0, -1), p2, Point(1)), 'Neck-Straight-Upper-')
		bezUpper1 = ZBezier3Segment.makeTwoPointsConnection(p1, Point(0, 0, -1), p2, Point(1))			#(p1, p4, p2, p3)
		rh.addBezierCurve(bezUpper1, name='Neck-Straight-Upper-1')
		bezUpper2 = bezUpper1.transformedBy(affMirror).reversed()
		rh.addBezierCurve(bezUpper2, name='Neck-Straight-Upper-2')

		neckLen = 100
		affLength = Affine(None, Point(0, neckLen))

		bezLower1 = bezUpper1.transformedBy(affLength)
		rh.addBezierCurve(bezLower1, name='Neck-Straight-Lower-1')
		bezLower2 = bezUpper2.transformedBy(affLength).reversed()
		rh.addBezierCurve(bezLower2, name='Neck-Straight-Lower-2')

		rh.addPoint(affLength * p2, 'Neck-straight-Lower-Center')

		# distance from straight lower part to body
		heelLength = 30
		heelHeight = 60
		heelTipHalfWidth = 8

		neckEndTop = Point(straightWidthHalf, neckLen + heelLength)
		neckEndBottom = Point(heelTipHalfWidth, neckLen + heelLength, -heelHeight)
		bezBody1 = ZBezier3Segment.makeTwoPointsConnection(neckEndTop, Point(0, 0, -1), neckEndBottom, Point(0, 0, 1))
		self.makeSymmBeziers(bezBody1, 'Neck-Heel-Body-')
		#bezHeel1 = ZBezier3Segment.makeTwoPointsConnection(neckEndTop, Point(0, 0, -1), neckEndBottom, Point(0, 0, 1))
		#rh.addBezierCurve(bezHeel1, name='Neck-Heel-Body-1')
		#bezHeel2 = bezHeel1.transformedBy(affMirror)
		#rh.addBezierCurve(bezHeel2, name='Neck-Heel-Body-2')

		rh.addLine(neckEndTop, affMirror * neckEndTop, name='Neck-Heel-Body-Line')
		rh.addLine(neckEndBottom, affMirror * neckEndBottom, name='Neck-Heel-Tip-Body-Line')

		neckHeelTipLength = heelLength * 0.7
		neckHeelTip = Point(0, neckLen + heelLength - neckHeelTipLength, -heelHeight)
		rh.addPoint(neckHeelTip, name='Neck-Heel-Tip-Point')

		self.makeSymmBeziers(ZBezier3Segment.makeTwoPointsConnection(neckHeelTip, Point(1,1), neckEndBottom, Point(0, -1)), 'Neck-Heel-Tip-')
		#bezHeelTip1 = ZBezier3Segment.makeTwoPointsConnection(neckHeelTip, Point(1,1), neckEndBottom, Point(0, -1))
		#rh.addBezierCurve(bezHeelTip1, name='Neck-Heel-Tip-1')
		#bezHeelTip2 = bezHeelTip1.transformedBy(affMirror)
		#rh.addBezierCurve(bezHeelTip2, name='Neck-Heel-Tip-2')

		rh.addLine(neckEndTop, affLength * p1, name='Neck-Heel-Line-Upper-1')
		rh.addLine(affMirror * neckEndTop, affMirror * affLength * p1, name='Neck-Heel-Line-Upper-2')

		straightTangent = Point(0, 1)
		heelCurve = ZBezier2Segment.makeTwoPointsConnection(affLength * p2, straightTangent, neckHeelTip, 0.3)
		rh.addBezierCurve(heelCurve, name='Neck-Heel-Curve-Center')

		#targetZ = lowerCenter.m_z
		func = lambda p: abs(p.m_z - lowerStraightCenterZ)
		thePointArr = bezBody1.findMinimalPoint(func)
		#print(thePointArr)
		interPoint1 = thePointArr[1]
		rh.addPoint(interPoint1, name='Neck-Body-Inter-1')
		rh.addPoint(affMirror * interPoint1, name='Neck-Body-Inter-2')

		interSeg1 = ZBezier3Segment.makeTwoPointsConnection(affLength * p2, Point(1), interPoint1, Point(0, -1), 0.5, 0.5)
		self.makeSymmBeziers(interSeg1, 'Neck-Heel-Inter-')

		# # the lower bezier segment of the straight part
		# bezLower = bezUpper.copy()
		# straightLength = 100
		# diff = Point(0, straightLength)
		# bezLower.transformBy(Affine(None, diff))
		# rh.addBezierCurve(bezLower, name='Neck-Straight-2')

		# lowerCenter = bezLower.getInterPointAtParameter(0.5)
		# rh.addPoint(lowerCenter, name='Neck-Heel-Lower-Center')

		# heelTip = Point(0, straightLength + 3, -25)
		# rh.addPoint(heelTip)

		# straightTangent = Point(0, 1)

		# heelCurve = ZBezier2Segment.makeTwoPointsConnection(lowerCenter, straightTangent, heelTip, 0.3)
		# rh.addBezierCurve(heelCurve, name='Neck-Heel-Curve-Center')

		# bodyDist = 15	# from lower straight curve
		# heelEnd1 = Point(5, straightLength + bodyDist, heelTip.m_z)
		# rh.addPoint(heelEnd1, name='Neck-Heel-Body-1')
		# heelEnd2 = affMirror * heelEnd1
		# rh.addPoint(heelEnd2, name='Neck-Heel-Body-2')
		# rh.addLine(heelEnd1, heelEnd2)

		# heelTipTangent = Point(1, 1)
		# heelBottomCurve1 = ZBezier2Segment.makeTwoPointsConnection(heelTip, heelTipTangent, heelEnd1, 0.5)
		# rh.addBezierCurve(heelBottomCurve1, name='Neck-Heel-Bottom-Curve-1')

		
		# #heelEnd2 = affMirror * heelEnd1
		# #rh.addPoint(heelEnd2)
		# heelBottomCurve2 = heelBottomCurve1.transformedBy(affMirror)
		# rh.addBezierCurve(heelBottomCurve2, name='Neck-Heel-Bottom-Curve-2')

		# planeEnd1 = Point(20, straightLength + bodyDist)
		# rh.addPoint(planeEnd1, name='Neck-Body-1')
		# rh.addLine(planeEnd1, bezLower.m_start, name='Neck-Heel-Straight-1')

		# planeEnd2 = affMirror * planeEnd1
		# rh.addPoint(planeEnd2, name='Neck-Body-2')
		# rh.addLine(planeEnd2, bezLower.m_stop, name='Neck-Heel-Straight-2')

		# tangent = Point(0, 0, 1)
		# bezBody1 = ZBezier3Segment.makeTwoPointsConnection(heelEnd1, tangent, planeEnd1, -tangent, 0.5, 0.5)
		# rh.addBezierCurve(bezBody1, 'Neck-Curve-Body-1')
		# bezBody2 = bezBody1.transformedBy(affMirror)
		# rh.addBezierCurve(bezBody2, 'Neck-Curve-Body-2')

		# targetZ = lowerCenter.m_z
		# func = lambda p: abs(p.m_z - targetZ)
		# thePointArr = bezBody1.findMinimalPoint(func)
		# #print(thePointArr)
		# interPoint1 = thePointArr[1]
		# rh.addPoint(interPoint1, name='Neck-Body-Inter-1')

		# interPoint2 = affMirror * interPoint1
		# rh.addPoint(interPoint2, name='Neck-Body-Inter-2')

		# interSeg1 = ZBezier3Segment.makeTwoPointsConnection(lowerCenter, Point(1), interPoint1, Point(0, -1), 0.5, 0.5)
		# rh.addBezierCurve(interSeg1, name='Neck-Inter-1')

		# interSeg2 = interSeg1.transformedBy(affMirror)
		# rh.addBezierCurve(interSeg2, name='Neck-Inter-2')

		rh.write()


	def test_polycurve(self):

		fName = os.path.join(dirOutFolder, 'WritePolyCurve.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		poly = rh.createPolyCurve()
		#print(poly)
		p1 = Point(20)
		p2 = Point(10, 15)
		rh.addLine(p1, p2, polyCurve=poly)
		p3 = Point(10, 15, 5)
		rh.addLine(p2, p3, polyCurve=poly)
		rh.addCurve(poly)
		rh.write()


	def test_arcCurve(self):
		"""
			make two lines  with rounded intersection as a rhino.PolyCurve
		"""
		fName = os.path.join(dirOutFolder, 'WriteArcCurve.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		poly = rh.createPolyCurve()

		size = 40
		rad = 10
		c1 = Point()
		c2 = Point(size)
		c3 = Point(size, size)
		#c4 = Point(0, size)
		diffH = Point(rad)
		diffV = Point(0, rad)

		dia = math.sqrt(0.5) * rad
		dia1 = Point(dia, -dia)

		p12 = c1 + diffH
		p21 = c2 - diffH

		rh.addLine(p12, p21, polyCurve=poly)

		p22 = c2 + diffV
		m2 = Point(p21.m_x, p22.m_y)
		#rh.addPoint(m2, name='the center')
		i2 = m2 + dia1
		#rh.addPoint(i2, name='interPoint')

		rh.addArcCurve(p21, i2, p22, polyCurve=poly)

		p31 = c3 - diffV
		rh.addLine(p22, p31, polyCurve=poly)

		rh.addCurve(poly, name='the polycurve')
		rh.write()


	def test_writeFullCircle(self):
		fName = os.path.join(dirOutFolder, 'WriteFullCircle.3dm')
		rh = ZRhinoFile.newFile(fName, 'inch')

		rh.addFullCircle(Point(), 15, None, None)

		center = Point(20)
		rh.addFullCircle(center, 15, center, None)

		center = Point(-20)
		normal = Point(10, 0, 10)
		rh.addFullCircle(center, 15, normal, None, name='oblique')

		rh.write()


	def test_writePathLines(self):
		fName = os.path.join(dirOutFolder, 'WritePathLines.3dm')
		rh = ZRhinoFile.newFile(fName, 'inch')
		xmlReader = SvgPathReader()
		# we have only one cmd (M as first). Afterwards we have 2 implicit Ls
		#  After this we have one explicit L and 3 implicit ones
		# the last closing z creates one more line to close the polygon
		text = "M 142,250 167,218 171,77.1 L 112,40 32,47.6 28,189 81,250 z"
		path = xmlReader.classParsePath(text)
		rh.addSvgPath(path, name='SomeLines')
		rh.write()


	def test_writePathWiener(self):
		fName = os.path.join(dirOutFolder, 'WritePathWiener.3dm')
		rh = ZRhinoFile.newFile(fName, 'inch')

		svgName = os.path.join(testInFolder, 'svg/Wiener1.svg')
		#svgName = 'test-in/svg/Wiener1.svg'
		xmlReader = SvgPathReader()
		xmlReader.setDAttributeName('{http://www.inkscape.org/namespaces/inkscape}original-d')
		xmlReader.readFile(svgName)
		path = xmlReader.m_paths[0]

		rh.addLayer('curveLayer', color='orange')
		rh.addSvgPath(path, name='Wiener')
		rh.write()


	def test_writePathWithCircleArc(self):
		"""
			Write a file with a path consisting of
			- a line
			- a quarter circle
			- another line
		"""
		fName = os.path.join(dirOutFolder, 'WritePathWithCircleArc.3dm')
		rh = ZRhinoFile.newFile(fName, 'inch')
		d = 'M 0,30 H 20 A 20 20 0 0 0 40,10 V 0'
		xmlReader = SvgPathReader()
		path = xmlReader.classParsePath(d)
		rh.addSvgPath(path)

		rh.write()


	def test_boolDifference(self):
		"""
			Create some pockets  in a solid
		"""
		fName = os.path.join(dirOutFolder, 'WriteBoolDifference.3dm')
		rh = ZRhinoFile.newFile(fName, 'mm')
		v = Point(40)
		h = Point(0, 60)
		rh.addPolyLine([Point(), v, v + h, h, Point()], name='base')
		rh.addListOfNamedPoints([Point(), Point(0, 0, 10)], 'base-extrusion-' )

		start = Point(20, 20, -5)
		stop = Point(20, 20, 15)
		normal = stop - start
		startDir = normal.anyPerpendicularPoint()
		cone = ZCone.makeCones(Point(20, 20, -5), 8, Point(20, 20, 15), 4, startDir)[0]
		rh.addConeCurves(cone, name='firstHole')			#	(Point(20, 20, -5), 8, Point(20, 20, 15), 4, name='firstHole')
		rh.addCylinderCurvesOld(Point(20, 40, 5), 6, Point(20, 40, 15) , name='secondHole')

		rh.write()


#################################################
#################################################


if __name__ == '__main__':
	unittest.main(verbosity=1)

print('----------------------------------')
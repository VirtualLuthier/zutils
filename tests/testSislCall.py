"""
	Test the functions from zutils.SISLCall.py
"""

import os
import random

from context import zutils, testInFolder, testOutFolder

from zutils.ZPath import ZBezier3Segment
from zutils.SISLCall import SislCurveHolder, SislSurfaceHolder, SislLoftedSurfaceHolder
from zutils.ZGeom import Point, Plane
from zutils.ZMatrix import Affine, Matrix
from zutils.OSCNode import OSCRoot, OSCForm3d, OSCCylinder, OSCSphere
from zutils.Form3d import Form3d


##################


def createSimpleSurface(quality):
	OSCRoot.s_quality = quality
	p1 = Point()
	p2 = Point(1)
	p3 = Point(2)
	offset = Point(0, 3)
	[p4, p5, p6] = [x + offset for x in [p1, p2, p3]]
	bezDiff = Point(0, 1, 1.5)
	bezDiffMinus = Point(0, -1, -1.5)
	curve1 = SislCurveHolder.createCurveFromStraightLine(p1, p4)
	curve2 = SislCurveHolder.createCurveFromControlPoints([p2, p2 + bezDiff, p5 + bezDiffMinus, p5])
	curve3 = SislCurveHolder.createCurveFromStraightLine(p3, p6)
	surface = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([curve1, curve2, curve3])
	return surface


def createQuasiExtrusionSurface(quality):
	OSCRoot.s_quality = quality
	start = Point()
	stop = Point(3)
	h1 = Point(1, 0, 0.5)
	h2 = Point(2, 0, 0.5)
	bez1 = ZBezier3Segment(start, stop, h1, h2)
	bez2 = bez1.copy()
	bez2.transformBy(Affine(Matrix(0.7), Point(0, 4)))
	curve1 = SislCurveHolder.createCurveFromBezier3Segement(bez1)
	curve2 = SislCurveHolder.createCurveFromBezier3Segement(bez2)
	surface = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([curve1, curve2])
	surface.m_bePseudoExtrusion = True
	return surface


def showSurface(surface):
	"""
		Return an OSCRoot showing the surface
	"""
	root = OSCRoot('rootNode')
	form = Form3d()
	form.addSurface(surface)

	oscForm = OSCForm3d('form3d', form, massCenter=Point(0, 0, 0.5))
	root.add(oscForm)

	return [root, form]


def showPoint(root, point):
	"""
		Show a ball at the point position on the OSCRoot
	"""
	sphere = OSCSphere('ball', point, 0.1)
	root.add(sphere)


###############################


def testCurveFromStraightLine():
	"""
		Tests createCurveFromStraightLine()
		Also tests getIntersectionPointsWithPlane() and subDivideAtParameter()
	"""
	p1 = Point()
	p2 = Point(10, 10)
	curve = SislCurveHolder.createCurveFromStraightLine(p1, p2)
	#curve.dump()

	points = curve.getRegularCurvePoints(10)
	#for point in points:
	#	point.printComment('p')

	plane = Plane(Point(5, 5), normal=p2)
	(intersection, params) = curve.getIntersectionPointsWithPlane(plane)
	interPoint = intersection[0]
	interPoint.printComment('intersection')

	partCurves = curve.subDivideAtParameter(params[0])
	partCurves[0].dump('testCurveFromStraightLine')
	partCurves[1].dump('testCurveFromStraightLine')


def testCurveConstant():
	val = Point(3.5, 2, 3)
	curve = SislCurveHolder.createCurveConstant(val)
	points = curve.getRegularCurvePoints(10)
	for point in points:
		if not val.isSameAs(point):
			raise Exception('testCurveConstant() failed')
	#curve.dumpCurvePoints(10)


def testCurveFromControlPoints():
	p1 = Point()
	p2 = Point(1, 0.5)
	p3 = Point(2, 0.5)
	p4 = Point(3)
	curve = SislCurveHolder.createCurveFromControlPoints([p1, p2, p3, p4])
	#curve.dump()

	points = curve.getRegularCurvePoints(10)
	#for point in points:
	#	point.printComment('p')
	#dumpCurvePoints(curve, 20)


def testSurfaceAndNormal():
	quality = 25
	surface = createSimpleSurface(quality)

	#surface.dump()

	root = showSurface(surface)[0]

	#root = OSCRoot('rootNode')
	#form = Form3d()
	#form.addSurface(surface)

	#oscForm = OSCForm3d('form3d', form, massCenter=Point(0, 0, 0.5))
	#root.add(oscForm)

	# now add a random surface normal
	u = random.randrange(quality)
	v = random.randrange(quality)
	normals = surface.getNormalVectors(quality+1)[0]
	points = surface.getSurfacePoints(quality)[0]
	sPoint = points[u][v]
	normal = -normals[u][v]
	pointer = OSCCylinder('normal', sPoint, normal, 0.5, 0.01)
	root.add(pointer)

	root.writeScadTo(s_outputRootFolder + '/testSurfaceAndNormal.scad')


def testSurfaceClosestPoint():
	quality = 16
	surface = createSimpleSurface(quality)
	point = Point(1, 1.5, 1)
	closest = surface.findClosestPointSimple(point)

	root = showSurface(surface)[0]
	showPoint(root, point)
	showPoint(root, closest)
	root.writeScadTo(s_outputRootFolder + '/testSurfaceClosestPoint.scad')

	#surface.dumpNurbs()


def testCurveTransform():
	p1 = Point()
	p2 = Point(3)
	curve1 = SislCurveHolder.createCurveFromStraightLine(p1, p2)
	#curve1.dump()
	curve2 = curve1.transformedBy(Affine())
	curve2.dump('testCurveTransform')


def testJoin2Curves():
	p1 = Point()
	p2 = Point(3)
	p3 = Point(3, 2)
	p4 = Point(0, 2)
	curve1 = SislCurveHolder.createCurveFromStraightLine(p1, p2)
	curve2 = SislCurveHolder.createCurveFromStraightLine(p2, p3)
	curve3 = SislCurveHolder.createCurveFromStraightLine(p3, p4)

	curveRet = SislCurveHolder.joinAllCurves([curve1, curve2, curve3])
	curveRet.dump('testJoin2Curves')
	#curveRet.dumpNurbs()


def testSurfaceTransform():
	quality = 25
	surface = createSimpleSurface(quality)
	surface2 = surface.transformedBy(Affine(None, Point(0, 0, 1)))
	#surface2.dump()

	root = showSurface(surface2)[0]
	root.writeScadTo(s_outputRootFolder + '/testSurfaceTransform.scad')


def testQuasiExtrusion():
	surface1 = createQuasiExtrusionSurface(5)
	root, _ = showSurface(surface1)
	root.writeScadTo(s_outputRootFolder + '/testQuasiExtrusion.scad')


def testSmoothTransition():
	surface1 = createQuasiExtrusionSurface(25)
	surface1.dump('testSmoothTransition')
	deriv1Curve = surface1.getDerivationAtEdge(True, True)

	curve1 = surface1.m_curves[0]
	aff1 = Affine(Matrix(2), Point(0, -1))
	curve2 = curve1.transformedBy(aff1)
	#surface2 = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([curve1, curve2])#

	aff2 = Affine(Matrix(), Point(0, -2))
	curve3 = curve1.transformedBy(aff2)

	curve4 = curve3.transformedBy(aff2)
	surface2 = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([curve3, curve4])
	surface2.m_bePseudoExtrusion = True
	deriv2Curve = surface2.getDerivationAtEdge(True, False)

	ct = SislLoftedSurfaceHolder.LoftedSurfaceCurveType
	curveTypes = [ct.TANGENTTONEXT, ct.ORDINARY, ct.ORDINARY, ct.ORDINARY, ct.TANGENTTOPRIOR]

	surfaceLast = SislLoftedSurfaceHolder.createLoftedSurfaceFromBSplines([deriv1Curve, curve1, curve2, curve3, deriv2Curve], curveTypes)

	root, oscForm = showSurface(surface1)
	oscForm.addSurface(surface2)
	oscForm.addSurface(surfaceLast)
	root.writeScadTo(s_outputRootFolder + '/testSmoothTransition.scad')


def testCreateSurfsFromCurves():
	top = Point(0, 0, -0.2)
	p1 = Point(1, 0, 0)
	p2 = Point(-0.3, 1, 0)
	p3 = Point(-0.3, -1, 0)
	points = [p1, p2, p3, p1]
	curves = []
	derivs = []
	for  ii in range(3):
		curves.append(SislCurveHolder.createCurveFromStraightLine(points[ii], points[ii+1]))	# s1602()
		tp1 = top + points[ii]
		tp2 = top + points[ii+1]
		derivs.append(SislCurveHolder.createCurveFromStraightLine(tp1, tp2))	# s1602()
	surfs = SislSurfaceHolder.createSurfsFromCurves(curves, derivs)	# s1391

	# display the surfaces in oscad:
	ii = 1
	for surf in surfs:
		surf.dump('testCreateSurfsFromCurves ' + str(ii))
		ii += 1
	root, oscForm = showSurface(surfs[0])
	oscForm.addSurface(surfs[1])
	oscForm.addSurface(surfs[2])
	root.writeScadTo(s_outputRootFolder + '/testCreateSurfsFromCurves.scad')


##################

# now create the output folders
#folder = os.path.dirname(os.path.abspath(__file__))
#folder = os.path.dirname(folder) + '/test-out'
#if not os.path.isdir(folder):
#	os.mkdir(folder)
folder = testOutFolder + '/testSislCall'
if not os.path.isdir(folder):
	os.mkdir(folder)
s_outputRootFolder = folder


testQuasiExtrusion()
testCurveFromStraightLine()
testCurveFromControlPoints()
testSurfaceAndNormal()
testSurfaceClosestPoint()
testCurveTransform()
testSurfaceTransform()
testSmoothTransition()
testJoin2Curves()
testCurveConstant()
testCreateSurfsFromCurves()

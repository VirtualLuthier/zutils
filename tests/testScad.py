"""
	Contains several tests for OpenScad generation
"""	

import os
import random

from context import zutils, testInFolder, testOutFolder

from zutils.ZGeom import Point, Polygon
from zutils.Form3d import Form3d, SurfacePolygon, SurfaceBezierCubic
from zutils.OSCNode import OSCRoot, OSCCombination, OSCHexahedron, OSCLongSlot3D, OSCCube, OSCCylinder, OSCPocketHull, OSCForm3d


########################################################
########################################################


s_outputRootFolder = None


def test_2AdjacentPolyhedra():
	"""
		Create 2 cubic polyhedra which touch each other with 1 surface
	"""
	p1 = Point()
	p2 = Point(1)
	p3 = Point(2)
	diffY = Point(0, 1)
	p4, p5, p6 = [x + diffY for x in [p1, p2, p3]]
	diffZ = Point(0, 0, 1)
	q1, q2, q3, q4, q5, q6 = [x + diffZ for x in [p1, p2, p3, p4, p5, p6]]
	c1 = OSCHexahedron('hexa1', p1, p2, p5, p4, q1, q2, q5, q4)
	c2 = OSCHexahedron('hexa2', p2, p3, p6, p5, q2, q3, q6, q5)

	root = OSCRoot('rootNode')
	root.add(c1)
	root.add(c2)
	root.writeScadTo(s_outputRootFolder + '/test2AdjacentPolyhedra.scad')


def pocketTest():
	root = OSCRoot('rootNode')

	wid = 200
	length = 100
	hei = 25

	diff = OSCCombination('main diff', 'difference')
	root.add(diff)
	box = OSCCube('mainCube', wid, length, hei, 0, 0, 0, Point())
	diff.add(box)

	
	diffX = Point(50, 0, 0,)
	diffY = Point(0, length - 2, 0)
	depthZ = Point(0, 0, -10)

	p1 = Point(1, 1, hei)
	p2 = p1 + diffX
	p3 = p2 + diffY
	p4 = p1 + diffY

	pocket = OSCPocketHull('pocket1', Polygon([p1, p2, p3, p4]), depthZ, 10)
	diff.add(pocket)

	p1 = Point(70, -10, hei)
	diffY = Point(0, length +20, 0)
	p2 = p1 + diffY

	slot = OSCLongSlot3D('long slot1', p1, p2, depthZ, depthZ.length(), 6, 10)
	diff.add(slot)

	p1 = Point(100, -10, hei)
	p2 = Point(120, 80, hei)
	p3 = Point(140, -10, hei)
	pocket = OSCPocketHull('pocket2', Polygon([p1, p2, p3]), depthZ, 6, False)
	diff.add(pocket)
	slot = OSCLongSlot3D('long slot1', p1, p2, depthZ, depthZ.length(), 6, 10)
	diff.add(slot)
	slot = OSCLongSlot3D('long slot1', p2, p3, depthZ, depthZ.length(), 6, 10)
	diff.add(slot)

	root.writeScadTo(s_outputRootFolder + '/pocket.scad')


def test_simpleOctohedron():
	"""
		Make a simple Octoeder
	"""
	form = Form3d()
	p1 = Point(1)
	p2 = Point(0, 1)
	p3 = Point (0, -1)
	p4 = Point(0.5, 0, 1)
	p5 = Point(0.5, 0, -1)
	ar1 = SurfacePolygon('a1', Polygon([p1, p2, p4]))
	form.addSurface(ar1)
	ar2 = SurfacePolygon('a2', Polygon([p1, p3, p4]))
	form.addSurface(ar2)
	ar3 = SurfacePolygon('a3', Polygon([p2, p3, p4]))
	form.addSurface(ar3)
	ar4 = SurfacePolygon('a4', Polygon([p1, p2, p5]))
	form.addSurface(ar4)
	ar5 = SurfacePolygon('a5', Polygon([p1, p3, p5]))
	form.addSurface(ar5)
	ar6 = SurfacePolygon('a6', Polygon([p2, p3, p5]))
	form.addSurface(ar6)
	if not form.isCornerClosed():
		raise Exception('form is not corner closed')

	root = OSCRoot('rootNode')
	oscForm = OSCForm3d('form3d', form)
	root.add(oscForm)
	root.writeScadTo(s_outputRootFolder + '/testForm3d_1.scad')


#def test_neckStraightPart():
#	"""
#		Make the straight part of a guitar neck - probably obsolete
#	"""
#	OSCRoot.s_quality = 5
#	form = Form3d()
#	d = 'M 2,0 C 2,0.8 1,1 0,1 -1,1 -2,0.8 -2,0 z'
#	path1 = SvgPathReader.classParsePath(d)
#
#	matrix = Matrix([Point(1.5), Point(0, 2), Point(0, 0, 1)])
#	affine = Affine(matrix, Point(0, 0, 5))
#	path2 = path1.copy()
#	path2.transformBy(affine)
#
#	surface = SurfacePathExtrusion('pathExtrusion', path1, path2)
#	form.addSurface(surface)
#
#	surface2 = SurfacePath('path1', path1)
#	form.addSurface(surface2)
#
#	surface3 = SurfacePath('path2', path2)
#	form.addSurface(surface3)
#
#	root = OSCRoot('rootNode')
#	oscForm = OSCForm3d('form3d', form)
#	root.add(oscForm)
#	root.writeScadTo(s_outputRootFolder + '/testForm3d_2.scad')


def test_baseCubeItself():
	OSCRoot.s_quality = 5
	oscForm = makeBaseCube()

	root = OSCRoot('rootNode')
	oscForm = OSCForm3d('form3d', oscForm, massCenter=Point(0, 0, 0.5))
	root.add(oscForm)
	root.writeScadTo(s_outputRootFolder + '/testForm3d_3.scad')


def test_baseCubeSimple():
	OSCRoot.s_quality = 5
	oscForm = makeBaseCube()
	[p5, p6, p7, p8] = makeCubeUpperPoints()
	tip = Point(0, 0, 1.5)
	ar1 = SurfacePolygon('b1', Polygon([p5, p6, tip]))
	oscForm.addSurface(ar1)
	ar2 = SurfacePolygon('b2', Polygon([p6, p7, tip]))
	oscForm.addSurface(ar2)
	ar3 = SurfacePolygon('b3', Polygon([p7, p8, tip]))
	oscForm.addSurface(ar3)
	ar4 = SurfacePolygon('b4', Polygon([p8, p5, tip]))
	oscForm.addSurface(ar4)


	root = OSCRoot('rootNode')
	oscForm = OSCForm3d('form3d', oscForm, massCenter=Point(0, 0, 0.5))
	root.add(oscForm)
	root.writeScadTo(s_outputRootFolder + '/testForm3d_4.scad')


def test_SurfaceBezierCubicBernsteinCoefficients():
	SurfaceBezierCubic.getBernsteinSurfaceCoefficients(5)
	SurfaceBezierCubic.getBernsteinSurfaceCoefficients(50)
	SurfaceBezierCubic.checkBernsteinCoefficients()


def test_SurfaceBezierCubic1():
	makeSurfaceBezierCubic(20, True, '_Bezier1.scad')


def test_SurfaceBezierCubic2():
	makeSurfaceBezierCubic(20, False, '_Bezier2.scad')


############################


def makeSurfaceBezierCubic(quality, showNormal, fName):
	OSCRoot.s_quality = quality
	theForm = makeBaseCube()
	[p5, p6, p7, p8] = makeCubeUpperPoints()

	overlap = Point(0, 0, 0.8)

	cp1 = p5
	cp2 = interpolate(p5, p6, 0.33)
	cp3 = interpolate(p5, p6, 0.66)
	cp4 = p6

	cp5 = interpolate(p5, p8, 0.33)
	cp8 = interpolate(p6, p7, 0.33)
	cp6 = interpolate(cp5, cp8, 0.33) + overlap
	cp7 = interpolate(cp5, cp8, 0.66) + overlap

	cp9 = interpolate(p5, p8, 0.66)
	cp12 = interpolate(p6, p7, 0.66)
	cp10 = interpolate(cp9, cp12, 0.33) + overlap
	cp11 = interpolate(cp9, cp12, 0.66) + overlap

	cp13 = p8
	cp16 = p7
	cp14 = interpolate(cp13, cp16, 0.33)
	cp15 = interpolate(cp13, cp16, 0.66)

	#controlPoints = [[cp1, cp2, cp3, cp4], [cp5, cp6, cp7, cp8], [cp9, cp10, cp11, cp12], [cp13, cp14, cp15, cp16]]
	controlPoints = [cp1, cp2, cp3, cp4, cp5, cp6, cp7, cp8, cp9, cp10, cp11, cp12, cp13, cp14, cp15, cp16]
	surface = SurfaceBezierCubic('testbezier', controlPoints)

	theForm.addSurface(surface)

	root = OSCRoot('rootNode')
	oscForm = OSCForm3d('form3d', theForm, massCenter=Point(0, 0, 0.5))
	root.add(oscForm)

	if showNormal:
		u = random.random()
		v = random.random()

		normal = -surface.getSurfaceNormal(u, v)
		sPoint = surface.getPointForUV(u, v)
		pointer = OSCCylinder('normal', sPoint, normal, 0.5, 0.01)
		root.add(pointer)

	root.writeScadTo(s_outputRootFolder + '/testForm3d' + fName)
	#root.printStructure()


def makeCubePoints():
	p1 = Point(1)
	p2 = Point(0, 1)
	p3 = Point (-1)
	p4 = Point(0, -1)

	p5, p6, p7, p8 = [x+Point(0, 0, 1) for x in [p1, p2, p3, p4]]
	return [p1, p2, p3, p4, p5, p6, p7, p8]


def makeCubeUpperPoints():
	[_, __, ___, ____, p5, p6, p7, p8] = makeCubePoints()
	return [p5, p6, p7, p8]


def makeBaseCube(closed=False):
	"""
		Make an empty cube with missing top surface
	"""
	[p1, p2, p3, p4, p5, p6, p7, p8] = makeCubePoints()
	form = Form3d()

	ar1 = SurfacePolygon('a1', Polygon([p1, p2, p3, p4]))
	form.addSurface(ar1)
	ar2 = SurfacePolygon('a2', Polygon([p1, p2, p6, p5]))
	form.addSurface(ar2)
	ar3 = SurfacePolygon('a3', Polygon([p2, p3, p7, p6]))
	form.addSurface(ar3)
	ar4 = SurfacePolygon('a4', Polygon([p3, p4, p8, p7]))
	form.addSurface(ar4)
	ar5 = SurfacePolygon('a5', Polygon([p4, p1, p5, p8]))
	form.addSurface(ar5)
	if closed:
		ar6 = SurfacePolygon('a6', Polygon([p5, p6, p7, p8]))
		form.addSurface(ar6)
		if not form.isCornerClosed():
			raise Exception('form is not corner closed')
	return form


def interpolate(p1, p2, t):
	return p1.scaledBy(1-t) + p2.scaledBy(t)


#############################################

# now create the output folder
folder = testOutFolder + '/testScad'
if not os.path.isdir(folder):
	os.mkdir(folder)
s_outputRootFolder = folder

#pocketTest()
test_simpleOctohedron()
test_2AdjacentPolyhedra()
#test_neckStraightPart()
test_baseCubeSimple()
test_baseCubeItself()
test_SurfaceBezierCubic1()
test_SurfaceBezierCubic2()
test_SurfaceBezierCubicBernsteinCoefficients()
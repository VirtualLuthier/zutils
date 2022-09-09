"""
	test the various svg reader and path functions
"""


import unittest
import os

#import sys
#sys.path.append('.')

from context import zutils, testInFolder, testOutFolder

from zutils.ZGeom import ZGeomItem, Point, Line
from zutils.SvgReader import SvgPathReader
from zutils.ZPath import ZArcSegment
from zutils.ZMatrix import Matrix, Affine

from zutils.OSCNode import OSCRoot, OSCExtrudeRounded


#unittest.TestLoader.sortTestMethodsUsing = None

####################################################
####################################################


class TestSvg(unittest.TestCase):

	s_outputRootFolder = None
	s_testInFolder = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# now create the output folders
		#folder = os.path.dirname(os.path.abspath(__file__))
		#folder = os.path.dirname(folder) + '/test-out'
		#if not os.path.isdir(folder):
		#	os.mkdir(folder)
		folder = os.path.join(testOutFolder, '/testSvg')
		if not os.path.isdir(folder):
			os.mkdir(folder)
		self.s_outputRootFolder = folder
		self.s_testInFolder = os.path.join(testInFolder, 'svg')


	def xtest_00_lines(self):
		# currently not used
		dAttribute = 'M -50,50 50,50 0,-50 z'
		#xmlReader = SvgPathReader()
		#xmlReader.parse(dAttribute)
		path = SvgPathReader.classParsePath(dAttribute)	#					xmlReader.m_paths[0]
		root = OSCRoot('testLines')
		rounded = OSCExtrudeRounded('the path', path, 20, 5)
		root.add(rounded)
		root.writeScadTo(self.s_outputRootFolder + '/Polygon.scad')


	def testCncFriendly(self):
		dAttribute = 'M -50 50 A 100 60 0 0 0 50 -50'
		path = SvgPathReader.classParsePath(dAttribute)
		self.assertTrue(path.areSegsConnected())
		cncPath = path.cncFriendly(0.1)
		self.assertTrue(cncPath.areSegsConnected())
		#print('length of cncPath: ' + str(len(cncPath.m_segments)))



	def test_05_arcs1(self):

		self.checkOneArcFromString('M 0 100 A 80 80 0 1 0 100 0', None, False)

		# a circle with an ok radius:
		self.checkOneArcFromString('M 0 100 A 80 80 0 0 0 100 0', None, False)
		# a circle with a too small radius:
		self.checkOneArcFromString('M 0 100 A 60 60 0 0 0 100 0', None, False)
		# an simple ellipse with rx > ry, the points centered around the origin
		self.checkOneArcFromString('M -50 50 A 100 60 0 0 0 50 -50', None, False)
		# an simple ellipse with rx > ry, the points NOT centered around the origin
		self.checkOneArcFromString('M 100 0 A 100 60 0 0 0 0 100', None, False)
		# an ellipse with rx > ry
		self.checkOneArcFromString('M 0 100 A 60 100 0 0 0 100 0', None, False)
		# check all the flag variants rotation = 0, ry > rx:
		args = 'M 0 100 A 60 100 0 flags 100 0'
		for flags in ['0 0', '0 1', '1 0', '1 1']:
			args = args.replace('flags', flags)
			self.checkOneArcFromString(args, None, False)

		# now for rotated ellipses:
		# in normal position
		self.checkOneArcFromString('M 100 0 A 100 60 30 0 0 0 100', None, False)
		# x, y changed
		self.checkOneArcFromString('M 100 0 A 60 100 30 0 0 0 100', None, False)
		# check all the flag variants rotation = 30, ry > rx:
		args = 'M 0 100 A 60 100 30 flags 100 0'
		for flags in ['0 0', '0 1', '1 0', '1 1']:
			args = args.replace('flags', flags)
			self.checkOneArcFromString(args, None, False)


	def test_01_arcPathVisually(self):
		args = 'M 0,100 A 60 100 30 flags 100,0 L 170,-90  -50,-90 -50,160 z'
		allFlags = ['0 0', '0 1', '1 0', '1 1']
		#allFlags = ['0 0']
		for flags in allFlags:
			myArgs = args.replace('flags', flags)
			flags2 = flags.replace(' ', '-')
			fName = 'Arc-' + flags2 + '.scad'
			self.checkOnePathFromString(myArgs, fName, False)


	def test_arcCircleDetection(self):
		dAttribute = ('M 285.0,350.0 A 100.0 100.0 0.0 0 1 185.0,450.0 A 100.0 100.0 0.0 0 1 85.0,350.0 ' +
			'A 100.0 100.0 0.0 0 1 185.0,250.0 A 100.0 100.0 0.0 0 1 285.0,350.0 ' +
			'M 125.0,350.0 A 60.0 60.0 0.0 0 0 185.0,410.0 A 60.0 60.0 0.0 0 0 245.0,350.0 ' +
			'A 60.0 60.0 0.0 0 0 185.0,290.0 A 60.0 60.0 0.0 0 0 125.0,350.0')
		xmlReader = SvgPathReader()
		xmlReader.parsePath(dAttribute)
		ellipses = xmlReader.m_circles
		self.assertEqual(len(ellipses), 2)


	def xtest_bezier2(self):
		# currently not used (problem with OSCExtrudeRounded)
		fName = os.path.join(self.s_testInFolder, 'test.svg')
		xmlReader = SvgPathReader()
		xmlReader.readFile(fName)
		root = OSCRoot('testBezier2')
		for path in xmlReader.m_paths:
			rounded = OSCExtrudeRounded('one char', path, 10, 0)
			root.add(rounded)
		root.writeScadTo(self.s_outputRootFolder + '/testText.scad')


	def test_Wiener(self):
		fName = os.path.join(self.s_testInFolder, 'Wiener1.svg')
		xmlReader = SvgPathReader()
		xmlReader.setDAttributeName('{http://www.inkscape.org/namespaces/inkscape}original-d')
		xmlReader.readFile(fName)

		self.assertTrue(xmlReader.foundSomething())
		path = xmlReader.m_paths[0]
		self.assertTrue(path.areSegsConnected())
		self.assertFalse(path.isClosed())
		start = path.getStart()
		stop = path.getStop()
		path.supplementByMirror(Line(start, stop))
		self.assertTrue(path.isClosed())


	def test_findMinimalPoint(self):
		fName = os.path.join(self.s_testInFolder, 'Wiener1.svg')
		xmlReader = SvgPathReader()
		xmlReader.setDAttributeName('{http://www.inkscape.org/namespaces/inkscape}original-d')
		xmlReader.readFile(fName)

		self.assertTrue(xmlReader.foundSomething())
		path = xmlReader.m_paths[0]
		myLambda = lambda point: abs(point.m_y - 140)
		test = path.findMinimalPoint(myLambda)
		#print(test)
		self.assertAlmostEqual(test[-1], 0)
		self.assertTrue(path.containsPoint(test[1]))


############################################

	def test_Blob(self):

		fName = os.path.join(self.s_testInFolder, 'Blob.svg')
		xmlReader = SvgPathReader()
		xmlReader.readFile(fName)

		self.assertTrue(xmlReader.foundSomething())

		path = xmlReader.getPath()

		self.assertTrue(path.isClosed())

		path.makeClockwise(False)
		self.assertFalse(path.isClockwise())
		path.reverse()
		self.assertTrue(path.isClockwise())


	def test_implicitLines(self):
		# in several cases we do not need a L(l) cmd, e.g. after a M(m) or L(l)
		xmlReader = SvgPathReader()
		# we have only one cmd (M as first). Afterwards we have 2 implicit Ls
		#  After this we have one explicit L and 3 implicit ones
		# the last closing z creates one more line to close the polygon
		text = "M 142,250 167,218 171,77.1 L 112,40 32,47.6 28,189 81,250 z"
		path = xmlReader.classParsePath(text)
		# because of the last z there is another (closing) line segment
		self.assertEqual(len(path.m_segments), 7)
		self.assertTrue(path.areSegsConnected())
		self.assertTrue(path.isClosed())


##################################################
# helping functions

	def checkRotationCorrectness(self, vect1, vect2, angle):
		# check, if vect1 is rotated to vect2
		aff = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), angle)
		vect2_ = vect2.unit()
		vect3 = (aff * vect1).unit()
		test = vect2_.isSameAs(vect3)
		if test:
			return
		realAngle = Affine.fullAngleBetween2d(vect1, vect2)
		print(f'found angle: {str(realAngle)}, but expected: {str(angle)}')
		self.fail('rotation check failed')
		#self.assertTrue(vect2.isSameAs(vect3))


	def checkIsSamePoint(self, p1, p2, fail=True):
		test = p1.isSameAs(p2)
		if test:
			return True
		if not fail:
			return False
		p1.printComment('point1')
		p2.printComment('point2')
		self.fail('points are not equal')


	def checkOnePathFromString(self, dAttribute, fName, printFlag):
		self.checkOneArcFromString(dAttribute, None, False)
		#xmlReader = SvgPathReader()
		#xmlReader.parse(dAttribute)
		#path = xmlReader.m_paths[0]

		path = SvgPathReader.classParsePath(dAttribute)
		
		if printFlag:
			path.printComment(fName)

		self.assertTrue(path.areSegsConnected())
		self.assertTrue(path.isClosed())

		if fName:
			root = OSCRoot('testArc')
			rounded = OSCExtrudeRounded('the path', path, 20, 0)
			root.add(rounded)
			root.writeScadTo(self.s_outputRootFolder + '/'+fName)


	#def checkArcWithTransforms(self, dAttribute, fName, printFlag):


	def checkOneArcFromString(self, dAttribute, fName, printFlag):
		#xmlReader = SvgPathReader()
		#xmlReader.parse(dAttribute)
		#path = xmlReader.m_paths[0]
		path = SvgPathReader.classParsePath(dAttribute)
		segs = path.m_segments
		arcs = list(filter(lambda x: isinstance(x, ZArcSegment), segs))
		arc = arcs[0]

		if printFlag:
			path.printComment(fName)

		self.checkOneArc(arc, path, fName)

		affs = self.getTestAffines()
		for aff in affs:
			arc2 = arc.copy()
			arc2.transformBy(aff)
			self.checkOneArc(arc2, path, fName)


	def checkOneArc(self, arc, path, fName):
		start = arc.m_start
		stop = arc.m_stop

		# check, if the start and stop really lie on the arc
		start.printComment('checking start')
		if not arc.containsPoint(start):
			print('debug me')
			arc.containsPoint(start)
		self.assertTrue(arc.containsPoint(start))
		#print('start was ok')
		self.assertTrue(arc.containsPoint(stop))

		# now test the correctness of startAngle, stopAngle and deltaAngle
		p = arc.getPointForParameter(arc.m_startAngle)
		self.checkIsSamePoint(p, arc.m_start, True)

		p = arc.getPointForParameter(arc.m_stopAngle)
		self.checkIsSamePoint(p, arc.m_stop, True)

		testAngle = ZGeomItem.normalizeAngle(arc.m_startAngle + arc.m_deltaAngle)
		self.assertAlmostEqual(testAngle, arc.m_stopAngle)
		
		delta = arc.m_deltaAngle
		if abs(abs(delta) - 180) > 0.0001:
		# 180 or -180 are ok
			if arc.m_largeArcFlag:
				self.assertTrue(abs(arc.m_deltaAngle) >= 180)
			else:
				self.assertTrue(abs(delta) <= 180)

		# this is preliminary:
		if not arc.m_sweepFlag:
			self.assertTrue(arc.m_deltaAngle < 0)
		else:
			self.assertTrue(arc.m_deltaAngle > 0)

		if fName:
			root = OSCRoot('testArc')
			rounded = OSCExtrudeRounded('the path', path, 10, 0)
			root.add(rounded)
			root.writeScadTo(self.s_outputRootFolder + '/'+fName)


	def getTestAffines(self):
		# return a list of affines that can transform out arcs
		# we check each transformed arc, if it is valid
		ret = []

		# a simple rotation around the origin
		aff = Affine.makeRotationAffine(Line(Point(), Point(0, 0, 1)), 30)
		ret.append(aff)

		# a more complicated rotation
		aff = Affine.makeRotationAffine(Line(Point(5, 3), direction=Point(0, 0, 1)), 30)
		ret.append(aff)

		# make a very big x:
		points = [Point(10), Point(0, 1)]
		ret .append(Affine(Matrix(points)))

		# make a very big y:
		points = [Point(1), Point(0, 10)]
		ret .append(Affine(Matrix(points)))

		# make a mirror
		#points = [Point(-1), Point(0, 1)]
		#ret .append(Affine(Matrix(points)))

		for aff in ret:
			self.assertTrue(aff.isInvertible)

		return ret




################################################


if __name__ == '__main__':
    unittest.main(verbosity=1)

print('----------------------------------')
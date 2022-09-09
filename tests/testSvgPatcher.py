"""
	test the SvgPatcher functions
"""

import os
import unittest
#import sys
#sys.path.append('.')


from zutils.ZGeom import Point
from zutils.SvgPatcherInkscape import SvgPatcherInkscape
from zutils.ZPath import ZPath, ZLineSegment, ZBezier3Segment, ZArcSegment



class TestSvgPatcher(unittest.TestCase):

	s_outputRootFolder = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# now create the output folders
		folder = os.path.dirname(os.path.abspath(__file__))
		folder = os.path.dirname(folder) + '/test-out'
		if not os.path.isdir(folder):
			os.mkdir(folder)
		folder = folder + '/testSvgPatcher'
		if not os.path.isdir(folder):
			os.mkdir(folder)
		self.s_outputRootFolder = folder


	def test_00_symmetric(self):
		patcher = SvgPatcherInkscape('TemplateSymmetry.svg', 'mm', self.s_outputRootFolder + '/patchOutSym.svg')
		wid = 370
		hei = 500
		patcher.setSize(wid, hei)
		patcher.prepareSymmetry()

		g = patcher.startGroup(patcher.m_root)
		p = patcher.startPath(g)

		path = ZPath()
		start = Point(wid / 2.0, 0)
		stop = Point(300, 50)
		seg = ZLineSegment(start, stop)
		path.addSegment(seg)

		d = path.svgCode()
		patcher.setSymmetricalPath(p, d, 'fill:none;stroke:Black;stroke-width:1.5;')

		patcher.write()


	def test_05_assymmetric(self):
		patcher = SvgPatcherInkscape('Template1.svg', 'mm', self.s_outputRootFolder + '/patchOut1.svg')
		wid = 370
		patcher.setSize(wid, 500)

		patcher.addGuide('center', wid/2.0, True)
		patcher.addGuide('waist', 97, False)

		path = ZPath()

		start = Point(wid / 2.0, 0)
		stop = Point(300, 50)
		
		seg = ZLineSegment(start, stop)
		path.addSegment(seg)
		start = stop

		stop = Point(300, 100)
		seg = ZBezier3Segment(start, stop, start, stop - Point(-40, 50))
		path.addSegment(seg)

		d = path.svgCode()
		g = patcher.startGroup(patcher.m_root)
		p = patcher.startPath(g)
		self.standardStroke(p)
		p.set('d', d)
		
		#print(d)
		# make a circle
		pathCircle = ZArcSegment.createFullCircle(Point(wid/2.0, 120), 60, False)
		d = pathCircle.svgCode()
		g = patcher.startGroup(patcher.m_root)
		p = patcher.startPath(g)
		self.standardStroke(p)
		p.set('d', d)

		#print(d)

		# make a soundhole with a hole around it
		# put in in one group
		center = Point(wid/2.0, 350)
		pathCircle = ZArcSegment.createFullCircleRing(center, 100, 60)
		d = pathCircle.svgCode()
		g = patcher.startGroup(patcher.m_root)

		p = patcher.startPath(g)
		p.set('style', 'fill:#efefef;fill-opacity:1;stroke:#020405;stroke-width:0.4')
		p.set('d', d)

		#print(d)

		p = patcher.startPath(g)
		pathCircle = ZArcSegment.createFullCircle(center, 50, False)
		p = patcher.startPath(g)
		self.standardStroke(p)
		p.set('d', pathCircle.svgCode())

		patcher.write()


###############################################


	def standardStroke(self, node):
		node.set('style', 'fill:none;stroke:Black;stroke-width:1.5;')


###############################################

################################################


if __name__ == '__main__':
    unittest.main(verbosity=1)

print('----------------------------------')
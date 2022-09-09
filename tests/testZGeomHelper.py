import unittest
#import math

#import sys

#sys.path.append('.')

from zutils.ZGeom import Point
from zutils.ZGeomHelper import ZGeomHelper
#from zutils.ZD3Body import ZCone, ZCylinder


class TestZGeomHelper(unittest.TestCase):

	def test_basic(self):
		p1 = Point(1)
		p2 = Point(0, 1)
		p3 = Point(-1)
		p4 = Point(0, -1)

		expectedCW = [
			[p1, p1, 0],
			[p1, p2, 270],
			[p4, p1, 270],
			[p1, p2, 270],
			[p3, p4, 270],
			[p2, p3, 270],
			[p1, p3, 180],
			[p2, p4, 180],
			[p1, p4, 90],
			[p4, p3, 90],
			[p3, p2, 90],
			[p2, p1, 90],
		]

		for arr in expectedCW:
			point1 = arr[0]
			point2 = arr[1]
			angle = ZGeomHelper.angleBetween(Point(), point1, point2, True)
			#print(angle)
			self.assertEqual(angle, arr[2])

		for arr in expectedCW:
			point1 = arr[0]
			point2 = arr[1]
			angle = ZGeomHelper.angleBetween(Point(), point1, point2, False)
			exp = arr[2]
			if exp != 0:
				exp = 360 - exp
			#print(angle)
			self.assertEqual(angle, exp)


#############


	def comparePoints(self, p1: Point, p2: Point):
		if not p1.isSameAs(p2):
			print('different points: ---------')
			p1.printComment('p1')
			p2.printComment('p2')
		self.assertTrue(p1.isSameAs(p2))


#################################################
#################################################


if __name__ == '__main__':
    unittest.main(verbosity=1)

print('----------------------------------')
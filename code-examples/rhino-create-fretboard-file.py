# simple example of a program using ZRhino3dm.py


from zutils.ZGeom import Point
from zutils.ZRhino3dm import ZRhinoFile

def test_fretboard():
	"""
		Create a polyline curve and 2 circles defining a simple fretboard
	"""
	fName = '/d/python/zutils/code-examples/WriteFretBoard.3dm'
	rh = ZRhinoFile.newFile(fName, 'mm')
	rh.getLayerWithFullPath('FretBoard::Curves')	# creates this layer and sets it as default

	# create a polyline as 4 corners of the fretboard base
	wU = 15
	wL = 20
	l = 200
	p1 = Point(wU)
	p2 = Point(wL, l)
	p3 = Point(-wL, l)
	p4 = Point(-wU)
	rh.addPolyLine([p1, p2, p3, p4, p1], name='fretboard-base-Path')

	# create 2 points for the extrusion
	rh.addListOfNamedPoints([Point(), Point(0, 0, 12)], 'fretboard-base-Extrusion-' )

	# create 2 circles for the rounded upper surface
	r = 100
	c = Point(0, -10, -r + 10)
	rh.addCylinderCurves(c, r, c + Point(0, l + 20) , name='fretboard-rounding')

	# create the destination layer with a given color
	rh.getLayerWithFullPath('FretBoard::solids', color='maroon')

	rh.write()

#########################################

# do it

test_fretboard()
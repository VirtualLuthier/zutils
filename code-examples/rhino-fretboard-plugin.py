
import sys
sys.path.insert(0, '/d/python/zutils') # so ZRhinoBase is found for importing


# ironpython caches imported modules, so we must update ZRhinoBase (in case we change anything inside of it)
import ZRhinoBase
from imp import reload		# imp is deprecated, but rhino needs it
reload(ZRhinoBase)

import rhinoscriptsyntax as rs

##################################################

def makeFretboard():
	'''
		this function creates the solid fretboard from the curves
	'''
	# first extrude the board base polygone
	extrusionGuid = ZRhinoBase.extrudeNamedCurve('fretboard-base', complain=False)
	if extrusionGuid is None:
		return
	
	# create rounding loft
	roundingGuid = ZRhinoBase.createLoftedSurface('fretboard-rounding-', complain=False)
	if roundingGuid is not None:
		# make rounding intersection
		board = rs.BooleanIntersection([extrusionGuid], [roundingGuid], True)[0]
	else:
		# no rounding defined - take extrusion as is
		board = extrusionGuid
		
	# move board to destination layer 
	rs.ObjectLayer(board, 'FretBoard::solids')

##################################################

makeFretboard()
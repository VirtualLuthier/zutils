"""
	Several useful functions needed inside of rhino.
	Useful to see the usage of several API functions
	Used:
	- scriptcontext.doc.Objects

	- rs.AddLoftSrf()
	- rs.AddNetworkSrf()
	- rs.AddNetworkSrfEx()	??????????
	- rs.AddPatch()
	- rs.BooleanDifference()
	- rs.BooleanIntersection()
	- rs.CapPlanarHoles()
	- rs.CurveClosestPoint()
	- rs.ExtrudeCurveStraight()
	- rs.ObjectLayer()
	- rs.PointAdd()
	- rs.PointCompare()
	- rs.PointSubtract()
	- rs.ReverseCurve()
	- rs.SplitCurve()

	- Rhino.AddNetworkSrfEx() ???????????
	
	- rs.Command()
	- rs.coercebrep()
	- rs.coercecurve()
	
	- rs.UnselectAllObjects()
	- rs.SelectObject()

	Hints:
	- .Geometry.Location gives coordinates of point object
	
	Problems:
	- In makePolyhedronImpl: the call of JoinSurfaces with "delete parts = True" results in a strange error
"""

import clr

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
from Rhino.Geometry import Mesh, MeshingParameters, NurbsSurface, Brep

clr.AddReference('XNurbsRhino7Common.dll')	# dll must be stored in one of the sys.path folders!!
import XNurbsRhinoCommon

#######################################################

s_allNamedObjects = dict()

def findObjectNamed(name, complain=True):
	"""
		Find an object with the given name
	"""
	if name in s_allNamedObjects:
		return s_allNamedObjects.get(name)
	theList = sc.doc.Objects
	for obj in theList:
		if obj.Name == name:
			s_allNamedObjects[name] = obj
			return obj
	if complain:
		print('findObjectNamed(): name not found: ' + name)
	return None


def findObjectListNamed(nameRoot, start=1, complain=True):
	"""
		Find a list of objects given by names xyz-1, xyz-2, ...
		nameRoot must end with '-'
	"""
	num = start
	ret = []
	while True:
		obj = findObjectNamed(nameRoot + str(num), complain)
		if obj is None:
			return ret
		ret.append(obj)
		num += 1
		complain = False
		
		
		
def getAllNamedObjects(nameList):
	"""
		Return all objects with the names from the given names
	"""
	ret = []
	for name in nameList:
		obj = findObjectNamed(name)
		if obj is not None:
			ret.append(obj)
	return ret
	
	
def splitPathAtNamedPoints(pathName, pointNames, partPoints=None):
	"""
		find the named path and all the named points, and return the splitted objects. partPoints can be a list of point indices (starting at 0).
		if partPoints is given, a list of part curves is returned, that connect the given points.

	"""
	path = findObjectNamed(pathName)
	if path is None:
		return None
	#heelOutlineOnBottomPoints = ['Neck-OutlineOnBottomEndPoints-1', 'Neck-OutlineOnBottomEndPoints-2', 'Neck-HeelProfilePathEndPoints-2']
	points = getAllNamedObjects(pointNames)
	parts = splitCurveAtPoints(path, points)
	if partPoints is None:
		return parts
	ret = []
	for pointPair in partPoints:
		p0 = points[pointPair[0]].Geometry.Location
		p1 = points[pointPair[1]].Geometry.Location
		test = findCurvePartWithEndPoints(parts, p0, p1)
		if test is not None:
			ret.append(test)
	return ret
	
	
#def splitPathAtNamedObjects(pathName, objectNames):
#	"""
#		find the named path and all the named splitting objects, and return the splitted objects
#	"""
#	path = findObjectNamed(pathName)
#	if path is None:
#		return None
#	#heelOutlineOnBottomPoints = ['Neck-OutlineOnBottomEndPoints-1', 'Neck-OutlineOnBottomEndPoints-2', 'Neck-HeelProfilePathEndPoints-2']
#	splittingObjects = getAllNamedObjects(objectNames)
#	parts = splitCurveAtObjects(path, splittingObjects)
#	return parts
	
	
def getNamedPoints(nameRoot, complain=True):
	"""
		Get a list of named points and return them as list of rhino point tuples.
		nameRoot must end with '-'
	"""
	thePoints = findObjectListNamed(nameRoot, complain=complain)
	return [point.Geometry.Location for point in thePoints]
	
	
def getCurveEnds(curveGuid):
	"""
		Return the curve given by the guid start and end point
	"""
	curve = rs.coercecurve(curveGuid)
	return [curve.PointAtStart, curve.PointAtEnd]


def hasCurveGuidEndPoints(curveGuid, startPoint, endPoint):
	"""
		Check, if the start and end points match. If direction is wrong, reverse the curve. Return True if match can be achieved
	"""
	start, end = getCurveEnds(curveGuid)
	test1 = rs.PointCompare(start, startPoint)
	if test1:
		return rs.PointCompare(end, endPoint)
	test1 = rs.PointCompare(start, endPoint)
	if not test1:
		return False
	test2 = rs.PointCompare(end, startPoint)
	if not test2:
		return False
	# the points match, but in wrong direction
	rs.ReverseCurve(curveGuid)
	return True
	
	
def findCurvePartWithEndPoints(curveGuidList, startPoint, endPoint):
	"""
		Search a list of curves for the first one with the given start and end point. If sevaeral are found, return the first one with the right direction
		to do: reverse the Curve ????
	"""
	withWrongDirection = []
	for curveGuid in curveGuidList:
		test = hasCurveGuidEndPoints(curveGuid, startPoint, endPoint)
		if test is None:
			continue
		if test == True:
			return curveGuid
		withWrongDirection.append(curveGuid)
	if len(withWrongDirection) == 0:
		return None
	return withWrongDirection[0]
		

def makeParallelEpiped(nameRoot, complain=True):
	"""
		Get a list of 4 named points and create and return a spanned-up parallelepid from those points.
		nameRoot must end with '-'
	"""
	rhPoints = getNamedPoints(nameRoot, complain=complain)
	if len(rhPoints) < 4:
		return None
	# create all 8 corner points
	c1, c2, c4, c5 = rhPoints
	#d1 = rs.PointSubtract(c2, c1) # not used
	d2 = rs.PointSubtract(c4, c1)
	d3 = rs.PointSubtract(c5, c1)
	c3 = rs.PointAdd(c2, d2)
	c6 = rs.PointAdd(c2, d3)
	c7 = rs.PointAdd(c3, d3)
	c8 = rs.PointAdd(c4, d3)
	# create all 6 facets from the 8 points
	allFacets = [
		[c1, c2, c3, c4],
		[c1, c2, c6, c5],
		[c2, c3, c7, c6],
		[c3, c4, c8, c7],
		[c4, c1, c5, c8],
		[c5, c6, c7, c8]
	]
	return makePolyhedronImpl(allFacets)


def makePolyhedronImpl(facets):
	"""
		Internal method taking a list of lists of 3 or 4 Rhino points each
	"""
	breps = []
	for facet in facets:
		if len(facet) == 3:
			srf = NurbsSurface.CreateFromCorners(facet[0], facet[1], facet[2])
		else:
			# len == 4
			srf = NurbsSurface.CreateFromCorners(facet[0], facet[1], facet[2], facet[3])
		#sc.doc.Objects.AddSurface(srf)	# showing it is not needed
		brep = Brep.CreateFromSurface(srf)
		breps.append(brep)
	ret = rs.JoinSurfaces(breps)	# not deleting inputs . would give an error!

	#sc.doc.Views.Redraw()
	return ret
		
		
def splitCurveAtNamedPoints(curve, nameRoot, start=1):
	"""
		Split the curve at the points given by a name list
	"""
	separators = findObjectListNamed(nameRoot, start)
	return splitCurveAtPoints(curve, separators)


def splitCurveAtPoints(curve, separatorPoints):
	"""
		Split the curve at the given points (gotten by findObjectListNamed())
	"""
	if len(separatorPoints) == 0:
		return None
	params = [rs.CurveClosestPoint(curve, rs.CreateVector(x.Geometry.Location)) for x in separatorPoints]
	return rs.SplitCurve(curve, params)
	
	
#def splitCurveAtObjects(curve, separatorObjects):
#	"""
#		Split the curve at the given given objects (like curves) (gotten by findObjectListNamed())
#	"""
#	if len(separatorObjects) == 0:
#		return None
#	#params = [rs.CurveClosestPoint(curve, rs.CreateVector(x.Geometry.Location)) for x in separatorObjects]
#	return rs.SplitCurve(curve, separatorObjects)
	
	
def createMultiSurfaceNetwork(startCurves, connectionCurves, stopCurves):
	"""
		Create a list of neighbouring network surfaces and join them
	"""
	surfs = []
	for ii in range(len(startCurves)):
		surf = rs.AddNetworkSrf([connectionCurves[ii], 
			stopCurves[ii], 
			connectionCurves[ii+1],
			startCurves[ii]],
			continuity=0		# strange: seems to be needed for joinability
			)
		surfs.append(surf)
	ret = rs.JoinSurfaces(surfs, True)
	return ret


def extrudeNamedCurve(curveName, pointsName=None, close=True, complain=True):
	"""
		Extrude the named curve, use the named points. If closed == True, cap the surface. Return guid
	"""
	curve = findObjectNamed(curveName + '-Path', complain=complain)
	if curve is None:
		return None

	if pointsName is None:
		pointsName = curveName + '-Extrusion-'
	points = findObjectListNamed(pointsName)
	extrusionGuid = rs.ExtrudeCurveStraight(curve, points[0].Geometry.Location, points[1].Geometry.Location)
	if close:
		rs.CapPlanarHoles(extrusionGuid)
		
	return extrusionGuid


def createLoftedSurface(curveNameRoot, close=True, complain=True):
	"""
		Return the guid of a lofted surface through a list of named curves
	"""
	curves = findObjectListNamed(curveNameRoot, complain=complain)
	if len(curves) < 2:
		return None
	loftedGuid = rs.AddLoftSrf(curves)
	if close:
		rs.CapPlanarHoles(loftedGuid)	
	return loftedGuid
	
	
def createMesh(objGuid):
	"""
		Create a smooth mesh for an object, return the guid
	"""
	brep = rs.coercebrep(objGuid)
	params = MeshingParameters.Smooth
	meshes = Mesh.CreateFromBrep(brep, params)
	
	brepMesh = Mesh()
	for mesh in meshes:
		brepMesh.Append(mesh)
	guid = sc.doc.Objects.AddMesh(brepMesh)
	sc.doc.Views.Redraw()
	return guid


def exportAsStl(objGuid, stlName):
	"""
		Create a mesh for the objGuid, export it as stl file and delete it
	"""
	if stlName is None:
		return
	objMeshGuid = createMesh(objGuid)
	rs.UnselectAllObjects()
	rs.SelectObject(objMeshGuid)
	rs.Command('_-Export ' + chr(34) + stlName + chr(34) + ' _Enter', True)
	rs.SelectObject(objMeshGuid)
	rs.Command('_Delete')


def makeArrow(curveName, complain=True):
	curve = findObjectNamed(curveName, complain=complain)
	if curve is not None:
	#Rhino.CurveArrows(curve, 3)
		rs.CurveArrows(curve, 2)



# rhinoscript to create an arrow and a text marker (food for thought)
#Option Explicit
#    Call Main()
#    Sub Main()
#       
#    	Dim arrP : arrP = Rhino.GetPoints(True,,,, 2)
#    	If isnull(arrP) Then Exit Sub
#    	If Ubound(arrP) <> 1 Then Exit Sub
#
#    	Dim idL : idL = Rhino.AddLine(arrP(0), arrP(1))
#    	Call Rhino.CurveArrows(idL, 3)

#    	Dim idDot : idDot = Rhino.AddTextDot(Round(Rhino.CurveLength(idL), 2), Rhino.CurveMidPoint(idL))
#
#    	Call Rhino.SelectObjects(array(idL, idDot))
#    	
#    End Sub
	

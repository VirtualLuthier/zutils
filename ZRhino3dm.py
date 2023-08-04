"""
	Some classes to create the structures of a rhino3dm.File3dm
	Currently creates Layers, Groups, Points and Curves in a convenient way.
	See testRhino.py for usage
	see https://mcneel.github.io/rhino3dm/python/api/File3dm.html
	see https://github.com/mcneel/rhino-developer-samples
"""

##########################################################

from __future__ import annotations
import os
import uuid
import logging

import rhino3dm as rhino
import rhino3dm._rhino3dm as rhinoInternal
import matplotlib.colors as matcolors


from zutils.ZGeom import Point
from zutils.ZMatrix import Affine


##############################################################
##############################################################


class ZRhinoFile:
	"""
		Encapsulates a rhino3dm.File3dm
	"""

	########### the Affine stack:
	s_currentAffine = Affine()
	s_affineStack = []

	@classmethod
	def affineReset(cls):
		cls.s_affineStack = []
		cls.affineRecalc()


	@classmethod
	def affineRecalc(cls):
		cls.s_currentAffine = Affine()
		for aff in cls.s_affineStack:
			cls.s_currentAffine = aff * cls.s_currentAffine


	@classmethod
	def affinePush(cls, aff):
		cls.s_affineStack.append(aff)
		cls.affineRecalc()


	@classmethod
	def affinePop(cls):
		cls.s_affineStack.pop()
		cls.affineRecalc()


############################################################


	@classmethod
	def newFile(cls, fName: str, unit: str) -> ZRhinoFile:
		"""
			Creates an empty ZRhinoFile, that is tied to the fName
		"""
		fileObject = rhino.File3dm()
		if unit == 'mm':
			theUnit = rhinoInternal.UnitSystem.Millimeters	#  2		#rhino.UnitSystem.Millimeters, see https://developer.rhino3d.com/5/api/RhinoCommon/html/T_Rhino_UnitSystem.htm
		elif unit == 'inch':
			theUnit = rhinoInternal.UnitSystem.Inches			#	8		#rhino.UnitSystem.Inches
		else:
			raise Exception('ZRhino3dm:newFile: illegal unit (only mm or inc allowed)')
		fileObject.Settings.ModelUnitSystem = theUnit
		return ZRhinoFile(fName, fileObject)


	def __init__(self, fName, fObject):
		self.affineReset()
		self.m_fName = fName
		self.m_fileObject = fObject
		self.m_layers = [ZRhinoLayer(layer) for layer in  fObject.Layers]
		self.m_objects = [ZRhinoObject(o) for o in fObject.Objects]
		self.m_currentLayer = None
		self.m_currentGroup = None


	def write(self, version=0):
		"""
			Write the file. If it currently opened by Rhino itself, it fails and gives an Exception
		"""
		ret = self.m_fileObject.Write(self.m_fName, version)
		if not ret:
			raise Exception('ZRhinoFile:write: could not write ' + self.m_fName + ' (is it open?)')


	def getLayerWithFullPath(self, fullPath, color=(0,0,0,255)):
		"""
			Returns the wanted (sub-)layer. Creates whole hierarchy, if needed.
		"""
		for layer in self.m_layers:
			if layer.FullPath == fullPath:
				self.m_currentLayer = layer
				return layer
		if not '::' in fullPath:
			return self.addLayer(fullPath, color=color)
		parts = fullPath.split('::')
		name = parts.pop()
		parentName = '::'.join(parts)
		parent = self.getLayerWithFullPath(parentName, color)
		return self.addLayer(name, parent.Id, color=color)


	def addListOfNamedPoints(self, points, nameRoot, first=1):
		num = first
		for point in points:
			self.addPoint(point, name=nameRoot + str(num))
			num += 1


	def addSvgPath(self, path, name=None):
		"""
			Adds a path from zutils.ZPath to this file.
			If there are several segments, combine them in a polycurve.
			Raise exception, if path contains a non-circle Ellipse
		"""
		if not path.areSegsConnected():
			path.printComment('not-connected path')
			raise Exception('ZRhinoFile:addSvgPath: path segments are not connected')
		segs = path.m_segments
		polyCurve = None
		if len(segs) > 1:
			polyCurve = self.createPolyCurve()
		for seg in segs:
			self.addSvgSegment(seg, name=name, polyCurve=polyCurve)
		if polyCurve is not None:
			self.addCurve(polyCurve, name)


	def addPathExtrusion(self, path, name, p1, p2):
		"""
			Add a named path and 2 points that describe the extrusion
		"""
		self.addSvgPath(path, name=name+'-Path')
		self.addListOfNamedPoints([p1, p2, ], name+'-Extrusion-' )


	def addPoint(self, point, name=None):
		"""
			Create a point and add it to object table
		"""
		rhPoint = rhino.Point(self.makeRhinoPoint(point))
		self.m_fileObject.Objects.Add(rhPoint, self.makeAttributes(name))


	def getGroup(self, name):
		"""
			Return an existing or create a group with this name. Also make it current.
			If name is None, reset the current group
		"""
		if name is None:
			self.m_currentGroup = None
			return
		gTable = self.m_fileObject.Groups
		oldGroup = gTable.FindName(name)
		if oldGroup is not None:
			self.m_currentGroup = oldGroup
			return
		newGroup = rhino.Group()
		newGroup.Name = name
		gTable.Add(newGroup)
		self.m_currentGroup = gTable.FindName(name)



	def dump(self):
		"""
			Output some useful information from the file
		"""
		print(f'ZRhinoFile {self.m_fName}')
		for sub in [self.m_layers]:
			for subSub in sub:
				subSub.dump()
		for obj in self.m_objects:
			obj.dump(self.m_layers)
		print(self.m_fileObject.Settings.ModelUnitSystem)
		#views = self.m_fileObject.Views
		#for view in views:
		#	print(view)
		#	details = view.GetDetailViews()


	def findUniqueObjectNamed(self, name, objectType=None, layerName=None):
		"""
			Search for an object with this name and return it (or None, if not found)
			Also return None, if name is not unique
		"""
		ret = None
		for o in self.m_objects:
			nm = o.getName()
			if nm != name:
				continue
			if objectType is not None:
				if o.getObjectType() != objectType:
					continue
			if layerName is not None:
				oLayer = self.findLayerOf(o)
				if oLayer.fullPath() != layerName:
					continue
			if ret is not None:
				print ('ZRhinoFile::findUniqueObjectNamed: name is not unique: ' + name)
				return None
			ret = o
		return ret


	def findLayerOf(self, obj):
		idx = obj.getLayerIdx()
		return self.m_layers[idx]


	def addLayer(self, layerName, parentId=None, color=(0,0,0,255)):
		"""
			adds a (sub) layer with given name and parent layer
		"""
		if '::' in layerName:
			raise Exception('ZRhinoFile:addLayer: layer name must not contain ::')
		color = self.getColorAsTuple(color)
		num = self.m_fileObject.Layers.AddLayer(layerName, color)
		self.m_layers = self.m_fileObject.Layers
		layer = self.m_layers[num]
		if parentId is not None:
			layer.ParentLayerId = parentId
			self.m_layers = self.m_fileObject.Layers
		self.m_currentLayer = layer
		return layer


	def getExistingLayerWithFullPath(self, fullPath):
		"""
			Returns the wanted (sub-)layer. Returns None, if not found
		"""
		for layer in self.m_layers:
			if layer.FullPath == fullPath:
				self.m_currentLayer = layer
				return layer
		return None


	def createPolyCurve(self):
		"""
			Return a new PolyCurve. It must be added after being filled with addCurve()
		"""
		return rhino.PolyCurve()


	def addLine(self, start, stop, name=None, polyCurve=None):
		"""
			Add a nurbs curve from a line segment. Set name, group and layer. . If polyCurve is given, add to it
		"""
		line = rhino.Line(self.makeRhinoPoint(start), self.makeRhinoPoint(stop))
		curve = rhino.NurbsCurve.CreateFromLine(line)
		self.addCurve(curve, name, polyCurve)


	def addPolyLine(self, points, name=None, polyCurve=None):
		"""
			Add a nurbs curve from a point array. Set name, group and layer. If polyCurve is given, add to it
		"""
		#line = rhino.Line(self.makeRhinoPoint(start), self.makeRhinoPoint(stop))
			#.CreateFromLine(line)
		rhPoints = rhino.Point3dList(len(points))
		#idx = 0
		for p in points:
			#print(idx)
			rhP = self.makeRhinoPoint(p)
			rhPoints.Add(rhP.X, rhP.Y, rhP.Z)					#	SetPoint(idx, self.makeRhinoPoint(p))
			#idx += 1

		curve = rhino.PolylineCurve(rhPoints)

		self.addCurve(curve, name, polyCurve)


	def addSvgSegment(self, seg, name, polyCurve):
		"""
			Add an svg segment to myself or the given polycurve
			Raise exception, if segment is a non-circle Ellipse.
			If polyCurve is given, add to it
		"""
		className = seg.__class__.__name__
		start = seg.m_start
		stop = seg.m_stop
		if className == 'ZLineSegment':
			self.addLine(start, stop, name, polyCurve)
			return
		if className in ['ZBezier3Segment', 'ZBezier2Segment']:
			self.addBezierCurve(seg, name, polyCurve)
			return
		if className == 'ZArcSegment':
			if seg.isACircle():
				interP = seg.getMyMiddlePoint()
				self.addArcCurve(seg.m_start, interP, seg.m_stop, name, polyCurve)
				return

		raise Exception('ZRhinoFile:addSvgSegment: cannot handle ellipse ' + className)


	def addArcCurve(self, startP, interP, endP, name=None, polyCurve=None):
		"""
			Add a partial circle arc. If polyCurve is given, add to it
		"""
		rhStart, rhInter, rhEnd = [self.makeRhinoPoint(x) for x in [startP, interP, endP]]
		arc = rhino.Arc(rhStart, rhInter, rhEnd)
		curve = rhino.ArcCurve(arc)
		self.addCurve(curve, name, polyCurve)


	def addFullCircle(self, center, radius, normal=None, startDir=None, name=None):
		"""
			Create and add a full circle curve. If normal == None in x-y-plain.
			startDir is a Vector from center to the startPoint(perpendicular to normal, important for lofting)
			In reality creates a polycurve with 2 half circles. If polyCurve is given, add to it
		"""
		if normal is None:
			normal = Point(0, 0, 1)
		if normal.isSameAs(Point()):
			raise Exception('ZRhinoFile:addFullCircle: null as normal is illegal')
		if startDir is not None:
			if not startDir.isPerpendicular(normal):
				raise Exception('ZRhinoFile:addFullCircle: startDir must be perpendicular to normal')
			dire1 = startDir.scaledTo(radius)
		else:
			dire1 = normal.anyPerpendicularPoint().scaledTo(radius)
		dire2 = normal.crossProduct(dire1).scaledTo(radius)
		start = center + dire1
		inter = center + dire2
		stop = center - dire1
		polyCurve = self.createPolyCurve()
		self.addArcCurve(start, inter, stop, name, polyCurve=polyCurve)
		inter = center - dire2
		self.addArcCurve(stop, inter, start, name=name, polyCurve=polyCurve)
		self.addCurve(polyCurve, name=name)


	def addBezierCurve(self, points, name=None, polyCurve=None):
		"""
			Add a nurbs curve from a 2-or-3 bezier segment. Set name and layer.
			Points must either be a ZBezierSegent or a list with 3 or 4 points
		"""
		if not isinstance(points, list):
			if points.__class__.__name__ == 'ZBezier3Segment':
				rhPoints = self.makeRhinoPoints([points.m_start, points.m_handleStart, points.m_handleStop,  points.m_stop])
			elif points.__class__.__name__ == 'ZBezier2Segment':
				rhPoints = self.makeRhinoPoints([points.m_start, points.m_handle,  points.m_stop])
		else:
			rhPoints = self.makeRhinoPoints(points)
		curve = rhino.NurbsCurve.Create(False, len(rhPoints) - 1, rhPoints)
		self.addCurve(curve, name, polyCurve)


	def addCurve(self, curve, name=None, polyCurve=None):
		"""
			Add any curve. Set name and layer. If polyCurve is given, add to it
		"""

		if polyCurve is not None:
			polyCurve.Append(curve)
			return
		self.m_fileObject.Objects.AddCurve(curve, self.makeAttributes(name))


	def addTextDot(self, point, text):
		rPoint = self.makeRhinoPoint(point)
		self.m_fileObject.Objects.AddTextDot(text, rPoint)


	def addTextArrow(self, point, text, point2, name=None):
		self.addTextDot(point, text)
		self.addLine(point, point2, name=name)


	def addConeCurvesOld(self, start, radius1, stop, radius2, name=None):
		"""
			Add 2 circles that can be lofted to a cone
		"""
		normal = stop - start
		startDir = normal.anyPerpendicularPoint()
		self.addFullCircle(start, radius1, normal, startDir=startDir, name=name + '-1')
		self.addFullCircle(stop, radius2, normal, startDir=startDir, name=name + '-2')


	def addConeCurves(self, cone, name=None):
		"""
			Add 2 circles that can be lofted to this cone (or cylinder)
			(take the circles around cone.m_p1, ...m_p2)
		"""
		start = cone.getCenterPointFor(cone.m_p1)
		stop = cone.getCenterPointFor(cone.m_p2)
		direction = cone.m_centerLine.m_direction
		#l = self.m_roundingCone.m_centerHeight
		r1 = cone.getRadius1()
		r2 = cone.m_r2
		#normal = stop - start
		startDir = direction.anyPerpendicularPoint()
		self.addFullCircle(start, r1, direction, startDir=startDir, name=name + '-1')
		self.addFullCircle(stop, r2, direction, startDir=startDir, name=name + '-2')


	def addCylinderCurvesOld(self, start, radius, stop, name=None):
		"""
			Add 2 circles that can be lofted to a cylinder
		"""
		self.addConeCurvesOld(start, radius, stop, radius, name=name)


	def makeAttributes(self, name=None):
		"""
			Return an rhino.ObjectAttributes with set name, group and layer
		"""
		attributes = rhino.ObjectAttributes()
		if name is not None:
			attributes.Name = name
		layer = self.m_currentLayer
		if layer is not None:
			attributes.LayerIndex = layer.Index
		group = self.m_currentGroup
		if group is not None:
			attributes.AddToGroup(group.Index)
		return attributes


	@classmethod
	def readFile(cls, fName: str) -> ZRhinoFile:
		"""
			Returns a ZRhinoFile that has read the contents of fName
		"""
		if not os.path.exists(fName):
			print(f'ZRhinoFile:readFile: file not found: {fName}')
			return None
		fileObject = rhino.File3dm.Read(fName)
		if fileObject is None:
			return None
		return ZRhinoFile(fName, fileObject)
		



	@classmethod
	def isEmptyUid(cls, uid: uuid.UUID) -> bool:
		"""
			Return true, if uid == the empty guid 00000000-0000-0000-0000-000000000000
		"""
		return uid == uuid.UUID(int=0)


	@classmethod
	def makeRhinoPoint(cls, point: Point) -> rhino.Point3d:
		"""
			Return a Rhino point for the given Point
		"""
		pAff = cls.s_currentAffine * point
		return rhino.Point3d(pAff.m_x, pAff.m_y, pAff.m_z)


	@classmethod
	def makeRhinoPoints(cls, points: list[Point]) -> list[rhino.Point3d]:
		"""
			Return a Rhino point for the given Point
		"""
		#return [rhino.Point3d((point.m_x, point.m_y, point.m_z) for point in points]
		return [cls.makeRhinoPoint(point) for point in points]


	@classmethod
	def getColorAsTuple(cls, colorNameOrTuple):
		"""
			Return a tuple (r, g, b, a) 0..255 Use strings from matplotlib
		"""
		if isinstance(colorNameOrTuple, list) or isinstance(colorNameOrTuple, tuple):
			if len(colorNameOrTuple) == 4:
				return tuple(colorNameOrTuple)
			return tuple(colorNameOrTuple, 255)	# ?????????????????????

		colorName = colorNameOrTuple.lower()
		color = matcolors.cnames.get(colorName, None)
		if color is None:
			logging.error('ZRhinoFile:getColorAsTuple: color not found: %s', colorName)
			return (0, 0, 0, 255)
		rs = int(color[1:3], 16)
		gs = int(color[3:5], 16)
		bs = int(color[5:], 16)
		return (rs, gs, bs, 255)
		

#####################################################
#####################################################


class ZRhinoLayer:
	"""
		Encapsulates a Rhino Layer
	"""
	def __init__(self, layer):
		self.m_layer = layer


	def dump(self):
		"""
			Outputs a textual description
		"""
		layer = self.m_layer
		print(f'rhino3dm.Layer ({layer.Name}) -----------')
		if layer.FullPath != layer.Name:
			print(f'	Full path: ({layer.FullPath}) -----------')
		#print('	Id: (' + str(layer.Id) + ') -----------')
		parId = layer.ParentLayerId
		if not ZRhinoFile.isEmptyUid(parId):
			print(f'	ParId: ({str(layer.ParentLayerId)}) -----------')
		#print('	IgesLevel: ' + str(layer.IgesLevel)) # is always -1, also for nested layers
		print(f'	Index: {str(layer.Index)}') # is always -1, also for nested layers
		#print('	LinetypeIndex: ' + str(layer.LinetypeIndex)) # is always -1, also for nested layers


	def fullPath(self):
		return self.m_layer.FullPath


###################################################
###################################################


class ZRhinoObject:
	"""
		Encapsulates a rhino object. Provides some convenience methods
	"""
	def __init__(self, theObject):
		self.m_object = theObject
		

	def getName(self):
		return self.m_object.Attributes.Name


	def getLayerIdx(self):
		return self.m_object.Attributes.LayerIndex


	def getObjectType(self):
		return str(self.m_object.Geometry.ObjectType)


	def dump(self, layers):
		o = self.m_object
		print('	object: ---------')
		print(f'		{str(o.Geometry.ObjectType)}')
		print(f'		name: "{self.getName()}"')
		#print(attr.Mode)
		#print('		mode: ' + str(attr.Mode))		# ObjectMode: Normal | Locked | Hidden
		idx = self.getLayerIdx()
		layerName = layers[idx].fullPath()
		print(f'		layer: {layerName}') 		#str(attr.LayerIndex))


	def getPoints(self):
		ret = []
		points = self.m_object.Geometry.Points
		size = len(points)
		for ii in range(size):
			p = points[ii]
			ret.append(Point(p.X, p.Y, p.Z))
		return ret


	def getKnots(self):
		ret = []
		knots = self.m_object.Geometry.Knots
		size = len(knots)
		for ii in range(size):
			k = knots[ii]
			ret.append(k)
		return ret

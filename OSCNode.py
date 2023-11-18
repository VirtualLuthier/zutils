"""
	Contains a lot of OpenScad classes.
	Usage:
	- create a object of class OSCRoot
	- build a hierarchy of other OSCClass objects under the root (with addChild())
	- call root.writeScadTo(fileName)
"""

# should also be regarded: CadQuery

###############################################
###############################################


import math

import xml.etree.ElementTree as ET
from xml.dom import minidom

from zutils.ZGeom import Point, Line, Plane, Polygon, Circle2
from zutils.ZMatrix import Matrix, Affine
from zutils.ZUnits import ZUnits

# also uses Form3d in class OSCForm3d


#################################################
#################################################


class OSCAbstract:
	"""
		The base class of the OSCAD classes
	"""
	s_floatPrecision = 7

	s_floatThreshold = 0		#	0.1 ** s_floatPrecision
	s_floatFormat = '%.4f'
	s_vectorFormat2 = '[%.4f, %.4f]'
	s_vectorFormat3 = '[%.4f, %.4f, %.4f]'
	s_vectorFormat4 = '[%.4f, %.4f, %.4f, %.4f]'
	

	@classmethod
	def setFloatPrecision(cls, prec):
		"""
			define the precision of the output of coordinates
		"""
		OSCAbstract.s_floatPrecision = prec
		OSCAbstract.s_floatThreshold = 0.1 ** OSCAbstract.s_floatPrecision
		OSCAbstract.s_floatFormat = '%.' + str(prec) + 'f'
		OSCAbstract.s_vectorFormat2 = cls.floatPrecisionString(prec, 2)
		OSCAbstract.s_vectorFormat3 = cls.floatPrecisionString(prec, 3)
		OSCAbstract.s_vectorFormat4 = cls.floatPrecisionString(prec, 4) 


	@classmethod
	def floatPrecisionString(cls, prec, num):
		prc = str(prec)
		ret = '['
		for ii in range(num):
			ret += '%.' + prc + 'f'
			if ii < num - 1:
				ret += ', '
		ret += ']'
		return ret


	def __init__(self, name):
		if OSCAbstract.s_floatThreshold == 0:
			OSCAbstract.setFloatPrecision(OSCAbstract.s_floatPrecision)
		self.m_children = []
		self.m_type = 'abstract'
		self.m_name = name
		self.m_parent = None


	def add(self, child):
		self.m_children.append(child)
		child.m_parent = self
		return child


	def writeToFile(self, f, tabNo):
		for child in self.m_children:
			child.writeToFile(f, tabNo+1)


	def getTransformation(self):
		runner = self
		transform = Affine()
		while runner is not None:
			if isinstance(runner, OSCTransform):
				transform = runner.m_affine * transform
			runner = runner.m_parent
		return transform
			

	def writeTabs(self, f, tabs):
		for _ in range(tabs):
			f.write(' ')


	def writeBlockOpen(self, f, tabs):
		self.writeTabs(f, tabs)
		f.write('{\n')


	def writeBlockClose(self, f, tabs, writeName=False):
		self.writeTabs(f, tabs)
		name = ''
		if writeName:
			name = '	// end of ' + self.m_name
		f.write('}' + name + '\n')


	def writeName(self, f, tabs):
		self.writeTabs(f, tabs)
		f.write('// '+self.m_name + '\n')


	def writeTranslate(self, f, vector):
		if vector.isSameAs(Point()):
			return
		f.write('translate(')
		self.writePoint3(f, vector)
		f.write(') ')


	def writeRotate(self, f, src, trg):
		# currently obsoleted by affine handling
		pivot = src.unit() + trg.unit()
		if pivot.distanceOf(Point(0, 0, 0)) < 0.01:
			# it is just a reversion, make some kind of mirror
			oldLine = Line(Point(0, 0, 0), src)
			otherLine = oldLine.anyPerpendicularLineThrough(Point(0, 0, 0))
			pivot = otherLine.m_direction.unit()
		f.write('rotate(a=180, v=')
		self.writePoint3(f, pivot)
		f.write(') ')


	def writeAffine(self, f, affine):
		"""
			Write the given affine to the OSCAD file.
			Handles orthonormal and non-orthonormal affines
		"""
		if not affine.m_matrix.isOrthonormal() or not affine.m_matrix.preservesOrientation():
			self.writeMultMatrix(f, affine)
			return
		# we handle here the orthonormal case
		m = affine.m_matrix
		self.writeTranslate(f, affine.m_shift)
		if affine.isTranslation():
			return

		angles = m.getEulerAngles()
		f.write('rotate(')
		self.writeFloatList(f, OSCAbstract.s_vectorFormat3, [angles[0], angles[1], angles[2]])
		#f.write(OSCAbstract.s_vectorFormat3 % (angles[0], angles[1], angles[2]))
		f.write(') ')


	def writeMultMatrix(self, f, affine):
		f.write('multmatrix(m=[')
		m = affine.m_matrix
		s = affine.m_shift
		for ii in range(3):
			p = m.m_lines[ii]
			#f.write(OSCAbstract.s_vectorFormat4 % (p.m_x, p.m_y, p.m_z, s[ii]))
			self.writeFloatList(f, OSCAbstract.s_vectorFormat4, [p.m_x, p.m_y, p.m_z, s[ii]])
			f.write(', ')
		f.write('[0, 0, 0, 1]')
		f.write('])')


	def writePoint2(self, f, point):
		#f.write(OSCAbstract.s_vectorFormat2 % (point.m_x, point.m_y))
		self.writeFloatList(f, OSCAbstract.s_vectorFormat2, [point.m_x, point.m_y])


	def writePoint3(self, f, point):
		#f.write(OSCAbstract.s_vectorFormat3 % (point.m_x, point.m_y, point.m_z))
		self.writeFloatList(f, OSCAbstract.s_vectorFormat3, [point.m_x, point.m_y, point.m_z])


	def writeFloatList(self, f, numFormat, numArray):
		"""
			used to get rid of the -0.00 stuff
		"""
		f.write(self.getFloatListString(numFormat, numArray))


	def getFloatListString(self, numFormat, numArray):
		"""
			used to get rid of the -0.00 stuff
		"""
		arr = []
		for x in numArray:
			if math.isnan(x):
				print('trying to write math.nan to scad file')
			if abs(x) < OSCAbstract.s_floatThreshold:
				x = 0
			arr.append(x)
		return numFormat % tuple(arr)


	def vectorLength(self, v):
		return v.distanceOf(Point(0, 0, 0))


	def printStructure(self, tabNo=0):
		for _ in range(tabNo):
			print('-', end='')
		print(self.structureString())
		for child in self.m_children:
			child.printStructure(tabNo+1)


	def structureString(self):
		return self.m_type + ' | "' + self.m_name + '"'


	def addXmlTo(self, parXml):
		node = ET.SubElement(parXml, self.__class__.__name__)
		node.set('name', self.m_name)
		self.addXmlDescriptionTo(node)
		for child in self.m_children:
			child.addXmlTo(node)


######################################################
######################################################


class OSCRoot(OSCAbstract):
	"""
		The root node of a OSCAD hierarchy
	"""
	s_quality = 50

	def __init__(self, name): #, circleQuality=math.nan):
		super().__init__(name)
		self.m_type = 'root'
		#if math.isnan(circleQuality):
		#	circleQuality = OSCRoot.s_quality
		#OSCRoot.s_quality = circleQuality
		#self.m_circleQuality = circleQuality


	def writeScadTo(self, fileName):
		if fileName is None:
			return
		with open(fileName, "w", encoding='utf-8') as f:
			f.write('$fn='+str(self.s_quality)+';\n\n')
			self.writeToFile(f, -1)


	def writeXmlTo(self, fileName):
		root = ET.Element('z3d')
		self.addXmlTo(root)
		
		rough_string = ET.tostring(root, 'utf-8')
		#print(rough_string)
		with open('test.txt', "w", encoding='utf-8') as ff:
			ff.write(rough_string.decode('utf-8'))

		reparsed = minidom.parseString(rough_string)
		nice = reparsed.toprettyxml(indent="	", newl='\n')
		with open(fileName, "w", encoding='utf-8') as f:
			f.write(nice)


	def addXmlDescriptionTo(self, _):
		pass


####################################################
####################################################


class OSCTransform(OSCAbstract):
	"""
		Describes an affine transformation of all of its children
	"""
	def __init__(self, name, affine):
		super().__init__(name)
		self.m_affine = affine
		self.m_type = 'transform'


	def writeToFile(self, f, tabNo):
		self.writeName(f, tabNo)
		self.writeAffine(f, self.m_affine)
		self.writeBlockOpen(f, tabNo)
		OSCAbstract.writeToFile(self, f, tabNo)
		self.writeBlockClose(f, tabNo, True)


	def addXmlDescriptionTo(self, node):
		node.set('affine', self.m_affine.xmlCoords())
		#self.addXmlAffineTo(node, self.m_affine)


##################################################
##################################################


class OSCModule(OSCAbstract):
	"""
		Encapsulates a module in OSCAD. Currently seldom used
	"""
	def __init__(self, name, nameWithBrackets):
		super().__init__(name)
		self.m_nameWithBrackets = nameWithBrackets
		self.m_type = 'module'


	def writeToFile(self, f, tabNo):
		f.write('\n/////////////////////////\n\n')
		self.writeName(f, tabNo)
		self.writeTabs(f, tabNo)
		f.write('module '+ self.m_nameWithBrackets)
		self.writeBlockOpen(f, tabNo)
		OSCAbstract.writeToFile(self, f, tabNo)
		self.writeBlockClose(f, tabNo, True)
		f.write('\n/////////////////////////\n\n')


	def addXmlDescriptionTo(self, node):
		theId = self.m_nameWithBrackets
		idx = theId.find('(')
		theId = theId[0:idx]
		node.set('id', theId)


#################################################
#################################################


class OSCAddMirror(OSCAbstract):
	"""
		Currently not used (make something mirrored)
	"""
	def __init__(self, name, normal, nameWithBrackets):
		super().__init__(name)
		self.m_nameWithBrackets = nameWithBrackets
		self.m_normal = normal
		self.m_type = 'AddMirror'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write(self.m_nameWithBrackets + '; {mirror(')
		self.writePoint3(f, self.m_normal)
		f.write(') ')
		f.write(self.m_nameWithBrackets + ';}\n\n')


	def addXmlDescriptionTo(self, node):
		theId = self.m_nameWithBrackets
		idx = theId.find('(')
		theId = theId[0:idx]
		node.set('call', theId)


#####################################################
#####################################################


class OSCCallModule(OSCAbstract):
	"""
		Currently not used
	"""
	def __init__(self, name, callString):
		super().__init__(name)
		self.m_callString = callString
		self.m_type = 'CallModule'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write(self.m_callString)
		f.write('\n\n')


#####################################################
#####################################################


class OSCPolygon(OSCAbstract):
	"""
		Encapsulates a OSCAD Polygon
	"""
	def __init__(self, name, points):
		super().__init__(name)
		self.m_points = points
		self.m_type = 'polygon'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('polygon([')
		for point in self.m_points:
			self.writePoint2(f, point)
			f.write(', ')
		f.write(']);\n')


	def addXmlDescriptionTo(self, node):
		#node.set('points', '...')
		Point.xmlAddPointList(node, self.m_points)


####################################################
####################################################


class OSCPath(OSCPolygon):
	"""
		Encapsulates a (svg) path in OSCAD
	"""
	def __init__(self, name, path, qualityFactor=math.nan):
		super().__init__(name, [])
		self.m_type = 'path'
		if not math.isnan(qualityFactor):
			quality = round(OSCRoot.s_quality * qualityFactor)
			quality = max([quality, 3])
			self.m_quality = quality
		else:
			self.m_quality = math.nan
		if math.isnan(self.m_quality):
			delta = 1 / OSCRoot.s_quality
		else:
			delta = 1 / self.m_quality
		points = path.getInterPoints(delta)
		self.m_points = points


#####################################################
#####################################################


class OSCCircle(OSCAbstract):
	"""
		Currently seldom used
	"""
	def __init__(self, name, center, radius):
		super().__init__(name)
		self.m_center = center
		self.m_radius = radius
		self.m_type = 'circle'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('{')
		self.writeTranslate(f, self.m_center)
		f.write('circle('+str(self.m_radius)+');')
		f.write('}\n')


####################################################
####################################################


class OSCSphere(OSCAbstract):
	"""
		Currently seldom used
	"""
	def __init__(self, name, center, radius):
		super().__init__(name)
		self.m_center = center
		self.m_radius = radius
		self.m_type = 'sphere'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('{')
		self.writeTranslate(f, self.m_center)
		f.write('sphere('+str(self.m_radius)+');')
		f.write('}\n')


####################################################
####################################################


class OSCCylinder(OSCAbstract):
	"""
		Encapsulates a OSCAD cylinder
	"""
	def __init__(self, name, startPoint, directionVector, length, radius, radius2=-1, qualityFactor=math.nan):
		# directionVector is meant from start to the end
		super().__init__(name)
		self.m_startPoint = startPoint
		self.m_directionVector = directionVector
		self.m_length = length
		self.m_radius = radius
		self.m_radius2 = radius2
		if self.m_radius2 < 0:
			self.m_radius2 = self.m_radius
		if math.isnan(self.m_radius) or math.isnan(self.m_radius2):
			print(f'OSCCylinder with radius nan! ({name})')
		if not math.isnan(qualityFactor):
			quality = round(OSCRoot.s_quality * qualityFactor)
			quality = max([quality, 3])
			self.m_quality = quality
		else:
			self.m_quality = math.nan
		self.m_type = 'cylinder'


	def enlarge(self, before=math.nan, after=0):
		# positive values mean enlargement
		if math.isnan(before):
			before = ZUnits.changeMmToMmOrInch(0.5)
		if math.isnan(after):
			after = ZUnits.changeMmToMmOrInch(0.5)
		unit = self.m_directionVector.unit()
		rDerivation = (self.m_radius2 - self.m_radius) / self.m_length
		if before != 0:
			newRadius = self.m_radius - rDerivation * before
			self.m_startPoint = self.m_startPoint + unit.scaledBy(-before)
			self.m_radius = newRadius
			self.m_length += before
		if after != 0:
			newRadius2 = self.m_radius2 + rDerivation * after
			self.m_radius2 = newRadius2
			self.m_length += after


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('{')

		matrix = Matrix.makeOrthonormalTransformation(pz=self.m_directionVector)
		affine = Affine(matrix, self.m_startPoint)
		self.writeAffine(f, affine)
		qualityString = ''
		if not math.isnan(self.m_quality):
			qualityString = ', $fn='+str(self.m_quality)
		fmt = OSCAbstract.s_floatFormat
		outString = 'cylinder('+ fmt + ', ' + fmt + ', ' + fmt + qualityString + ');'
		#print(outString)
		f.write(outString % (self.m_length, self.m_radius, self.m_radius2))
		#f.write('cylinder('+ str(round(self.m_length, 3))+', '  +  str(round(self.m_radius, 3))+', ' + str(round(self.m_radius2, 3)) +qualityString+');')
		f.write('}\n')


	def addXmlDescriptionTo(self, node):
		node.set('length', str(self.m_length))
		node.set('radius', str(self.m_radius))
		node.set('radius2', str(self.m_radius2))
		node.set('start', self.m_startPoint.xmlCoords())
		node.set('direction', self.m_directionVector.xmlCoords())


####################################################
####################################################


class OSCCube(OSCAbstract):
	"""
		Creates a cube with the given widths, euler angles and targetPoint
	"""
	def __init__(self, name, xWidth, yWidth, zWidth, ax, ay, az, targetPoint):
		super().__init__(name)
		self.m_xWidth = xWidth
		self.m_yWidth = yWidth
		self.m_zWidth = zWidth
		self.m_angleX = ax
		self.m_angleY = ay
		self.m_angleZ = az
		self.m_targetPoint = targetPoint
		self.m_type = 'cube'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('{')


		sp = self.m_targetPoint
		self.writeTranslate(f, sp)
		rotationPoint = (Point(self.m_angleX, self.m_angleY, self.m_angleZ))
		if not rotationPoint.isSameAs(Point()):
			f.write('rotate(')
			self.writePoint3(f, rotationPoint)
			f.write(') ')
		f.write('cube(['+ str(self.m_xWidth)+', '  +  str(self.m_yWidth)+', ' + str(self.m_zWidth) +']);')
		f.write('}\n')


	
	def addXmlDescriptionTo(self, node):
		node.set('target', self.m_targetPoint.xmlCoords())
		node.set('xWidth', str(self.m_xWidth))
		node.set('yWidth', str(self.m_yWidth))
		node.set('zWidth', str(self.m_zWidth))
		node.set('angleX', str(self.m_angleX))
		node.set('angleY', str(self.m_angleY))
		node.set('angleZ', str(self.m_angleZ))
		

####################################################
####################################################


class OSCCube2(OSCAbstract):
	"""
		Creates a cube with the given x-y-z sizes and an Affine
	"""
	def __init__(self, name, xWidth, yWidth, zWidth, affine):
		super().__init__(name)
		self.m_xWidth = xWidth
		self.m_yWidth = yWidth
		self.m_zWidth = zWidth
		self.m_affine = affine
		self.m_type = 'cube'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('{')
		self.writeAffine(f, self.m_affine)
		f.write('cube(['+ str(self.m_xWidth)+', '  +  str(self.m_yWidth)+', ' + str(self.m_zWidth) +']);')
		f.write('}\n')


	def addXmlDescriptionTo(self, node):
		node.set('xWidth', str(self.m_xWidth))
		node.set('yWidth', str(self.m_yWidth))
		node.set('zWidth', str(self.m_zWidth))
		node.set('affine', self.m_affine.xmlCoords())
		#self.addXmlAffineTo(node, self.m_affine)


####################################################
####################################################


class OSCCombination(OSCAbstract):
	"""
		Allow a combination (like union, difference, intersection, render?) of my children
	"""
	def __init__(self, name, theType):
		super().__init__(name)
		self.m_type = theType


	def writeToFile(self, f, tabNo):
		self.writeName(f, tabNo)
		self.writeTabs(f, tabNo)
		if '(' in self.m_type:
			f.write(self.m_type+'\n')
		else:
			f.write(self.m_type+'()\n')
		self.writeBlockOpen(f, tabNo)
		OSCAbstract.writeToFile(self, f, tabNo)
		self.writeBlockClose(f, tabNo)


	def writeBlockClose(self, f, tabs, writeName=False):
		self.writeTabs(f, tabs)
		f.write('} // end ' + self.m_name + '\n')


	def addXmlDescriptionTo(self, node):
		node.set('type', self.m_type)


#####################################################
#####################################################


class OSCPocketHull(OSCCombination):
	"""
		Currently almost not used. Uses the "hull" feature of oscad for some cylinders located at my polgon
	"""
	def __init__(self, name, polygon, direction, radius, makeSmall=True):
		super().__init__(name, 'hull')
		if makeSmall:
			self.m_polygon = polygon.insetBy(-radius)
		else:
			self.m_polygon = polygon
		self.m_direction = direction
		self.m_radius = radius
		num = 0
		for point in self.m_polygon.m_points:
			num = num + 1
			name = self.m_name + '/cyl' + str(num)
			cyl = OSCCylinder(name, point, direction, direction.length(), radius)
			self.add(cyl)


######################################################
######################################################


class OSCExtrudeLin(OSCAbstract):
	"""
		Extrude linear of my children
	"""
	def __init__(self, name, height):
		super().__init__(name)
		self.m_height = height
		self.m_type = 'extrusion'


	def writeToFile(self, f, tabNo):
		self.writeTabs(f, tabNo)
		f.write('linear_extrude(height='+str(self.m_height)+')\n')
		self.writeBlockOpen(f, tabNo)
		OSCAbstract.writeToFile(self, f, tabNo)
		self.writeBlockClose(f, tabNo, True)


	def addXmlDescriptionTo(self, node):
		node.set('height', str(self.m_height))


######################################################
######################################################


class OSCLongSlot2D(OSCCombination):
	"""
		Currently rarely used, uses "hull"
	"""
	def __init__(self, name, center1, center2, rad):
		super().__init__(name, 'union')
		self.m_type = 'hull'
		self.add(OSCCircle(name+'/circle1', center1, rad))
		self.add(OSCCircle(name+'/circle2', center2, rad))


######################################################
######################################################
#	this can be used for dovetail slots:

class OSCLongSlot3D(OSCCombination):
	"""
		Currently rarely used, uses "hull"
	"""
	def __init__(self, name, center1, center2, direction, depth, rad1, rad2=-1):
		super().__init__(name, 'hull')
		self.m_type = 'hull'
		cyl = OSCCylinder(name+'/circle1', center1, direction, depth, rad1, rad2)
		cyl.enlarge(math.nan, math.nan)
		self.add(cyl)
		cyl2 = OSCCylinder(name+'/circle2', center2, direction, depth, rad1, rad2)
		cyl2.enlarge(math.nan, math.nan)
		self.add(cyl2)


######################################################
######################################################


class OSCPolyhedron(OSCAbstract):
	"""
		Encapsulates a surface that can be represented by a set of faces
	"""

	def __init__(self, name, nonPlanarity=-1, massCenter=None):
		super().__init__(name)
		self.type = 'polyhedron'
		self.m_points = []
		self.m_namesToIndices = dict()
		self.m_faces = []
		self.m_nonPlanarity = nonPlanarity
		self.m_massCenter = massCenter


	def addFace(self, points: list):
		face = []
		if self.m_nonPlanarity >= 0 and len(points) > 3:
			plane = Plane(points[0], points[1], points[2])
			ii = 3
			while ii < len(points):
				point = points[ii]
				dist = plane.distanceOfPoint(point)
				if dist > self.m_nonPlanarity:
					raise Exception('given face does not lie in plane: '+str(dist))
				ii += 1
		for point in points:
			face.append(self.getPointIdx(point))
		self.m_faces.append(face)


	def addFaceWithNames(self, pointNames):
		face = [self.getPointNameIdx(x) for x in pointNames]
		self.m_faces.append(face)


	# get the index of point in the point list
	# if not yet existing, add it
	def getPointIdx(self, point):
		if point in self.m_points:
			return self.m_points.index(point)
		self.m_points.append(point)
		return len(self.m_points) - 1


	def getPointNameIdx(self, pointName):
		# maintain a dictionary of pointNames
		return self.m_namesToIndices.get(pointName)


	def addPointNames(self, pointNamesDict):
		self.m_namesToIndices = dict()
		num = 0
		for name, point in pointNamesDict.items():
			self.m_namesToIndices[name] = num
			self.m_points.append(point)
			num = num + 1


	def writeToFile(self, f, tabNo):
		self.checkAllPolygons()
		self.writeTabs(f, tabNo)
		self.writeTabs(f, tabNo)
		f.write('polyhedron([')
		for point in self.m_points:
			self.writePoint3(f, point)
			f.write(', ')
		f.write('],\n')
		self.writeTabs(f, tabNo+1)
		f.write('[')
		for indexes in self.m_faces:
			f.write('[')
			for index in indexes:
				f.write(str(index))
				f.write(',')
			f.write('],')
		f.write(']);\n')


	def checkAllPolygons(self):
		# check, if every polygon is clockwise (seen from outside)
		massCenter = self.m_massCenter
		if massCenter is None:
			massCenter = Point()
			for point in self.m_points:
				massCenter += point
			factor = 1.0 / len(self.m_points)
			massCenter = massCenter.scaledBy(factor)
			self.m_massCenter = massCenter
		#print(massCenter)
		num = 0
		degen = []
		for face in self.m_faces:
			points = []
			for idx in face:
				points.append(self.m_points[idx])
			poly = Polygon(points)
			
			status = poly.makeClockwise(massCenter)
			if status == 0:
				# was clockwise
				pass
			elif status == 1:
				# must reverse:
				face.reverse() 
			else:
				# degenerate
				print(f'{self.m_name}: face degenerate: {str(num)}')
				degen.append(num)
			num = num +1

		degen.reverse()
		for face in degen:
			self.m_faces.pop(face)


	def addXmlDescriptionTo(self, node):
		#node.set('sense', 'currently unclear')
		Point.xmlAddPointList(node, self.m_points)
		facesNode = ET.SubElement(node, 'faces')
		for face in self.m_faces:
			faceNode = ET.SubElement(facesNode, 'face')
			idxString = ''
			for idx in face:
				idxString += str(idx) + ', '
			faceNode.set('indices', idxString)


##################################################
##################################################

class OSCParallelEpiped(OSCPolyhedron):
	"""
		A polyhedron with 8 parallel faces (12 edges) made up by the 4 points
	"""
	def __init__(self, name, p1, p2, p3, p4):
		super().__init__(name)
		self.m_type = 'parallelepiped'

		offset1 = p2 - p1
		p5 = p3 + offset1
		p6 = p4 + offset1

		offset2 = p4 - p1
		p7 = p3 + offset2
		p8 = p5 + offset2

		# we regard the bottom as 1-3-7-4
		self.addFace([p1, p3, p7, p4])	# bottom
		self.addFace([p2, p6, p8, p5])	# top
		self.addFace([p1, p2, p5, p3])	# 
		self.addFace([p4, p7, p8, p6])	# opposite of last
		self.addFace([p4, p6, p2, p1])	# 
		self.addFace([p3, p5, p8, p7])	# opposite of last


#################################################
#################################################

class OSCHexahedron(OSCPolyhedron):
	"""
		An Hexaeder from the bottom area p1, p2, p3, p4 and according upper area points
		Generalization of a cube
	"""

	def __init__(self, name, p1, p2, p3, p4, p5, p6, p7, p8):
		super().__init__(name)
		self.m_type = 'hexahedron'

		#for p in [p1, p2, p3, p4, p5, p6, p7, p8]:
		#	p.printComment('hex point')

		# we regard the bottom as 1-2-3-4
		self.addFace([p1, p2, p3, p4])	# bottom
		self.addFace([p8, p7, p6, p5])	# top
		self.addFace([p1, p5, p6, p2])	# 
		self.addFace([p3, p7, p8, p4])	# opposite of last
		self.addFace([p2, p6, p7, p3])	# 
		self.addFace([p4, p8, p5, p1])	# opposite of last


#######################################################
#######################################################

class OSCExtrudeRounded(OSCPolyhedron):
	"""
		The extrusion of a path, with rounded edges of given radius
	"""
	def __init__(self, name, path, height, roundRadius):
		super().__init__(name)
		self.m_type = 'ExtrudeRounded'
		self.m_height = height
		self.m_path = path
		self.m_roundRadius = roundRadius
		self.makePolyhedron()


	def makePolyhedron(self):
		delta = 1 / OSCRoot.s_quality
		#print(delta)
		roundingQuality = 4
		pointsAndTangents = self.m_path.getInterPointsWithTangent(delta)
		namesToPoints = dict()
		numOfPoints = len(pointsAndTangents)

		roundingQuality = 5
		if self.m_roundRadius == 0:
			roundingQuality = 1
			
		corners = self.makeRoundingOffsets(self.m_roundRadius, roundingQuality)
		numLines = 1
		self.makeSeveralRoundCornersLines(pointsAndTangents, namesToPoints, corners, numLines)
		numLines = numLines + len(corners)	# the next index

		corners = self.makeRoundingOffsets(self.m_roundRadius, roundingQuality, self.m_height)
		self.makeSeveralRoundCornersLines(pointsAndTangents, namesToPoints, corners, numLines)
		numLines = numLines + len(corners) - 1	# the last index

		self.addPointNames(namesToPoints)

		lowerArea = [(str(x) + '-1') for x in range(numOfPoints)]

		self.addFaceWithNames(lowerArea)
		upperArea = [(str(x) + '-' +str(numLines)) for x in range(numOfPoints)]
		upperArea.reverse()
		self.addFaceWithNames(upperArea)

		for ii in range(numOfPoints - 1):
			self.addFacesWithNames(ii, ii + 1, numLines)
		self.addFacesWithNames(numOfPoints - 1, 0, numLines)


	def makeRoundingOffsets(self, radius, numSteps, height=0):
		# if height is > 0, make it reverse down from height
		circle = Circle2(Point(radius, radius), radius)
		diff = float(radius) / numSteps
		start = 0.0
		ret = []
		while start < (radius - 0.01):
			line = Line(Point(start), Point(start, 1))
			points = circle.intersect(line)
			point = points[0]
			if point.m_y > radius:
				point = points[1]
			ret.append([start, point.m_y])
			start = start + diff
		ret.append([radius, 0])
		#print(ret)
		if height > 0:
			# reverse it and make down from height
			ret.reverse()
			for entry in ret:
				entry[0] = height - entry[0]
		return ret


	def makeSeveralRoundCornersLines(self, pointsAndTangents, namesToPoints, offsets, startLineNo):
		#print(startLineNo)
		for offset in offsets:
			hei = offset[0]
			normal = offset[1]
			self.makeOneRoundCornersLine(pointsAndTangents, namesToPoints, hei, normal, startLineNo)
			startLineNo = startLineNo + 1


	def makeOneRoundCornersLine(self, pointsAndTangents, namesToPoints, height, normalDistance, rowIndex):
		numOfPoints = 0
		#print(str(rowIndex) + '  ' + str(height) + ' ' +str(normalDistance))
		heightOffset = Point(0, 0, height)
		zVector = Point(0, 0, -1)
		for pointAndTangent in pointsAndTangents:
			point = pointAndTangent[0]

			tang = pointAndTangent[1]
			normal = tang.crossProduct(zVector).scaledTo(normalDistance)
			point2 = point + heightOffset + normal	# on the top 
			namesToPoints[str(numOfPoints) + '-' + str(rowIndex)] = point2
			numOfPoints = numOfPoints + 1


	def addFacesWithNames(self, pointNum1, pointNum2, numFaces):
		for ii in range(1, numFaces):
			self.myAddFaceWithNames(pointNum1, pointNum2, ii, ii + 1)


	def myAddFaceWithNames(self, pointNum1, pointNum2, idx1, idx2):
		e1Name = str(pointNum1) + '-' + str(idx2)
		e2Name = str(pointNum2) + '-' + str(idx2)
		e3Name = str(pointNum2) + '-' + str(idx1)
		e4Name = str(pointNum1) + '-' + str(idx1)

		face = [e1Name, e2Name, e3Name, e4Name]
		self.addFaceWithNames(face)


	def addXmlDescriptionTo(self, node):
		node.set('height', str(self.m_height))
		node.set('roundRadius', str(self.m_roundRadius))
		self.m_path.xmlAddTo(node)


#####################################################################


class OSCForm3d(OSCPolyhedron):
	"""
		A (hopefully) closed polyhedron of several surfaces.
		If it is not closed, the user must close it
	"""

	def __init__(self, name, form, massCenter=None):
		super().__init__(name, massCenter=massCenter)
		self.m_form = form
		self.m_type = 'Form3d'
		

	def writeToFile(self, f, tabNo=0):
		self.makePolyhedron()
		super().writeToFile(f, tabNo)


	def makePolyhedron(self):
		quality = OSCRoot.s_quality

		for surface in self.m_form.m_surfaces:
			self.m_massCenter = surface.m_massCenter
			faces = surface.allFaces(quality)
			for face in faces:
				self.addFace(face)


	def addXmlDescriptionTo(self, node):
		node.set('sense', 'currently unclear')


###########################################################
###########################################################


class OSCForm3dLofted(OSCForm3d):
	"""
		A (hopefully) closed polyhedron of a lofted surface and 2 closing surfaces
		taken from the first and last defining curve.
		If it is not closed, the user must close it
	"""
	def __init__(self, name, form, massCenterStart, massCenterStop, massCenter=None):
		super().__init__(name, form, massCenter=massCenter)
		self.m_massCenterStart = massCenterStart
		self.m_massCenterStop = massCenterStop
		self.m_type = 'OSCForm3dLofted'


	def makePolyhedron(self):
		super().makePolyhedron()
		quality = OSCRoot.s_quality
		polygon1, polygon2 = self.m_form.m_surfaces[0].getEdgePolygons(quality)

		self.addClosingPoly(polygon1, self.m_massCenterStart)
		self.addClosingPoly(polygon2, self.m_massCenterStop)


	def addClosingPoly(self, poly, massCenter):
		self.m_massCenter = massCenter
		self.addFace(poly)


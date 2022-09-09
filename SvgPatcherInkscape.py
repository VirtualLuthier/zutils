"""
	Contains only the class with the same name
"""


import math
import re

import xml.etree.ElementTree as ET
from zutils.ZGeom import ZGeomItem, Point, Rect, Line, Circle2
from zutils.SvgPatcher import SvgPatcher
from zutils.ZMatrix import Affine
from zutils.SvgReader import SvgPathReader



class SvgPatcherInkscape(SvgPatcher):
	"""
		Allows to open and change an existing Inkscape svg file
	"""
	def __init__(self, templateFileName, mmOrIn, targetFileName):
		super().__init__(templateFileName, mmOrIn, targetFileName)
		self.registerNamespace('inkscape', 'http://www.inkscape.org/namespaces/inkscape')
		self.registerNamespace('sodipodi', 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd')
		self.registerNamespace('dc', 'http://purl.org/dc/elements/1.1/')
		self.registerNamespace('cc', 'http://creativecommons.org/ns#')
		self.registerNamespace('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
		self.m_symmetryId = None

		# we do this only after registering all our own namespaces:
		self.readTemplateFile()
		self.setAttribute(self.m_root, 'sodipodi:docname', targetFileName)


	def addGuide(self, name, offset, verticalFlag):
		# verticalFlag may also be Line!
		# in this case offset is ignored
		# if verticalFlag == True (vertical line):
		#	offset is offset from left page edge
		# if verticalFlag == False (horizontal line):
		#	offset is offset from bottom page edge
		#self.enumerateTags(self.m_root)
		parent = self.m_root.find('sodipodi:namedview', namespaces=self.m_namespaces)
		guide = ET.SubElement(parent, 'sodipodi:guide')
		
		textOffset = ZGeomItem.transformMMs(-50)
		if isinstance(verticalFlag, bool):
			offset = round(offset, 4)
			if verticalFlag:
				x = offset
				y = textOffset
				orient = '-1,0'
			else:
				x = textOffset
				y = self.m_height - offset
				orient = '0,1'
		else:
			# 'verticalFlag' is in reality a Line
			namePoint, angle = self.getGuideDetailsForLine(verticalFlag)
			if namePoint is None:
				print('SvgPatcherInkscape: cannot show oblique line')
				return
			x = namePoint.m_x
			# the sodipodi origin seems to be in another corner !!!:
			y = self.m_height - namePoint.m_y
			radians = math.radians(angle)
			sin = round(math.sin(radians), 7)
			cos = round(math.cos(radians), 7)
			orient = str(sin) + ',' + str(cos)

		guide.set('position', str(x) + ',' + str(y))
		guide.set('orientation', orient)
		guide.set('inkscape:label', name)
		guide.set('inkscape:locked', 'true')


	def removeAllGuideLines(self):
		parent = self.m_root.find('sodipodi:namedview', namespaces=self.m_namespaces)
		toRemove = []
		for c in parent:
			if c.tag == '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}guide':
				toRemove.append(c)
		for c in toRemove:
			parent.remove(c)


	def removeTheseGuideLines(self, nameList):
		parent = self.m_root.find('sodipodi:namedview', namespaces=self.m_namespaces)
		toRemove = []
		for c in parent:
			if c.tag == '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}guide':
				if c.get('{http://www.inkscape.org/namespaces/inkscape}label', None) in nameList:
					toRemove.append(c)
		for c in toRemove:
			parent.remove(c)


	def getGuideDetailsForLine(self, line):
		"""
			Return the comment point and the angle for the guide
			only used for a guide line that is not axis parallel
		"""
		
		edges = [Point(), Point(self.m_width), Point(0, self.m_height), Point(self.m_width, self.m_height), ]
		idx = 0
		#interPoints = []
		#interIdxs = []
		for edge in [(edges[0], edges[2]), (edges[2], edges[3]),(edges[0], edges[1]),(edges[3], edges[1])]:
			first = edge[0]
			second = edge[1]
			edgeLine = Line(first, second)
			inter = edgeLine.intersectLine(line)
			if inter is not None:
				if edgeLine.liesInside(inter):
					#interPoints.append(inter)
					#interIdxs.append(idx)
					break
			idx += 1
		if inter is None:
			return [None, None]

		direction = line.m_direction
		offsetSmall = direction.scaledTo(ZGeomItem.transformMMs(1))
		offset = direction.scaledTo(ZGeomItem.transformMMs(50))
		rect = Rect(Point(), Point(self.m_width, self.m_height))
		namePoint = inter + offsetSmall
		if rect.containsPoint(namePoint):
			namePoint = inter - offset
		else:
			namePoint = inter + offset
		#namePoint.printComment('namePoint')
		angle = Affine.fullAngleBetween2d(Point(1), direction)
		return [namePoint, angle]


	def prepareSymmetry(self, mX=math.nan):
		#self.enumerateTags(self.m_root)
		defs = self.m_root.find('svg:defs', namespaces=self.m_namespaces)
		pathEffect = defs.find('inkscape:path-effect', namespaces=self.m_namespaces)
		if math.isnan(mX):
			w = self.m_width
			useDefault = True
		else:
			w = 2.0 * mX
			useDefault = False
		right = str(w/2.0) + ','
		h = self.m_height
		pathEffect.set('start_point', right + '0')
		pathEffect.set('end_point', right + str(h))
		pathEffect.set('center_point', right + str(h/2.0))
		if not useDefault:
			pathEffect.set('mode', 'free')
		self.m_symmetryId = pathEffect.get('id')


	def setSymmetricalPath(self, p, d, style):
		p.set('style', style)
		p.set('d', '')
		self.setAttribute(p, 'inkscape:path-effect', '#' + self.m_symmetryId)
		self.setAttribute(p, 'inkscape:original-d', d)


	def addPathGroup(self, pathCode, style, symmetric=False, parent=None, theId=None):
		g = self.startGroup(parent, theId)
		p = self.startPath(g)
		d = pathCode

		if symmetric:
			self.setSymmetricalPath(p, d, 'fill:none;stroke:Black;stroke-width:1;')
		else:
			#self.standardSvgStroke(p)
			p.set('style', 'fill:none;stroke:Black;stroke-width:1.0;')
			p.set('d', d)


	def addLayer(self, name):
		"""
			return a group that is usable as an inkscape layer
		"""
		layer = self.startGroup()
		self.setAttribute(layer, 'inkscape:label', name)
		self.setAttribute(layer, 'inkscape:groupmode', 'layer')
		self.setAttribute(layer, 'id', self.makeIdFromString(name))
		return layer


	def transformEveryNode(self, aff, factor, startNode=None):
		if startNode is None:
			startNode = self.m_root
		if startNode.tag == '{http://www.w3.org/2000/svg}path':
			#print('found path')
			self.setTransformedPath(startNode, aff, '{http://www.inkscape.org/namespaces/inkscape}original-d')
			self.setTransformedPath(startNode, aff, 'd')
			self.changeStrokeWidth(startNode, factor)
		elif startNode.tag == '{http://www.w3.org/2000/svg}circle':
			#print('found circle')
			cx = float(startNode.get('cx'))
			cy = float(startNode.get('cy'))
			r = float(startNode.get('r'))
			circle = Circle2(Point(cx, cy), r)
			#circle.printComment('before')
			circle2 = aff * circle
			#circle2.printComment('after ')
			startNode.set('cx', str(round(circle2.m_center.m_x, 4)))
			startNode.set('cy', str(round(circle2.m_center.m_y, 4)))
			startNode.set('r', str(round(circle2.m_radius, 4)))
			self.changeStrokeWidth(startNode, factor)
		elif startNode.tag == '{http://www.w3.org/2000/svg}ellipse':
			print('found ellipse - currently unhandled')
		else:
			for subNode in startNode:
				self.transformEveryNode(aff, factor, startNode=subNode)


	def setTransformedPath(self, node, aff, dName):
		d = node.get(dName)
		if d is None or d == '':
			return
		#print('d = ' + d)
		path = SvgPathReader.classParsePath(d, smartCircles=False)
		#path.printComment('original')
		path.transformBy(aff)
		#path.printComment('transformed')
		dNew = path.svgCode()
		node.set(dName, dNew)


	@classmethod
	def changeStrokeWidth(cls, node, factor):
		strokeAtt = node.get('stroke-width')
		if strokeAtt is not None:
			newAtt = cls.scaleNumberInString(strokeAtt, factor)
			if newAtt is not None:
				node.set('stroke-width', newAtt)
				return

		styleAtt = node.get('style')
		if styleAtt is None:
			return
		strokeMatch = re.search(r'stroke-width:[\d\.]+', styleAtt)
		if strokeMatch is None:
			return
		strokePart = strokeMatch.group(0)
		newStrokePart = cls.scaleNumberInString(strokePart, factor)
		if newStrokePart is not None:
			newStyleAtt = styleAtt.replace(strokePart, newStrokePart)
			node.set('style', newStyleAtt)


	@classmethod
	def scaleNumberInString(cls, string, factor):
		"""
			Find a number in a string, scale it by factor and return the changed string - thanks to Inkscape!
		"""
		num = re.search(r'-?\d+(\.\d+)?', string)
		if num is None:
			return None
		found = num.group(0)
		fl = float(found)
		fl *= factor
		fl = round(fl, 5)
		ret = string.replace(found, str(fl))
		return ret





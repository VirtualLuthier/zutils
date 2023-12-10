"""
	Contains the classes:
	- SvgWriter (create and populate an svg file)
	- SvgPatcher (read an svg file and modify it)
"""

import os
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

from zutils.ZGeom import Point


class SvgWriter:
	'''
		Create an svg file and add elements like 
		- path
		- rect
		- circle
		- ellipse
		- text
		Also write the file afterwards
	'''
	def __init__(self, mmOrIn, createRoot=True, useNamespaces=True, targetFile=None):
		'''
				Create a node with the needed svg namespace settings and the viewport
		'''
		self.m_unit = mmOrIn
		self.m_useNamespaces = useNamespaces

		self.m_namespaces = {}
		if self.m_useNamespaces:
			self.registerNamespace('', 'http://www.w3.org/2000/svg')
			self.registerNamespace('svg', 'http://www.w3.org/2000/svg')
			self.m_namespacePrefix = 'svg:'
		else:
			self.m_namespacePrefix = ''

		self.m_tree = None
		self.m_root = None
		self.m_width = math.nan
		self.m_height = math.nan

		self.m_targetFile = targetFile

		if createRoot:
			root = ET.Element('svg')
			root.set('version', '1.1')
	#		ret.set('id', 'Layer_1')
			root.set('xmlns', 'http://www.w3.org/2000/svg')
			root.set('xmlns:svg', 'http://www.w3.org/2000/svg')
			root.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
			self.m_root = root


	def registerNamespace(self, name, url):
		ET.register_namespace(name, url)
		self.m_namespaces[name] = url


	def enumerateTags(self, node):
		for child in node:
			print(child.tag)


	def enumerateAttributes(self, node):
		for att in node.attrib:
			print(att)


	def setAttribute(self, node, name, value):
		'''
			its a shame, this should not be needed
			registering namespaces seems to be useless for attributes
			for inkscape:label use {http://www.inkscape.org/namespaces/inkscape}:label
		'''
		parts = name.split(':')
		if len(parts) > 1:
			space = self.m_namespaces[parts[0]]
			replacement = '{'+space+'}'
			node.set(replacement + parts[1], value)
			return
		node.set(name, value)


	def setSize(self, width, height, left=0, top=0, addFactor=0):
		'''
			Set the viewbox. Virtually use 1.0 dpi (or 1.0 dpmm). If addFactor > 0: add a margin
		'''
		root = self.m_root
		if addFactor > 0:
			widthUsed = width*(1 + 2*addFactor)
			heightUsed = height*(1 + 2*addFactor)
			leftUsed = left - addFactor*width
			topUsed = top - addFactor*width
		else:
			widthUsed = width
			heightUsed = height
			leftUsed = left
			topUsed = top
		root.set('width', f'{widthUsed}{self.m_unit}')
		root.set('height', f'{heightUsed}{self.m_unit}')
		root.set('viewBox', f'{leftUsed} {topUsed} {widthUsed} {heightUsed}')
		self.m_left = leftUsed
		self.m_top = topUsed
		self.m_width = widthUsed
		self.m_height = heightUsed


	def write(self, targetFile=None):
		#self.m_tree.write('svg/raw.svg', "utf-8") # used for debugging
		if targetFile is not None:
			self.m_targetFile = targetFile
		pretty = self.svgString(True)
		with open(self.m_targetFile, 'w') as f:
			f.write(pretty)


	def svgString(self, prettify=False):
		theString = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(self.m_root, 'unicode')
		if not prettify:
			return theString
		return self.prettifiedSvgString(theString)


	def prettifiedSvgString(self, roughString):
		reparsed = minidom.parseString(roughString)
		bString = reparsed.toprettyxml(indent="	", newl='\n', encoding='utf-8')
		return str(bString, 'utf-8')


	def startGroup(self, parent=None, name=None):
		if parent is None:
			parent = self.m_root
		group = ET.SubElement(parent, 'svg:g')
		if name is not None:
			group.set('id', name)
		return group


	@classmethod
	def makeIdFromString(cls, theString):
		'''
			Make a string that is usable as an id
		'''
		ret = ''
		start = theString[0]
		if not start.isalpha():
			ret = 'ID'
		for theChr in theString:
			if not theChr.isalpha and not theChr.isdigit():
				ret += '_'
			else:
				ret += theChr
		return ret
	

	def getSizeFrom(self, node, attName):
		'''
			get a float number from the attribute value with the given name of this node. Else return math.nan
		'''
		val = node.get(attName)
		if val is None:
			return math.nan
		numberPart = re.findall(r'[\d\.]+', val)
		if len(numberPart) == 0:
			return math.nan
		return float(numberPart[0])
	

	def getNiceParent(self, parent):
		'''
			if parent is none, use my root node, else use the parent
		'''
		if parent is not None:
			return parent
		return self.m_root
	

	def addPath(self, parent, pathObject, strokeWidth=1, stroke='black', fill='none'):
		'''
			create an svg path
		'''
		path = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'path')
		path.set('stroke', stroke)
		path.set('stroke-width', str(strokeWidth))
		path.set('fill', fill)
		path.set('d', pathObject.svgCode())
		return path


	def addCircle(self, parent, circleObject, strokeWidth=1, stroke='black', fill='none'):
		'''
			crate an svg circle node (not a path arc)
		'''
		circle = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'circle')
		circle.set('cx', str(circleObject.m_center.m_x))
		circle.set('cy', str(circleObject.m_center.m_y))
		circle.set('r', str(circleObject.m_radius))
		circle.set('stroke', stroke)
		circle.set('stroke-width', str(strokeWidth))
		circle.set('fill', fill)
		return circle
	

	def addEllipse(self, parent, ellipseObject, xAngle, strokeWidth=1, stroke='black', fill='none'):
		'''
			create an svg ellipse node (not a path arc)
		'''
		ellipse = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'ellipse')
		cx = ellipseObject.m_center.m_x
		cy = ellipseObject.m_center.m_y
		ellipse.set('cx', str(cx))
		ellipse.set('cy', str(cy))
		ellipse.set('rx', str(ellipseObject.m_diam1.length()))
		ellipse.set('ry', str(ellipseObject.m_diam2.length()))
		ellipse.set('stroke', stroke)
		ellipse.set('stroke-width', str(strokeWidth))
		ellipse.set('fill', fill)
		if xAngle > 0:
			ellipse.set('transform', f'rotate({xAngle}, {cx}, {cy})')	
		return ellipse


	def addLine(self, parent, p1, p2, strokeWidth=1, strokeColor='black'):
		'''
			create an svg line node from the 2 given points
		'''
		line = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'line')
		line.set('x1', str(p1.m_x))
		line.set('y1', str(p1.m_y))
		line.set('x2', str(p2.m_x))
		line.set('y2', str(p2.m_y))
		line.set('stroke', strokeColor)
		line.set('stroke-width', str(strokeWidth))
		return line


	def addRect(self, parent, left, top, width, height, strokeWidth=1, stroke='black', fill='none'):
		'''
			crate an svg rect node
		'''
		rect = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'rect')
		rect.set('x', str(left))
		rect.set('y', str(top))
		rect.set('width', str(width))
		rect.set('height', str(height))
		rect.set('stroke', stroke)
		rect.set('stroke-width', str(strokeWidth))
		rect.set('fill', fill)
		return rect
	

	def addText(self, parent, msg, pos, offset=Point(), font=None, fontSize=None, fill='black'):
		'''
			create an svg text node
		'''
		text = ET.SubElement(self.getNiceParent(parent), self.m_namespacePrefix + 'text')
		text.text = msg
		text.set('x', str(pos.m_x+offset.m_x))
		text.set('y', str(pos.m_y+offset.m_y))
		text.set('fill', fill)
		if font is not None:
			text.set('font', font)
		if fontSize is not None:
			text.set('font-size', str(fontSize))



##########################################################
##########################################################


class SvgPatcher(SvgWriter):
	"""
		Allows to open and change an existing svg file
	"""
	def __init__(self, templateFileName, mmOrIn, targetFileName):
		"""
		
		"""
		super().__init__(mmOrIn, False)
		self.m_templateName = self.getFullTemplateFilePath(templateFileName)
		self.m_targetFile = targetFileName
		

	@classmethod
	def getFullTemplateFilePath(cls, templateRelativeName):
		if templateRelativeName.find('/') >= 0 or templateRelativeName.find('\\') >= 0:
			# if name is absolute, return name
			return templateRelativeName
		ownFolder = os.path.dirname(os.path.abspath(__file__))
		return ownFolder + '/templateFiles/' + templateRelativeName


	def readTemplateFile(self):
		tree = ET.parse(self.m_templateName)
		self.m_tree = tree
		self.m_root = tree.getroot()
		self.m_width = self.getSizeFrom(self.m_root, 'width')
		self.m_height = self.getSizeFrom(self.m_root, 'height')


"""
	Contains only the class with the same name
"""

import os
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re


class SvgPatcher:
	"""
		Allows to open and change an existing svg file
	"""
	def __init__(self, templateFileName, mmOrIn, targetFileName):
		"""
		
		"""
		self.m_templateName = self.getFullTemplateFilePath(templateFileName)
		self.m_targetFile = targetFileName
		self.m_unit = mmOrIn
		self.m_namespaces = {}
		#self.m_namespaces = {'svg': 'http://www.w3.org/2000/svg'}
		self.registerNamespace('', 'http://www.w3.org/2000/svg')
		self.registerNamespace('svg', 'http://www.w3.org/2000/svg')
		self.m_tree = None
		self.m_root = None
		self.m_width = math.nan
		self.m_height = math.nan


	@classmethod
	def getFullTemplateFilePath(cls, templateRelativeName):
		if templateRelativeName.find('/') >= 0 or templateRelativeName.find('\\') >= 0:
			# if name is absolute, return name
			return templateRelativeName
		ownFolder = os.path.dirname(os.path.abspath(__file__))
		return ownFolder + '/templateFiles/' + templateRelativeName


	@classmethod
	def makeIdFromString(cls, theString):
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


	def readTemplateFile(self):
		tree = ET.parse(self.m_templateName)
		self.m_tree = tree
		self.m_root = tree.getroot()
		self.m_width = self.getSizeFrom(self.m_root, 'width')
		self.m_height = self.getSizeFrom(self.m_root, 'height')


	def getSizeFrom(self, node, attName):
		val = node.get(attName)
		if val is None:
			return math.nan
		numberPart = re.findall(r'[\d\.]+', val)
		if len(numberPart) == 0:
			return math.nan
		return float(numberPart[0])


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
		# its a shame, this should not be needed
		# registering namespaces seems to be useless for attributes
		# for inkscape:label use {http://www.inkscape.org/namespaces/inkscape}:label
		parts = name.split(':')
		if len(parts) > 1:
			space = self.m_namespaces[parts[0]]
			replacement = '{'+space+'}'
			node.set(replacement + parts[1], value)
			return
		node.set(name, value)


	def setSize(self, width, height):
		w = width		# perhaps should be rounded?
		h = height		# perhaps should be rounded?
		self.m_width = w
		self.m_height = h
		root = self.m_root
		root.set('width', str(w) + self.m_unit)
		root.set('height', str(h) + self.m_unit)
		root.set('viewBox', '0 0 ' + str(width) + ' ' + str(height))


	def write(self):
		#self.m_tree.write('svg/raw.svg', "utf-8") # used for debugging
		pretty = self.prettify(self.m_root)
		with open(self.m_targetFile, 'w') as f:
			f.write(pretty)


	def prettify(self, elem):
    	#	Return a pretty-printed XML string for the Element.
		rough_string = ET.tostring(elem, 'utf-8')
		#print(rough_string)
		reparsed = minidom.parseString(rough_string)
		return reparsed.toprettyxml(indent="	", newl='\n')
		#return reparsed.toprettyxml(indent="  ")


	def startGroup(self, parent=None, name=None):
		if parent is None:
			parent = self.m_root
		group = ET.SubElement(parent, 'svg:g')
		if name is not None:
			group.set('id', name)
		return group


	def startPath(self, parent):
		path = ET.SubElement(parent, 'svg:path')
		return path


	def addCircle(self, parent, circle, strokeWidth=1):
		c = ET.SubElement(parent, 'svg:circle')
		c.set('cx', str(circle.m_center.m_x))
		c.set('cy', str(circle.m_center.m_y))
		c.set('r', str(circle.m_radius))
		c.set('stroke', 'black')
		c.set('stroke-width', str(strokeWidth))
		c.set('fill', 'none')




	
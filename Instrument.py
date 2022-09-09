"""
	Contains only the class with the same name
"""

import os
#import traceback
import xml.etree.ElementTree as ET
from xml.dom import minidom
from zutils.ZUnits import ZUnits
from zutils.ZGeom import ZGeomItem, Point, Plane
from zutils.ZMatrix import Affine
from zutils.OSCNode import OSCTransform, OSCRoot

from zutils.ZRhino3dm import ZRhinoFile

# the "unused" classes are needed to be in globals!!!
from  zutils.ZWidgetDescriptors import (
		WidgetDescCheckBox, WidgetDescDoubleLineInput, WidgetDescTextLine, WidgetDescTextArea, WidgetDescComboBox, # pylint: disable=unused-import
		WidgetDescIntLineInput	# pylint: disable=unused-import
)


class Instrument():
	"""
		Superclass for musical instruments. Handles composition of parts, editing, error checking, and updating
	"""
	s_catchExceptions = False		# if False, crash, else just emit an error message and continue

	def __init__(self, metric=True, concertPitch=440, leftHanded=False, folder='', title='', text=''):
		super().__init__()
		self.m_parts = []
		self.m_names = dict()
		if folder is None:
			folder = ''
		folder = folder.replace('\\', '/')
		if len(folder) > 0 and folder[-1] != '/':
			folder += '/'
		self.m_folder = folder
		self.m_leftHanded = leftHanded
		if not metric:
			ZUnits.s_isMetric = False
			ZGeomItem.s_isMetric = False
		self.m_isMetric = metric
		self.m_concertPitch = concertPitch
		self.m_title = title
		self.m_text = text


	def refresh(self):
		for part in self.m_parts:
			part.m_folder = self.m_folder
			part.refresh()


	def addPart(self, compo, name):
		if compo is not None:
			self.m_parts.append(compo)
			self.m_names[compo] = name
			compo.m_folder = self.m_folder
		self.__dict__['m_' + name] = compo


	def calculateAll(self) -> bool:
		"""
			Try to calculate all parts of me. Return True for success or False
		"""
		
		folder = self.m_folder
		if folder is None or folder == '':
			raise Exception('Instrument: No folder given ----------------------')
			#return False
		else:
			if not os.path.isdir(folder):
				try:
					os.makedirs(folder)
				except Exception as err:
					print(f'Illegal folder: {str(folder)}')
					print(f'cause: {str(err)}')
					return False

		self.refresh()
		
		currentPart = None
		theParts = self.partsInOrderToUpdate()
				
		for part in theParts:
			currentPart = part
			try:
				part.updateFromInstrument(self)
			except Exception as e:
				#traceback.print_stack()
				print(f'Exception doing updateFromInstrument(): {str(e)}')
				print(f'currentPart = {currentPart.__class__.__name__}')
				if self.s_catchExceptions:
					return False
				raise

		for part in theParts:
			currentPart = part
			try:
				part.calculateAll()
			except Exception as e:
				#traceback.print_stack()
				print(f'Exception doing updateFromInstrument(): {str(e)}')
				print(f'currentPart = {currentPart.__class__.__name__}')
				if self.s_catchExceptions:
					return False
				raise
		
		return True


	def writeOSC(self, fileName, wantedPart=None):
		self.calculateAll()
		root = OSCRoot('rootNode')
		rootMirror = root
		
		#render = OSCCombination('the rendered part, seems no longer neccessary', '//render')
		#root.add(render)
		if self.m_leftHanded:
			yzPlane = Plane(Point(), normal=Point(1))
			aff = Affine.makeMirror(yzPlane)
			rootMirror = OSCTransform('left handed mirror', aff)
			root.add(rootMirror)
			render = rootMirror
		parts = self.m_parts
		if wantedPart:
			parts = [wantedPart]
		for part in parts:
			part.addOscColor(root)
			affine = part.createAffLocalToGlobal(self)
			name = self.m_names[part]
			transform = OSCTransform('part named ' + name + ':', affine)
			root.add(transform)
			part.writeMyOSC(root, transform)
		root.writeScadTo(fileName)

		#root.printStructure()


	#def writeOneComponent(self, compo, affine, name, root, parent):
	#	trCompo = OSCTransform('subtree of ' + name + ':', affine)
	#	parent.add(trCompo)
	#	compo.writeMyOSC(root, trCompo)


	
	def writeRhino(self, fileName, wantedPart=None):
		self.calculateAll()
		#root = OSCRoot('rootNode')
		#rootMirror = root
		unit = 'inch' if ZGeomItem.s_inchWanted else 'mm'
		rhinoFile = ZRhinoFile.newFile(fileName, unit)
		
		if self.m_leftHanded:
			yzPlane = Plane(Point(), normal=Point(1))
			aff = Affine.makeMirror(yzPlane)
			ZRhinoFile.affinePush(aff)

		parts = self.m_parts
		if wantedPart:
			parts = [wantedPart]
		for part in parts:
			affine = part.createAffLocalToGlobal(self)
			#name = self.m_names[part]
			ZRhinoFile.affinePush(affine)
			part.writeMyRhino(rhinoFile)
			ZRhinoFile.affinePop()

		rhinoFile.write()


	def allWidgetDescs(self):
		ret = []
		ret.append(WidgetDescTextLine(self, 'Instrument.Title', 'm_title'))
		ret.append(WidgetDescTextLine(self, 'Instrument.Folder', 'm_folder'))
		ret.append(WidgetDescCheckBox(self, 'Instrument.IsMetric', 'm_isMetric', dimmed=True))
		ret.append(WidgetDescDoubleLineInput(self, 'Instrument.ConcertPitch', 'm_concertPitch', 400, 500, 2))
		ret.append(WidgetDescCheckBox(self, 'Instrument.IsLeftHanded', 'm_leftHanded'))
		ret.append(WidgetDescTextArea(self, 'Instrument.Comment', 'm_text'))

		return ret


	def checkInto(self, handler):
		freq = self.m_concertPitch
		if freq < 380 or freq > 460:
			handler.addError(self, 'Instrument.Error.WrongConcertPitch', 'm_concertPitch')
		folder = self.m_folder
		if folder is None or folder == '':
			handler.addError(self, 'Instrument.Error.FolderNotGiven', 'm_folder')
			return
		else:
			if not os.path.isdir(folder):
				handler.addError(self, 'Instrument.Error.FolderNotFound', 'm_folder')
				return
			if not os.access(folder, os.W_OK | os.X_OK):
				print(f'folder not writable: {folder}')
				handler.addError(self, 'Instrument.Error.FolderNotWritable', 'm_folder')
				return

		for part in self.m_parts:
			part.checkInto(handler)


	def makeArgsDict(self):
		"""
			Return a dict that can be used for the Instrument() constructor.
			It can reconstruct the current guitar, but single entries can be overwritten.
			They can not simply be replaced, because the constructor must be run.
		"""
		args = dict()
		args['folder'] = self.m_folder
		args['isMetric'] = self.m_isMetric
		args['concertPitch'] = self.m_concertPitch
		args['title'] = self.m_title
		args['text'] = self.m_text

		return args


	def xmlWrite(self, fileName):
		rootNode = ET.Element('Instrument')
		instNode = ET.SubElement(rootNode, self.__class__.__name__)
		self.xmlAddAllWidgetDescriptionsOf(instNode, self)

		partsNode = ET.SubElement(instNode, 'Parts')
		for part in self.m_parts:
			partNode = ET.SubElement(partsNode, part.__class__.__name__)
			self.xmlAddAllWidgetDescriptionsOf(partNode, part)
		
		rough_string = ET.tostring(rootNode, 'utf-8')

		reparsed = minidom.parseString(rough_string)
		nice = reparsed.toprettyxml(indent="	", newl='\n')
		with open(fileName, "w", encoding='utf-8') as f:
			f.write(nice)


	@classmethod
	def xmlAddAllWidgetDescriptionsOf(cls, parentNode, owner):
		wNode = ET.SubElement(parentNode, 'Widgets')
		for w in owner.allWidgetDescs():
			#w.m_owner = owner
			w.xmlUnder(wNode)


	@classmethod
	def xmlGetAllChildren(cls, node):
		ret = []
		for child in node:
			ret.append(child)
		return ret


	@classmethod
	def xmlReadFromFile(cls, fName, classFactory):
		tree = ET.parse(fName)
		root = tree.getroot()

		if root.tag != 'Instrument':
			return [None, 'Instrument.Error.XML.NoValidFile']
		instrumentNodes = cls.xmlGetAllChildren(root)
		if len(instrumentNodes) != 1:
			return [None, 'Instrument.Error.XML.NoValidFile']
		instrumentNode = instrumentNodes[0]
		instrumentClassName = instrumentNode.tag
		instrumentClass = classFactory.getClassFromName(instrumentClassName)

		instrumentWidgets = cls.xmlReadWidgetsUnder(instrumentNode)
		fullDict = {} # dict()
		for w in instrumentWidgets:
			fullDict[w.m_varName[2:]] = w.valueFromString(instrumentWidgets[w])

		partsNode = cls.xmlFindFirstChild(instrumentNode, 'Parts')
		if partsNode is not None:
			for p in partsNode:
				part = cls.xmlReadPart(p, classFactory)
				instrumentClass.storePartInDict(part, fullDict)

		ret = instrumentClass(**fullDict)
		return ret


	@classmethod
	def xmlReadPart(cls, node, classFactory):
		className = node.tag
		theClass =classFactory.getClassFromName(className)
		thePart = theClass()
		widgetsDict = cls.xmlReadWidgetsUnder(node)
		for w in widgetsDict:
			w.m_owner = thePart
			w.setOwnerVal(w.valueFromString(widgetsDict[w]))

		return thePart


	@classmethod
	def xmlReadWidgetsUnder(cls, parentNode):
		"""
			read widgets under a given xml node
		"""
		ret = dict()
		widgetsMainNode = cls.xmlFindFirstChild(parentNode, 'Widgets')
		if widgetsMainNode is None:
			return ret

		for w in widgetsMainNode:
			className = w.tag
			varName = w.get('instVar')
			value = w.get('value')
			if varName == 'm_isMetric':
				# we must set this as early as possible, so the respective constructors can work correctly
				inchesFlag = (value == 'False')
				ZGeomItem.adaptForInches(inchesFlag)

			theClass = globals()[className]
			widgetDesc = theClass(None, None, varName)
			ret[widgetDesc] = value

		return ret



	@classmethod
	def xmlFindFirstChild(cls, parent, tag):
		for c in parent:
			if c.tag == tag:
				return c
		
		return None

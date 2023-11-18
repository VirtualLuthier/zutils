"""
	Contains only the class with the same name
"""


import os.path
import math
from typing import List
import logging

from zutils.GMaterial import GMaterial
from zutils.ZGeom import Point, Plane, Line, Circle2, ZGeomItem
from zutils.OSCNode import OSCAbstract, OSCRoot, OSCCombination, OSCTransform, OSCExtrudeLin, OSCPath, OSCCallModule
from zutils.ZMatrix import Matrix, Affine
from zutils.SvgReader import SvgPathReader
from zutils.ZUnits import ZUnits
from zutils.SvgPatcherInkscape import SvgPatcherInkscape

from zutils.ZRhino3dm import ZRhinoFile

from zutils.ZWidgetDescriptors import WidgetDescDoubleLineInput, WidgetDescIntLineInput, WidgetDescTextLine, WidgetDescCheckBox, WidgetDescSpacer, WidgetDescComboBox

class InstrumentPart():
	"""
		Is the common superclass of all instrument parts. Implements things like Inkscape sketch handling, editing, storing, error checking
	"""
	def __init__(self):
		self.m_isSymmetric = False
		self.m_uid = None

		# is set by the instrument:
		self.m_modelFolder = '.'

		# is calculated later:
		# just to define the variables
		if self.needsAnSvgFile():
			self.m_svgFile = self.__class__.__name__ + '.svg'

		self.m_folder = None		# set by instrument
		self.m_svgPath = None
		self.m_circles = None
		self.m_protocol = ''
		self.m_affLocalToGlobal = None
		self.m_affGlobalToLocal = None

		self.m_material = 'InstrumentPart.Materials.Maple'
		self.m_rhinoFile = None

		self.refresh()


	def refresh(self):
		self.m_svgPath = None
		self.m_circles = None
		self.m_protocol = ''
		self.m_affLocalToGlobal = None
		self.m_affGlobalToLocal = None


	def mustBeSymmetric(self):
		return False


	def getAffGlobalToLocal(self):
		if not self.m_affGlobalToLocal:
			self.m_affGlobalToLocal = self.m_affLocalToGlobal.inverted()
		return self.m_affGlobalToLocal


	def getFullSvgFilePath(self):
		if not self.needsAnSvgFile():
			return None
		ret = self.m_folder + self.m_svgFile
		ret = ret.replace('/', os.sep)
		ret = ret.replace('\\', os.sep)
		return ret


	def getAffSvgToLogical(self):
		"""
			Return an Affine, that maps my svg coordinates to the logical ones
			Eg map Point(extX/2, extY) (svg coords of bottom center) to Point(0, 0) in logical coords
			Ie in logical coords the bottom center is (0, 0)
		"""
		ext = self.getSvgDefaultExtent()
		affShift = Affine(None, Point(-ext.m_x / 2.0, -ext.m_y))
		plane = Plane(Point(), normal=Point(0, 1))
		affMirror = Affine.makeMirror(plane)
		aff = affMirror * affShift
		return aff


	def getAffLogicalToSvg(self):
		return self.getAffSvgToLogical().inverted()


	@classmethod
	def getSmallLength(cls):
		return ZUnits.changeMmToMmOrInch(1)


	@classmethod
	def getLengthFromMm(cls, mms):
		return ZUnits.changeMmToMmOrInch(mms)


	def getUidString(self):
		if self.m_uid:
			return self.m_uid
		return self.__class__.__name__
		

	def createPlate3D(self, parent, height, path=None, qualityFactor=math.nan):
		extrude = OSCExtrudeLin('extrude', height)
		parent.add(extrude)
		if path is None:
			path = self.m_svgPath
		oscPath = OSCPath('extrude-path', path, qualityFactor)
		extrude.add(oscPath)
		return extrude
		

	def protocol(self, msg):
		self.m_protocol += self.getUidString()  + msg + '\n'
		print(f'{self.getUidString()}: {msg}')


	def getPathDAttributeName(self):
		# when we read an inkscape svg file with a mirrored path
		if self.m_isSymmetric:
			return '{http://www.inkscape.org/namespaces/inkscape}original-d'
		else:
			return 'd'


	def readSvg(self):
		if self.m_svgFile is None or self.m_svgFile == '' or not self.needsAnSvgFile():		
			return
		_, fileExtension = os.path.splitext(self.m_svgFile)
		if fileExtension != '.svg':
			return
		fullsvgFileName = self.getFullSvgFilePath()		
		#self.useIncscapeMirroring(self.m_isSymmetric)
		if not os.path.exists(fullsvgFileName):
			self.createSvgDefaultFile()
		xmlReader = SvgPathReader()
		xmlReader.setDAttributeName(self.getPathDAttributeName())
		pathsIn = xmlReader.readFile(fullsvgFileName)
		
		if len(pathsIn) == 0:
			print(f'empty/unreadable file: {self.getFullSvgFilePath()}')
			return False

		affSvgToLogical = self.getAffSvgToLogical()
		circles = xmlReader.m_circles
		self.m_circles = [affSvgToLogical * x for x in circles]

		for path in pathsIn:
			path.transformBy(affSvgToLogical)
			self.acceptSvgPath(path)


	def acceptSvgPath(self, path):
		"""
			MAy be overridden by subclasses
		"""
		self.mirrorPathIfWanted(path)
		self.m_svgPath = path


	def mirrorPathIfWanted(self, path):
		"""
			work in progress
		"""
		if not path.areSegsConnected():
			path.printComment('areSegsConnected = False')
			logging.error('areSegsConnected = False')
			raise Exception('areSegsConnected = False -------------------')
		#print('path named: ' + str(path.m_groupId))
		#path.printComment('vorher')
		#print('debug me')
		mirrorNeeded = False
		if self.m_isSymmetric and not path.isClosed():
			stop = path.getSmartStop()

			if stop.m_x != 0:
				# we must somehow make a path that is able to mirror
				lastSeg = path.m_segments[-1]
				lastSeg.m_stop.m_x = 0
			mirrorNeeded = True

		if mirrorNeeded:
			plane = Plane.alongAxes('y', 'z')
			path.supplementByMirror(plane)
		path.closeByLine()
		
		if not path.isClosed():
			path.printComment('is not closed')
			logging.error('path is not closed')
			raise Exception('path is not closed')


	def createSvgDefaultFile(self):
		"""
			Create a minimal svg file
		"""
		if self.m_isSymmetric:
			templateName = 'TemplateSymmetry.svg'
		else:
			templateName = 'Template1.svg'
		
		paths = self.createDefaultOutlinePaths()
		if not isinstance(paths, list):
			paths = [paths]

		aff = self.getAffLogicalToSvg()
		patcher = SvgPatcherInkscape(templateName, ZUnits.svgLengthUnitString(), self.getFullSvgFilePath())
		ext = self.getSvgDefaultExtent()
		patcher.setSize(ext.m_x, ext.m_y)
		if self.m_isSymmetric:
			patcher.prepareSymmetry()

		for path in paths:
			if not path.isClosed() and not self.m_isSymmetric:
				# we assume, that the subclass provides only a "half" path, that can be expanded symmetrically
				# make a symmetrical expansion anyhow, user can change later
				line = Line(Point(), path.getStop())
				path.supplementByMirror(line)
				path.closeByLine()

			path.transformBy(aff)

			patcher.addPathGroup(path.svgCode(), 'fill:none;stroke:Black;stroke-width:1;', self.m_isSymmetric, None, path.m_groupId,)

		self.createOwnSvgDefaults(patcher, aff)

		self.addGuidesToPatcher(patcher, aff)

		circles = self.getDefaultCircles()
		if len(circles) > 0:
			circles = [aff * c for c in circles]
			parent = patcher.m_root
			for circle in circles:
				patcher.addCircle(parent, circle)

		patcher.write()


	def createOwnSvgDefaults(self, _, __):
		pass


	def getDefaultCircles(self) ->List[Circle2]:
		return []


	def recreateSvgGuides(self):
		"""
			Patches the currently valid guides into the svg file.
			Assumes, that calculateAll() has been done
		"""
		fullName = self.getFullSvgFilePath()
		if fullName is None:
			return
		patcher = SvgPatcherInkscape(fullName, ZUnits.svgLengthUnitString(), fullName)
		aff = self.getAffLogicalToSvg()
		self.addGuidesToPatcher(patcher, aff)
		patcher.write()


	def addOneGuideToPatcher(self, patcher, affNormal, pointLocal, name, lineOrFlag):
		"""
			Add one spreified guide line to the patcher (workhorse for addGuidesToPatcher)
		"""
		aff = self.getPathAffSvgLogicalToLocal(name).inverted()
		pointSvg = affNormal * aff * pointLocal

		if isinstance(lineOrFlag, bool):
			# vertical or horizontal
			if lineOrFlag:
				# vertical
				patcher.addGuide(name, pointSvg.m_x, True)		# True means vertical
			else:
				# horizontal
				patcher.addGuide(name, pointSvg.m_y, False)		# False means horizontal
		else:
			patcher.addGuide(name, pointSvg.m_y, affNormal * aff * lineOrFlag)		# False means horizontal


	def removeAllSvgGuides(self):
		"""
			Really removes all guide lines from the file
		"""
		fullName = self.getFullSvgFilePath()
		patcher = SvgPatcherInkscape(fullName, ZUnits.svgLengthUnitString(), fullName)
		patcher.removeAllGuideLines()
		patcher.write()

	
	def standardSvgStroke(self, node):
		node.set('style', 'fill:none;stroke:Black;stroke-width:1.0;')


	# some parts of calculation might be done not before writeOSC()
	def fullCalculateAll(self):
		self.calculateAll()
		self.writeOSC(None)


	def calculateAll(self):
		pass


	def updateFromInstrument(self, _):
		if self.needsAnSvgFile():
			self.readSvg()


	def writeOSC(self, fileName):
		root = OSCRoot('rootNode')
		#render = OSCCombination('the rendered part, seems no longer neccessary', '//render')
		#root.add(render)
		#self.addOscColor(root)
		self.writeMyOSC(root, root)
		root.writeScadTo(fileName)


	def writeRhino(self, fileName):
		unit = 'inch' if ZGeomItem.s_inchWanted else 'mm'
		rhinoFile = ZRhinoFile.newFile(fileName, unit)
		self.writeMyRhino(rhinoFile)
		rhinoFile.write()


	def writeMyRhino(self, rhinoFile):
		self.m_rhinoFile = rhinoFile


	def rhinoWriteLayer(self, layerName, materialName=None):
		#if materialName is None:
		color = self.getColorFromMaterialName(materialName)
		self.m_rhinoFile.getLayerWithFullPath(layerName, color)



	def makeTrickyOscColorNode(self, root, referenceNode, color):
		# seems no longer to be needed! (except one thing in BodyHollow):
		# this is rather tricky:
		# the color nodes are somehow parallel to the real object
		# if the real object is transformed, the colored object must get same transformation
		affine = referenceNode.getTransformation()
		parent = root
		if not affine.isSameAs(Affine()):
			oscTransform = OSCTransform('analog transformation', affine)
			root.add(oscTransform)
			parent = oscTransform
		color = OSCCombination('dummy color', 'color("' + color +'")')
		parent.add(color)
		return color


	def capitalize(self, aString):
		"""
			Capitalize in a way, that only the first letter is touched, the other may be capital too
		"""
		first = aString[0:1]
		rest = aString[1:]
		return first.capitalize() + rest


	def makeWidgetDouble(self, nameRoot, varName, dimmed=False):
		return WidgetDescDoubleLineInput(self, nameRoot + self.capitalize(varName), 'm_' + varName, dimmed=dimmed)


	def makeWidgetInt(self, nameRoot, varName, dimmed=False):
		return WidgetDescIntLineInput(self, nameRoot + self.capitalize(varName), 'm_' + varName, dimmed=dimmed)


	def makeWidgetString(self, nameRoot, varName):
		return WidgetDescTextLine(self, nameRoot + self.capitalize(varName), 'm_' + varName)


	def makeWidgetCheckBox(self, nameRoot, varName):
		return WidgetDescCheckBox(self, nameRoot + self.capitalize(varName), 'm_' + varName)


	def makeWidgetSpacer(self,  nameRoot, sym):
		return WidgetDescSpacer(nameRoot + sym)


	def makeComboBox(self, sym, varName):
		return WidgetDescComboBox(self, sym, 'm_' + varName)


	def getOptionsForVarName(self, varName):
		if varName == 'm_material':
			return [
				'InstrumentPart.Materials.None', 
				'InstrumentPart.Materials.Rosewood', 
				'InstrumentPart.Materials.Maple', 
				'InstrumentPart.Materials.Mahogany',
				'InstrumentPart.Materials.Spruce',
				'InstrumentPart.Materials.Cedar',
				'InstrumentPart.Materials.Ebony',
				'InstrumentPart.Materials.Ash',
				'InstrumentPart.Materials.Oak'
			]



	def addOscColor(self, parent):
		self.addOscColorFromMaterialName(parent, self.m_material)


	def getColorFromMaterialName(self, materialName: str=None) -> None:
		if materialName is None:
			materialName = self.m_material
		if materialName == 'InstrumentPart.Materials.None':
			return None
		idx = materialName.rfind('.')
		if idx < 0:
			return None
		matName = materialName[idx+1:]
		matColor = GMaterial.getMaterialNamed(matName).m_color
		return matColor

		#if mat is None:
		#	return None
		
		#if isinstance(mat, list):
		#	# rgb values
		#	colString = '[' + ', '.join(str(x) for x in mat) + ']'
		#else:
		#	# color name
		#	colString = '"' + mat + '"'
		#parent.add(OSCCallModule('color', 'color(' + colString + ')'))


	def addOscColorFromMaterialName(self, parent: OSCAbstract, materialName: str) -> None:
		col = self.getColorFromMaterialName(materialName)
		if col is None:
			return
		if isinstance(col, list):
			colString = '[' + ', '.join(str(x) for x in col) + ']'
		else:
			colString = '"' + col + '"'
		parent.add(OSCCallModule('color', 'color(' + colString + ')'))


	def allWidgetDescs(self):
		ret = []
		if self.needsAnSvgFile():
			ret.append(self.makeWidgetSpacer('InstrumentPart.Shape.', 'Name'))
			ret.append(self.makeWidgetString('InstrumentPart.', 'svgFile'))
			symm = self.makeWidgetCheckBox('InstrumentPart.', 'isSymmetric')
			if self.mustBeSymmetric():
				symm.m_dimmed = True
			ret.append(symm)

		ret.append(self.makeComboBox('InstrumentPart.Material.Name', 'material'))
			
		return ret


	def needsAnSvgFile(self):
		return True


	def checkInto(self, handler):
		if self.needsAnSvgFile():
			if self.m_svgFile is None or self.m_svgFile == '':		
				handler.addError(self, 'InstrumentPart.Error.NoSvgFile', 'm_svgFile')
			elif not self.m_svgFile.endswith('.svg'):
				handler.addError(self, 'InstrumentPart.Error.SvgFileWrongType', 'm_svgFile')
			elif self.m_svgPath is None and os.path.exists(self.getFullSvgFilePath()):
				handler.addError(self, 'InstrumentPart.Error.SvgFileNotReadable', 'm_svgFile')
		if self.m_material == 'InstrumentPart.Materials.None':
			handler.addError(self, 'InstrumentPart.Error.MaterialNotSet', 'm_material')



	def checkStrictPositiveList(self, handler, varNameList):
		for varName in varNameList:
			val = self.__dict__[varName]
			if val <= 0:
				handler.addError(self, 'InstrumentPart.Error.NonPositive', varName)


	def convertAllLengths(self, factor, _):
		self.m_affLocalToGlobal = None
		self.m_affGlobalToLocal = None

		varNames = self.allLengthVarNames()
		varNames = list(dict.fromkeys(varNames))	# remove duplicates, to play it sure
		for varName in varNames:
			#print(varName)
			oldVal = self.__dict__[varName]
			if isinstance(oldVal, list):
				newVal = [round(x * factor, 6) for x in oldVal]
			else:
				newVal = round(oldVal * factor, 6)
			self.__dict__[varName] = newVal


	def allLengthVarNames(self):
		return []


	def addPreUnitChangeDetailsTo(self, aDict):
		if not self.needsAnSvgFile():
			return
		myData = dict()
		aDict[self] = myData
		myData['getAffSvgToLogical'] = self.getAffSvgToLogical()


	def convertSvgFile(self, factor, oldProps, inchesFlag):
		"""
			Convert the svg file when a change mm <-> inch is made
		"""

		if not self.needsAnSvgFile():
			return
		svgFile = self.getFullSvgFilePath()
		if not os.path.exists(svgFile):
			return

		# now convertUnitsInSvgFile:
		myOldProps = oldProps[self]
		myOldAffSvgToLocal = myOldProps['getAffSvgToLogical']
		factorAff = Affine(Matrix() * factor)
		myNewAffLocalToSvg = self.getAffLogicalToSvg()
		fullAff = myNewAffLocalToSvg * factorAff * myOldAffSvgToLocal

		unitString = 'in' if inchesFlag else 'mm'

		patcher = SvgPatcherInkscape(svgFile, unitString, svgFile)
		ext = self.getSvgDefaultExtent()
		patcher.setSize(ext.m_x, ext.m_y)

		patcher.transformEveryNode(fullAff, factor)

		patcher.write()

		self.recreateSvgGuides()

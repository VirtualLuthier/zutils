"""
	A set of abstract widget (type) descriptions for the communication of qt widgets and model classes.
	note: no QT things imported
	Also contains 2 error related classes:
	- ZErrorDescriptor
	- ZErrorHandler
"""


import math
import re

from enum import Enum, auto
import xml.etree.ElementTree as ET

##########################################################
##########################################################


class ZWidgetType(Enum):
	UNDEFINED = auto()
	SPACER = auto()
	CHECKBOX = auto()
	DOUBLELINEINPUT = auto()
	INTLINEINPUT = auto()
	TEXTINPUT = auto()
	COMBOBOX = auto
	TEXTAREA = auto()


###########################################################
###########################################################


class WidgetDesc:
	"""
		Abstract superclass
	"""
	def __init__(self, owner, caption, varName, myType=ZWidgetType.UNDEFINED, dimmed=False):
		self.m_owner = owner
		self.m_varName = varName
		self.m_type = myType
		self.m_caption = caption
		self.m_editor = None
		self.m_widget = None
		self.m_dimmed = dimmed


	def setOwnerVal(self, val):	
		#print(f'setOwnerVal: {self.m_owner}')
		if self.m_editor is not None:
			#print(f'setOwnerVal2: {self.m_owner}')
			oldVal = self.m_owner.__dict__[self.m_varName]
			if val != oldVal:
				self.m_owner.__dict__[self.m_varName] = val
				self.m_editor.attributeHasChanged()
				return
		self.m_owner.__dict__[self.m_varName] = val
		
		


	def xmlUnder(self, parent):
		if self.m_varName is None:
			print('debug me, my varName is None')
		node = ET.SubElement(parent, self.__class__.__name__)
		node.set('instVar', self.m_varName)
		node.set('value', str(self.m_owner.__dict__[self.m_varName]))


	def updateWidget(self):
		val = str(self.m_owner.__dict__[self.m_varName])
		self.m_widget.setText(val)


	@classmethod
	def xmlReadValueFrom(cls, node, owner):
		tag = node.tag
		classObj = globals().get(tag)
		instVar = node.get('instVar')
		val = node.get('value')
		obj = classObj(owner, '', instVar)
		obj.setOwnerVal(obj.valueFromString(val))


############################################################
############################################################


class WidgetDescSpacer(WidgetDesc):
	"""
		Only represents a spacer line with a caption, no semantics
	"""
	def __init__(self, caption):
		super().__init__(None, caption, None, ZWidgetType.SPACER)

	def xmlUnder(self, _):
		pass


	def setOwnerVal(self, _):
		pass


	def updateWidget(self):
		pass


###########################################################
###########################################################


class WidgetDescCheckBox(WidgetDesc):
	"""
		Represents a boolean value
	"""
	def __init__(self, owner, caption, varName, dimmed=False):
		super().__init__(owner, caption, varName, ZWidgetType.CHECKBOX, dimmed=dimmed)
	
	
	def valueChanged(self, value):
		if value == 0 or value == 'False':
			val = False
		else:
			val = True
		#print('checkBoxStateChanged: ' + self.m_varName + ' (' + str(val) + ')')
		self.setOwnerVal(val)


	def valueFromString(self, string):
		return string == 'True'


	def updateWidget(self):
		val = self.m_owner.__dict__[self.m_varName]
		self.m_widget.setChecked(val)


###########################################################
###########################################################


class WidgetDescComboBox(WidgetDesc):
	"""
		Represents a combo box (a choice of several possible values)
	"""
	def __init__(self, owner, caption, varName):
		super().__init__(owner, caption, varName, ZWidgetType.COMBOBOX)
		

	def getOptions(self):
		ret = self.m_owner.getOptionsForVarName(self.m_varName)
		if not isinstance(ret, list):
			raise Exception('undefined options list for ' + self.m_varName)
		return ret


	def valueChanged(self, value):
		#print('WidgetDescComboBox: ' + self.m_varName + ' (' + str(value) + ')')
		self.setOwnerVal(self.getOptions()[value])


	def getCurrentIndex(self):
		selectedOption = self.m_owner.__dict__[self.m_varName]
		idx = 0
		for opt in self.getOptions():
			if opt == selectedOption:
				return idx
			idx += 1
		return 0


	def valueFromString(self, string):
		return string


	def updateWidget(self):
		val = self.getCurrentIndex()
		self.m_widget.setCurrentIndex(val)


###########################################################
###########################################################


class WidgetDescTextLine(WidgetDesc):
	"""
		Represents a line of text
	"""
	def __init__(self, owner, caption, varName, dimmed=False):
		super().__init__(owner, caption, varName, ZWidgetType.TEXTINPUT, dimmed)


	def valueChanged(self, value):
		self.setOwnerVal(value)


	def valueFromString(self, string):
		return string


#########################################################
#########################################################

class WidgetDescTextArea(WidgetDesc):
	"""
		Represents a larger text
	"""
	def __init__(self, owner, caption, varName):
		super().__init__(owner, caption, varName, ZWidgetType.TEXTAREA)


	def valueChanged(self):
		text = self.m_widget.toPlainText()
		self.setOwnerVal(text)


	def valueFromString(self, string):
		return string


	def updateWidget(self):
		val = str(self.m_owner.__dict__[self.m_varName])
		self.m_widget.setPlainText(val)
		



##########################################################
##########################################################


class WidgetDescDoubleLineInput(WidgetDesc):
	"""
		Represents a float number
	"""
	def __init__(self, owner, caption, varName, minVal=math.nan, maxVal=math.nan, numDigitsAfter=math.nan, dimmed=False):
		super().__init__(owner, caption, varName, ZWidgetType.DOUBLELINEINPUT, dimmed)
		#print(f'create WidgetDescDoubleLineInput {self.m_owner}')
		self.m_minVal = minVal
		self.m_maxVal = maxVal
		self.m_numDigitsAfter = numDigitsAfter


	def valueChanged(self, value):
		#print(f'valueChanged (ignored):')
		#print(f'valueChanged (ignored): {value}')
		#return
		self.setOwnerVal(self.valueFromString(value))


	def valueFromString(self, string):
		if string == '':
			return 0
		try:
			return float(string)
		except ValueError as _:
			return 0


##########################################################
##########################################################


class WidgetDescIntLineInput(WidgetDesc):
	"""
		Represents an int value
	"""
	def __init__(self, owner, caption, varName, minVal=math.nan, maxVal=math.nan, dimmed=False):
		super().__init__(owner, caption, varName, ZWidgetType.INTLINEINPUT, dimmed=dimmed)
		self.m_minVal = minVal
		self.m_maxVal = maxVal


	def valueChanged(self, value):
		stringParts = re.findall(r'\-?\d+', value)
		if len(stringParts) == 0:
			val = 0
		else:
			val = int(stringParts[0])
		#print('valueChanged: ' + self.m_varName + ' (' + str(value) + ')')
		#print('stringPart = ' + str(stringPart))
		#if stringPart == '':
		#	val = 0
		#else:
		#	print('stringPart: ' + stringPart)
		#	val = int(stringPart)

		self.setOwnerVal(val)


	def valueFromString(self, string):
		if string == '':
			return 0
		try:
			return int(string)
		except ValueError as _:
			return 0


################################################################
################################################################
################################################################
################################################################
# is strangely similar to WidgetDescriptor !?

class ZErrorDescriptor:
	"""
		Represents an error and its location
	"""
	def __init__(self, owner, caption1, caption2, varName, args=None):
		self.m_owner = owner
		self.m_caption1 = caption1
		self.m_caption2 = caption2
		self.m_varName = varName
		if args is not None and not isinstance(args, list):
			args = [args]
		self.m_args = args


###############################################################
###############################################################

class ZErrorHandler:
	"""
		More an interface for an object that collects error descriptors
	"""
	def __init__(self) -> None:
		self.m_errorList = []


	def addError(self, owner, caption, varName=None, args=None):
		self.m_errorList.append(ZErrorDescriptor(owner, caption, caption + 'TT', varName, args))

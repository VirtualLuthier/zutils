"""
	Contains the classes:
	- ZMainWindow
	- ErrorWindow
"""


############################################################
############################################################


import os.path
import math

from PySide6.QtWidgets import (
	QInputDialog, QMainWindow, QWidget, QComboBox, QLabel, QLineEdit, QApplication, QCheckBox, QMessageBox, QListWidget, 
	QPlainTextEdit, QSplitter, QFileDialog, QTabWidget, QVBoxLayout, QScrollArea, QTextEdit)
from PySide6.QtCore import QLocale, QTranslator, Qt
from PySide6.QtGui import QDoubleValidator, QFont

from zutils.ZWidgetDescriptors import ZWidgetType, ZErrorDescriptor


###########################################################
###########################################################


class ZMainWindow(QMainWindow):
	"""
		A qt main window with several useful functions:
		- support for one document, including change control
		- support for WidgetDescriptors
		- support for error checking
		- main menu support
	"""

	m_app = None
	m_standardStoreFolder = '.'	# should be initialized by subclass


	def __init__(self):
		super().__init__()
		ZMainWindow.m_app = QApplication.instance()
		#ZMainWindow.m_app.focusChanged.connect(self.onFocusChanged)
		self.m_changedFlag = False

		self.m_allWidgetDescriptors = []
		self.m_errorList = []
		self.m_errorWindow = None

		self.m_currentFile = None
		self.m_currentModel = None

		self.m_menuBar = None
		self.m_menuFile = None

		self.m_currentEmphasizedWidget = None


	def attributeHasChanged(self):
		self.m_changedFlag = True


	@classmethod
	def makeFileName(cls, name):
		"""
			Create a string that can represent the given name as a file name
		"""
		return 'f-' + ''.join([cls.legalFileCharFor(x) for x in name])


	@classmethod
	def legalFileCharFor(cls, chr):
		"""
			Return True, if the char in chr is legal in a file name (not very exact)
		"""
		num = ord(chr[0])
		if num < 33:
			return '-'
		if chr in r'*."/\\[]:;|,?() <>|':
			return '-'
		return chr


	def resetModel(self):
		"""
			remove all references to the current model
		"""
		self.closeErrorWindow()
		self.m_currentEmphasizedWidget = None
		self.m_allWidgetDescriptors = []
		self.m_errorList = []
		self.m_changedFlag = False


	#def onFocusChanged(self, oldWidgt, newWidget):
	#	#print('focus changed')
	#	pass


	def okToLoadNewPart(self, varName, sym):
		"""
			If the current model has panding changes, ask, if to forget them. Return True means, current model can be forgotten
		"""
		if not self.checkForCurrentModel():
			return
		if self.m_currentModel.__dict__[varName] is None:
			return True
		return self.confirm(sym, sym + 'TT')


	def deemphasizeWidget(self):
		"""
			If currently a widget is emphasized (visually), deemphasize it
		"""
		w = self.m_currentEmphasizedWidget
		if w is None:
			return
		w.setStyleSheet('background-color: white;')
		self.m_currentEmphasizedWidget = None


	def emphasizeWidget(self, widget):
		"""
			Emphasize widget visually
		"""
		self.deemphasizeWidget()
		widget.setStyleSheet('background-color: red;')
		self.m_currentEmphasizedWidget = widget


	def createMainMenu(self):
		menuBar = self.menuBar()

		fileMenu = menuBar.addMenu(self.tr('Generics.Menu.File'))

		self.addMenuItem(fileMenu, 'Generics.Menu.File.New', self.choosedFileNew)
		self.addMenuItem(fileMenu, 'Generics.Menu.File.Open', self.choosedFileOpen)
		self.addMenuItem(fileMenu, 'Generics.Menu.File.Reload', self.choosedFileReload)
		fileMenu.addSeparator()
		self.addMenuItem(fileMenu, 'Generics.Menu.File.Save', self.choosedFileSave)
		self.addMenuItem(fileMenu, 'Generics.Menu.File.SaveAs', self.choosedFileSaveAs)

		self.m_menuBar = menuBar
		self.m_menuFile = fileMenu


	def checkForCurrentModel(self):
		"""
			Return True, if there is a model loaded currently. Notify, if there is none
		"""
		if self.m_currentModel is not None:
			return True
		self.notify('Generics.Error.NoModelLoaded')
		return False


	def choosedFileNew(self):
		"""
			Create a new model
		"""
		if not self.okToClose():
			return
		title = self.prompt('Generics.Menu.File.New.EnterNewName')
		if title == '':
			return
		fName = self.makeFileName(title)
		#print(fName)
		folder = self.m_standardStoreFolder + '/' + fName
		file = folder + '.xml'
		if os.path.isdir(folder):
			self.notify('Generics.Menu.File.Error.FolderExists', [folder])
			return
		if os.path.isdir(file):
			self.notify('Generics.Menu.File.Error.FileExists', [file])
			return
		self.m_currentFile = None
		self.setNewModel(title, folder)
		self.m_currentFile = file


	def choosedFileOpen(self):
		"""
			Open a model from a file
		"""
		if not self.okToClose():
			return
		caption = self.tr('Generics.Menu.File.Open.Title')
		folder = self.m_standardStoreFolder
		selected = QFileDialog.getOpenFileName(self, caption, folder, '*.xml')
		fileName = selected[0]
		if len(fileName) == 0:
			return
		self.openFromFile(fileName)


	def choosedFileReload(self):
		"""
			Relaod the current model from the file, forgetting recent changes
		"""
		if not self.m_currentFile:
			self.notify('Generics.Error.NoCurrentFile')
			return
		if not self.okToClose():
			return
		self.openFromFile(self.m_currentFile)


	def choosedFileSave(self):
		"""
			Save current file (or save as, if needed)
		"""
		if not self.checkForCurrentModel():
			return
		if self.m_currentFile is None:
			self.choosedFileSaveAs()
			return
		self.doWrite(self.m_currentFile)


	def choosedFileSaveAs(self):
		"""
			File save as
		"""
		if not self.checkForCurrentModel():
			return
		caption = self.tr('Generics.Menu.File.SaveAs.Title')
		oldFile = self.m_standardStoreFolder + '/something.xml' if self.m_currentFile is None else self.m_currentFile
		selected = QFileDialog.getSaveFileName(self, caption, oldFile, '*.xml')
		fileName = selected[0]
		if len(fileName) == 0:
			return

		self.doWrite(fileName)


	def doWrite(self, fileName):
		"""
			Do the file save into given file name
		"""
		self.m_currentModel.xmlWrite(fileName)
		self.m_currentFile = fileName
		self.m_changedFlag = False
		self.setCurrentTitle()


	def closeEvent(self, event):
		"""
			Callback for UI close event. Do or ignore, if pending changes
		"""
		if self.okToClose():
			self.closeErrorWindow()
			super().closeEvent(event)
		else:
			event.ignore()


	def allWidgetDesriptionsOf(self, owner):
		"""
			Return all widgets descriptions of the given owner
		"""
		ret = []
		for w in self.m_allWidgetDescriptors:
			if w.m_owner == owner:
				ret.append(w)
		return ret


	def findWidgetDescriptorFor(self, owner, varName):
		"""
			Return the widgetDescriptor for the geiven owner and instance var name
		"""
		for w in self.m_allWidgetDescriptors:
			if w.m_owner == owner and w.m_varName == varName:
				return w
		return None


	#def addAllWidgetDescriptionsOf(self, parent, owner):
	#	wNode = ET.SubElement(parent, 'Widgets')
	#	for w in self.allWidgetDesriptionsOf(owner):
	#		w.xmlUnder(wNode)


	def createTranslator(self, nlsName):
		"""
			create and install the wanted translator in the qt app
		"""
		app = self.m_app
		if not os.path.exists(nlsName):
			raise Exception('nls file not found: ' + nlsName)
		translator = QTranslator(app)	# this argument (app) is very important !
		translator.load(nlsName)
		app.installTranslator(translator)


	def addMenuItem(self, parent, sym, action):
		theAction = parent.addAction(self.tr(sym))
		theAction.triggered.connect(action)


	def confirm(self, title, text=None):
		"""
			Show the 1 or 2 texts and return True, if OK is clicked
		"""
		msg = QMessageBox()
		msg.setIcon(QMessageBox.Warning)
		msg.setWindowTitle(self.tr(title))
		if text is None:
			text = title + 'TT'
		msg.setText(self.tr(text))
		msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

		retval = msg.exec_()
		return retval == QMessageBox.Ok


	def notify(self, text, details=None):
		"""
			Show the 1 or 2 texts and let user click ok
		"""
		msg = QMessageBox()
		msg.setIcon(QMessageBox.Warning)
		msg.setWindowTitle(self.tr('Generics.Error.Name'))
		msg.setText(self.tr(text, details))
		msg.setStandardButtons(QMessageBox.Ok)

		msg.exec_()


	def prompt(self, msg, oldText=''):
		"""
			Prompt for a text line. Show the old text to edit
		"""
		tr = self.tr(msg)
		text, ok = QInputDialog.getText(self, '?', tr, text=oldText)
		if ok:
			return text
		return None


	def okToClose(self):
		"""
			Check, if i have no unsaved changes, or if they can be forgotten
		"""
		ret = True
		if self.m_changedFlag:
			ret = False
		if ret:
			return True
		return self.confirm('Generics.Menu.File.ForgetChanges.Title', 'Generics.Menu.File.ForgetChanges.Text')


	@classmethod
	def tr(cls, symbol, params=None):
		"""
			Translate the symbol and insert additional strings, if needed.
			QT translation is said to be unstable.
		"""
		ret = cls.m_app.tr(symbol)
		if params is None:
			params = []
		length = len(params)
		if length == 0:
			return ret
		if length == 1:
			#print('ret = ' + ret + ', param = ' + str(params[0]))
			return ret.format(str(params[0]))
		return ret.format(str(params[0]), str(params[1]))


	def updateAllWidgets(self):
		"""
			Update the contents of all my widgets from the model
		"""
		for w in self.m_allWidgetDescriptors:
			w.updateWidget()


	def createCheckBox(self, parent, descriptor):
		"""
			Create a qt checkbox and connect to widgetDescriptor
		"""
		descriptor.m_editor = self
		cb = QCheckBox()
		owner = descriptor.m_owner
		varName = descriptor.m_varName
		symbol = descriptor.m_caption
		cb.setChecked(owner.__dict__[varName])
		if descriptor.m_dimmed:
			cb.setEnabled(False)
		cb.setToolTip(self.tr(symbol + 'TT'))
		parent.addRow(self.tr(symbol), cb)
		cb.stateChanged.connect(descriptor.valueChanged)
		descriptor.m_widget = cb
		self.m_allWidgetDescriptors.append(descriptor)


	def createDoubleLineInput(self, parent, descriptor):
		"""
			Create a qt double input and connect to widgetDescriptor
		"""
		
		descriptor.m_editor = self
		lineEdit = QLineEdit()

		owner = descriptor.m_owner
		varName = descriptor.m_varName
		minVal = descriptor.m_minVal
		maxVal = descriptor.m_maxVal
		numDigitsAfter = descriptor.m_numDigitsAfter
		symbol = descriptor.m_caption

		lineEdit.setToolTip(self.tr(symbol + 'TT'))
		lineEdit.setText(str(owner.__dict__[varName]))
		if descriptor.m_dimmed:
			lineEdit.setEnabled(False)
		if not math.isnan(minVal):
			validator = QDoubleValidator(minVal, maxVal, numDigitsAfter, notation=QDoubleValidator.StandardNotation)
			validator.setLocale(QLocale.c())		# use the "neutral" locale!
			lineEdit.setValidator(validator)
		parent.addRow(self.tr(symbol), lineEdit)

		# i have no idea, why the first does not wor, but the second does !!!!!!!!!!
		lineEdit.textChanged.connect(descriptor.valueChanged)
		#lineEdit.textChanged.connect(lambda  text: descriptor.valueChanged(text))

		#lineEdit.textEdited.connect(descriptor.valueChanged)
		#print(f'descriptor: {descriptor}')
		#lineEdit.textChanged.connect(descriptor.m_owner)
		#print('createDoubleLineInput: ')
		descriptor.m_widget = lineEdit
		self.m_allWidgetDescriptors.append(descriptor)


	def createTextLineInput(self, parent, descriptor):
		"""
			Create a qt text line input and connect to widgetDescriptor
		"""
		descriptor.m_editor = self
		lineEdit = QLineEdit()

		owner = descriptor.m_owner
		varName = descriptor.m_varName
		symbol = descriptor.m_caption
		lineEdit.setToolTip(self.tr(symbol + 'TT'))
		lineEdit.setText(str(owner.__dict__[varName]))
		if descriptor.m_dimmed:
			lineEdit.setEnabled(False)
		parent.addRow(self.tr(symbol), lineEdit)
		lineEdit.textChanged.connect(descriptor.valueChanged)
		descriptor.m_widget = lineEdit
		self.m_allWidgetDescriptors.append(descriptor)


	def createTextArea(self, parent, descriptor):
		"""
			Create a qt multiline text and connect to widgetDescriptor
		"""
		descriptor.m_editor = self
		textEdit = QPlainTextEdit()

		owner = descriptor.m_owner
		varName = descriptor.m_varName
		symbol = descriptor.m_caption
		textEdit.setToolTip(self.tr(symbol + 'TT'))
		textEdit.setPlainText(str(owner.__dict__[varName]))
		parent.addRow(self.tr(symbol), textEdit)
		textEdit.textChanged.connect(descriptor.valueChanged)
		descriptor.m_widget = textEdit
		
		self.m_allWidgetDescriptors.append(descriptor)


	def createComboBox(self, parent, descriptor):
		"""
			Create a qt combo box and connect to widgetDescriptor
		"""
		descriptor.m_editor = self
		widget = QComboBox()

		symbol = descriptor.m_caption
		widget.setToolTip(self.tr(symbol + 'TT'))
		for sym in descriptor.getOptions():
			widget.addItem(self.tr(sym))
		widget.setCurrentIndex(descriptor.getCurrentIndex())
		parent.addRow(self.tr(symbol), widget)
		widget.currentIndexChanged.connect(descriptor.valueChanged)
		descriptor.m_widget = widget
		self.m_allWidgetDescriptors.append(descriptor)


	def createIntLineInput(self, parent, descriptor):
		"""
			Create a qt int input and connect to widgetDescriptor
		"""
		descriptor.m_editor = self
		lineEdit = QLineEdit()

		owner = descriptor.m_owner
		varName = descriptor.m_varName
		minVal = descriptor.m_minVal
		maxVal = descriptor.m_maxVal
		numDigitsAfter = 0
		symbol = descriptor.m_caption

		lineEdit.setToolTip(self.tr(symbol + 'TT'))
		lineEdit.setText(str(owner.__dict__[varName]))
		if descriptor.m_dimmed:
			lineEdit.setEnabled(False)
		if not math.isnan(minVal):
			validator = QDoubleValidator(minVal, maxVal, numDigitsAfter, notation=QDoubleValidator.StandardNotation)
			validator.setLocale(QLocale.c())		# use the "neutral" locale!
			lineEdit.setValidator(validator)
		parent.addRow(self.tr(symbol), lineEdit)
		lineEdit.textChanged.connect(descriptor.valueChanged)
		descriptor.m_widget = lineEdit
		self.m_allWidgetDescriptors.append(descriptor)	# seems to be needed (prevent garbage collection?)


	def createWidgetsInLayout(self, layout, widgetDescs):
		"""
			This is done here, and not by the WidgetDesc itself,
			so the Instrument classes have no connection to Qt
		"""
		for w in widgetDescs:
			if w.m_type == ZWidgetType.CHECKBOX:
				self.createCheckBox(layout, w)		
			elif w.m_type == ZWidgetType.DOUBLELINEINPUT:
				self.createDoubleLineInput(layout, w)
			elif w.m_type == ZWidgetType.INTLINEINPUT:
				self.createIntLineInput(layout, w)
			elif w.m_type == ZWidgetType.SPACER:
				self.createSpacerItem(layout, w)
			elif w.m_type == ZWidgetType.TEXTINPUT:
				self.createTextLineInput(layout, w)
			elif w.m_type == ZWidgetType.COMBOBOX:
				self.createComboBox(layout, w)
			elif w.m_type == ZWidgetType.TEXTAREA:
				self.createTextArea(layout, w)


	def createTabView(self, parentLayout):
		"""
			Return a QTabWidget located under the parentLayout
			If parentLayout is None, as the centralWidget
		"""
		tabsHolder = QWidget()
		if parentLayout is None:
			self.setCentralWidget(tabsHolder)
		else:
			parentLayout.addWidget(tabsHolder)		
		tabsLayout = QVBoxLayout()
		tabsHolder.setLayout(tabsLayout)
		tabsWidget = QTabWidget()
		tabsLayout.addWidget(tabsWidget)

		return tabsWidget


	def createOneTab(self, parentTabsWidget, caption):
		"""
		Create one tab with the given caption and a scrollarea in the given parentTabsWidget.
		return (tabWidget, subWidget, scroller)
		"""
		tabWidget = QWidget()
		parentTabsWidget.addTab(tabWidget, caption)
		tabLayout = QVBoxLayout()
		tabWidget.setLayout(tabLayout)
		
		scroller = QScrollArea()
		scroller.setWidgetResizable(True)
		tabLayout.addWidget(scroller)
		subWidget = QWidget()
		scroller.setWidget(subWidget)
		return [tabWidget, subWidget, scroller]


	def createSpacerItem(self, parent, descriptor):
		"""
			Create a comment-like spacer item and connect to descriptor
		"""
		capLabel = QLabel(self.tr(descriptor.m_caption))
		myFont = QFont()
		myFont.setBold(True)
		capLabel.setFont(myFont)
		parent.addRow(capLabel, QLabel(''))


	def errorCheckAll(self):
		"""
			Run all checks and open an error window
		"""
		self.deemphasizeWidget()
		if not self.checkForCurrentModel():
			return
		model = self.m_currentModel
		self.m_errorList = []
		checked = model.calculateAll()
		if not checked:
			self.notify('Generics.Error.FatalErrorChecking')
			return
		self.updateAllWidgets()
		model.checkInto(self)
		self.openErrorWindow()


	def addError(self, owner, caption, varName=None, args=None):
		"""
			Add some error desription to my error list
		"""
		self.m_errorList.append(ZErrorDescriptor(owner, caption, caption + 'TT', varName, args))


	def openErrorWindow(self):
		"""
			Open a window with a list of my current errors
		"""
		self.closeErrorWindow()
		if len(self.m_errorList) > 0:		
			self.m_errorWindow = ErrorWindow(self, self.tr('Generics.Error.ErrorsFound'), self.m_errorList)


	def closeErrorWindow(self):
		"""
			Close my error window (if existing)
		"""
		if self.m_errorWindow is not None:
			self.m_errorWindow.close()
			self.m_errorWindow = None


	def makeFolder(self, folder):
		"""
			Create the given folder. If impossible: notify and return False.
		"""
		if os.path.exists(folder):
			return True
		try:
			os.makedirs(folder)
			return True
		except Exception as _:
			self.notify('Generics.Error.CouldNotCreateFolder', [folder])
			return False


	def startExternalProgram(self, progName, args):
		"""
			Start the given program with given args. Do not care about the output.
			If no full path is given, the program must be on the executable path.
		"""
		cmdLine = progName
		for arg in args:
			cmdLine += ' ' + arg
		cmdLine = cmdLine.replace('/', os.sep)
		cmdLine = cmdLine.replace('\\', os.sep)
		#print('starting ' + cmdLine)
		os.popen(cmdLine)



###########################################################
###########################################################


class ErrorWindow(QMainWindow):
	"""
		A window with a list and a field to describe the current list selection.
		The parent window must provide the selection details (including the translation)
	"""
	def __init__(self, parentWindow, title, errorList):
		super().__init__()
		self.m_parentWindow = parentWindow
		self.m_errorList = errorList
		splitter = QSplitter(Qt.Horizontal)
		self.setCentralWidget(splitter)
		theList = QListWidget()
		for err in errorList:
			theList.addItem(ZMainWindow.tr(err.m_caption1))
		self.m_theListWidget = theList
		theList.itemClicked.connect(self.errorClicked)
		splitter.addWidget(theList)
		text = QTextEdit()
		self.m_textWidget = text
		splitter.addWidget(text)
		self.setWindowTitle(title)
		self.setMinimumWidth(400)
		self.setMinimumHeight(400)
		self.show()


	def errorClicked(self, _):
		idx = self.m_theListWidget.currentRow()
		error = self.m_errorList[idx]
		self.m_textWidget.setText(ZMainWindow.tr(error.m_caption2, error.m_args))
		self.m_parentWindow.emphasizeError(error)

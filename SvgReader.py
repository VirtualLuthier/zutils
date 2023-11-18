"""
	Contains only the class with the same name
"""

import math
import os.path
import xml.etree.ElementTree as ET
from zutils.ZGeom import Point, Circle2, Ellipse2
from zutils.ZPath import ZPath, ZBezier3Segment, ZLineSegment, ZBezier2Segment, ZArcSegment

############################################
############################################


class SvgPathReader:
	"""
		Allows to read an existing svg file and to convert pathes and ellipses to objects of class ZPath.ZPath
	"""
	@classmethod
	def classParsePath(cls, dAttr, smartCircles=True) -> ZPath:
		"""
			Return the path described in the d-attribute.
		"""
		instance = cls()
		return instance.parsePath(dAttr, smartCircles)


	def __init__(self):
		self.m_fName = None
		self.m_namespaces = {'svg': 'http://www.w3.org/2000/svg'}
		self.m_dAtributeName = 'd'
		self.m_text = None
		self.m_idx = 0
		self.m_commands = []
		self.m_currentCommand = None
		self.m_args = []
		self.m_lastPoint = Point()
		self.m_possibleNextCmdName = None
		self.m_paths = []
		self.m_circles = []
		self.m_currentLoopStart = None

	def initialize(self):
		self.m_text = None
		self.m_idx = 0
		self.m_commands = []
		self.m_currentCommand = None
		self.m_args = []
		self.m_lastPoint = Point()
		self.m_possibleNextCmdName = None
		self.m_currentLoopStart = None

	def addNamespace(self, symbol, url):
		self.m_namespaces[symbol] = url

	def setDAttributeName(self, attName):
		self.m_dAtributeName = attName

	def foundSomething(self):
		return len(self.m_commands) > 0


	def readFile(self, fName) -> list[ZPath]:
		if not os.path.exists(fName):
			raise Exception('SvgPathReader.readFile(): File does not exist: ' + fName)
		self.m_fName = fName
		tree = ET.parse(fName)
		rootNode = tree.getroot()
		self.m_paths = []

		#self.enumerateTags(rootNode)

		for g in rootNode.findall('svg:g', namespaces=self.m_namespaces):
			#self.enumerateTags(g)
			self.analyzeGroup(g)

		for circle in rootNode.findall('svg:circle', namespaces=self.m_namespaces):
			self.parseCircle(circle)

		return self.m_paths


	def analyzeGroup(self, node):
		for pathNode in node.findall('svg:path', namespaces=self.m_namespaces):
			text = pathNode.get(self.m_dAtributeName)
			if not text:
				#print('could not find attribute ' + self.m_dAtributeName)
				# not every path must be mirrored!
				text = pathNode.get('d')
			path = self.parsePath(text)
			path.m_groupId = self.getGroupName(node)
		for circle in node.findall('svg:circle', namespaces=self.m_namespaces):
			self.parseCircle(circle)
		for ellipse in node.findall('svg:ellipse', namespaces=self.m_namespaces):
			self.parseEllipse(ellipse)
		for group in node.findall('svg:g', namespaces=self.m_namespaces):
			# groups can be nested
			self.analyzeGroup(group)


	def getGroupName(self, node):
		#print('in getGroupNode')
		while node:
			#print(node)
			theId = node.get('id', None)
			if theId is not None:
				#print('found group name:' + theId)
				return theId
			node = node.find('..')
		return None


	def enumerateTags(self, node):
		for child in node:
			print (child.tag)


	def parseCircle(self, circleXml):
		cx = float(circleXml.get('cx'))
		cy = float(circleXml.get('cy'))
		r = float(circleXml.get('r'))
		self.m_circles.append(Circle2(Point(cx, cy), r))


	def parseEllipse(self, ellipseXml):
		cx = float(ellipseXml.get('cx'))
		cy = float(ellipseXml.get('cy'))
		rx = float(ellipseXml.get('rx'))
		ry = float(ellipseXml.get('ry'))
		if abs(rx - ry) < 0.1:
			self.m_circles.append(Circle2(Point(cx, cy), rx))
		else:
			self.m_circles.append(Ellipse2(Point(cx, cy), rx, ry))


	def parsePath(self, text, smartCircles=True) -> ZPath:
		self.initialize()
		self.m_text = text
		self.m_idx = 0
		while True:
			token = self.nextToken()
			if token is None:
				break
			#print(token)
			value = token[0]
			theType = token[1]
			
			if theType == 'command':
				# we must start a new command
				if value in 'zZ':
					self.finishLastCommand()
					self.closeTheCurrentLoop()
					continue
				self.addCommand(SvgCommand.getCommandForName(value))

			elif theType == 'number':
				# we found a number
				self.m_args.append(float(value))
				cmd = self.m_currentCommand
				
				if cmd is None:
					# this may never happen for the first command
					# currentCommand is None, we must create a new command,
					# that was not given in the d string
					# so we can assume, that self.m_possibleNextCmdName is set
					cmd = SvgCommand.getCommandForName(self.m_possibleNextCmdName)
					self.addCommand(cmd)
					cmd.m_start = self.m_lastPoint
					# m_args was cleaned in addCommand()
					self.m_args.append(float(value))

				possibleNextCmdName = cmd.getDefaultFollowerName(len(self.m_args))
				self.m_possibleNextCmdName = possibleNextCmdName
				if possibleNextCmdName is not None:
					# currentCommand is finished, we might have to create a new one
					self.finishLastCommand()
					self.m_currentCommand = None
				
		self.finishLastCommand()
		for cmd in self.m_commands:
			cmd.checkArguments()
		path = self.getPath()
		if smartCircles:
			self.m_circles.extend(path.extractFullEllipses())
		if len(path.m_segments) > 0:
			self.m_paths.append(path)
		return path


	def addEllipsesFromPath(self, path):
		for seg in path.m_segments:
			# this must be a bunch of ZArcSegments
			center = seg.m_center
			rx = seg.m_rx
			ry = seg.m_ry
			if abs(rx - ry) < 0.00001:
				newOne = Circle2(center, rx)
			else:
				newOne = Ellipse2(center, rx, ry)
			found = False
			for circle in self.m_circles:
				if circle.isSameAs(newOne):
					found = True
					break
			if not found:
				self.m_circles.append(newOne)


	def closeTheCurrentLoop(self):
		# if needed, create a line from the last stop point to the very first start point
		start = self.m_currentLoopStart
		lastCmd = self.m_commands[-1]
		stop = lastCmd.m_stop
		if start.isSameAs(stop):
			return
		cmd = SvgCommandLine('L')
		cmd.m_start = stop
		cmd.m_stop = start
		self.m_commands.append(cmd)
		self.m_lastPoint = start	# stop in reality


	def getPath(self):
		path = ZPath()
		segs = []
		for cmd in self.m_commands:
			pathParts = cmd.asPartPathCollection()
			if pathParts is not None:
				segs.extend(pathParts)
		path.setSegments(segs)
		return path


	def addCommand(self, command):
		self.finishLastCommand()
		self.m_commands.append(command)
		command.m_start = self.m_lastPoint
		self.m_currentCommand = command
		if self.m_currentLoopStart is None:
			if command.m_cmdString not in 'mM':
				# the abnormal case, normally a loop will begin with mM
				self.m_currentLoopStart = self.m_lastPoint
			

	def finishLastCommand(self):
		if self.m_currentCommand is not None:
			self.m_lastPoint = self.m_currentCommand.acceptNumbers(self.m_args)
		self.m_args = []
		self.m_currentCommand = None


	def nextToken(self):
		"""
			Return the next token, but swallow 'ignore' and 'comma' tokens. Should be quite helpful for debugging.
		"""
		while True:
			tok = self.nextTokenOld()
			if tok is None:
				# finished
				return None
			if not tok[1] in ['ignore', 'comma']:
				# useful token
				return tok


	def nextTokenOld(self):
		text = self.m_text
		idx = self.m_idx
		if len(text) <= idx:
			return None
		nextChar = text[idx]
		idx = idx + 1
		self.m_idx = idx
		if nextChar.isalpha():
			return [nextChar, 'command']
		if nextChar == ' ':
			return [nextChar, 'ignore']
		if nextChar == ',':
			return [nextChar, 'comma']
		collector = nextChar
		while True:
			if len(text) <= idx:
				return [collector, 'number']
			nextChar = text[idx]			
			if nextChar not in '-.0123456789':
				return [collector, 'number']
			collector = collector + nextChar
			idx = idx + 1
			self.m_idx = idx


################################################
################################################


class SvgCommand:
	def __init__(self, cmdString):
		self.m_isRelative = cmdString.islower()
		self.m_cmdString = cmdString.upper()
		self.m_stop = None
		self.m_start = None


	def __str__(self):
		rel = '(abs) '
		if self.m_isRelative:
			rel = '(rel) '
		ret = self.__class__.__name__ + '(' + rel
		ret = ret + ')'
		return ret


	def acceptPointsFrom(self, numbers):
		idx = 0
		if len(numbers) %2 != 0:
			raise Exception('odd number of numbers is not accepted')
		ret = []
		while idx < len(numbers):
			p = self.calculatePoint(Point(numbers[idx], numbers[idx+1]))
			ret.append(p)
			idx = idx + 2
		return ret


	def calculatePoint(self, point):
		if self.m_isRelative:
			if self.m_start is None:
				print('hoppala')
			return self.m_start + point
		return point


	def getDefaultFollowerName(self, _):		# second arg = number of found number args
		# it is possible, that I am already complete with this num of args
		# then I return a command that handles the rest of the args
		# then I will be finished now
		# returning None means: I will handle more args
		# overridden by subclasses
		return None


	def commandFor(self, cmd):
		# return the cmd as upper/lower case, depending on my own relative setting
		if self.m_isRelative:
			return cmd.lower()
		return cmd.upper()


	@classmethod
	def getCommandForName(cls, value):
		if value in 'mM':
			return SvgCommandMove(value)		
		if value in 'lL':
			return SvgCommandLine(value)
		if value in 'hH':
			return SvgCommandHorizontal(value)
		if value in 'vV':
			return SvgCommandVertical(value)
		if value in 'qQ':
			return SvgCommandBezierQ(value)
		if value in 'cC':
			return SvgCommandBezierC(value)
		if value in 'aA':
			return SvgCommandArc(value)

		if value in 'sS':
			raise NotImplementedError('svg command: ' + value)
			#return SvgCommandBezierS(value)
		if value in 'tT':
			raise NotImplementedError('svg command: ' + value)
			#return SvgCommandBezierT(value)

		raise Exception('unknown command: ' + value)

	def asPartPathCollection(self):
		raise Exception('not implemented asPartPathCollection() in class: ' + self.__class__.__name__)


#########################################################
#########################################################


class SvgCommandMove(SvgCommand):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
		

	def acceptNumbers(self, numbers):
		points = self.acceptPointsFrom(numbers)
		self.m_stop = points[0]
		return self.m_stop

	def checkArguments(self):
		return self.m_stop is not None

	def getDefaultFollowerName(self, numOfArgs):
		if numOfArgs == 2:
			return self.commandFor('L')
		return None

	def asPartPathCollection(self):
		return None


#################################################
#################################################


class SvgCommandBezier(SvgCommand):
	def __init__(self, cmdString):
		super().__init__(cmdString)
		self.m_points = []


	def checkArguments(self):
		return True


	def acceptNumbers(self, numbers):
		self.m_points = self.acceptPointsFrom(numbers)
		if len(self.m_points) == 0:
			print('hoppala, got 0 points')
		self.m_stop = self.m_points[-1]
		return self.m_points[-1]


#################################################
#################################################


class SvgCommandBezierC(SvgCommandBezier):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
	def checkArguments(self):
		length = len(self.m_points)
		if length == 0:
			return False
		if length % 3 == 0:
			return True
		return False


	def asPartPathCollection(self):
		ret = []
		ii = 0
		start = self.m_start
		points = self.m_points
		while ii < len(points):
			stop = points[ii+2]
			handle1 = points[ii]
			handle2 = points[ii+1]
			if handle1.isSameAs(handle2) and (handle1.isSameAs(start) or handle1.isSameAs(stop)):
				# i am degenerated to a straight line
				seg = ZLineSegment(start, stop)
			else:
				seg = ZBezier3Segment(start, stop, handle1, handle2)
			ret.append(seg)
			start = points[ii+2]
			ii = ii + 3
		return ret


	def acceptPointsFrom(self, numbers):
		# a bit tricky: relativ means, it is always relative to the end point of the last segment
		# (at least for cC)

		if len(numbers) %2 != 0:
			raise Exception('odd number of numbers is not accepted')
		idx = 0
		currentReference = self.m_start
		ret = []
		while idx < len(numbers):
			p = Point(numbers[idx], numbers[idx+1])
			if self.m_isRelative:
				p = currentReference + p
			ret.append(p)
			if idx % 6 == 4:
				# we just added a 3rd point, i.e. this is our new reference point
				currentReference = p
			idx = idx + 2
		return ret


###################################################
###################################################


class SvgCommandBezierM(SvgCommandBezier):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
	def checkArguments(self):
		return True


####################################################
####################################################


class SvgCommandBezierS(SvgCommandBezier):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
	def checkArguments(self):
		return True


###################################################
###################################################


class SvgCommandBezierQ(SvgCommandBezier):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
	def checkArguments(self):
		length = len(self.m_points)
		if length == 0:
			return False
		if length % 2 == 0:
			return True
		return False


	def acceptPointsFrom(self, numbers):
		# a bit tricky: relativ means, it is always relative to the end point of the last segment
		# (at least for cC)

		if len(numbers) %2 != 0:
			raise Exception('odd number of numbers is not accepted')
		idx = 0
		currentReference = self.m_start
		ret = []
		while idx < len(numbers):
			p = Point(numbers[idx], numbers[idx+1])
			if self.m_isRelative:
				p = currentReference + p
			ret.append(p)
			if idx % 4 == 2:
				# we just added a 3rd point, i.e. this is our new reference point
				currentReference = p
			idx = idx + 2
		return ret


	def asPartPathCollection(self):
		ret = []
		ii = 0
		start = self.m_start
		points = self.m_points
		while ii < len(points):
			stop = points[ii+1]
			handle = points[ii]
			#handle2 = points[ii+1]
			#if handle.isSameAs(handle2) and (handle1.isSameAs(start) or handle1.isSameAs(stop)):
			#	# i am degenerated to a straight line
			#	seg = ZLineSegment(start, stop)
			#else:
			seg = ZBezier2Segment(start, stop, handle)
			ret.append(seg)
			start = stop
			ii = ii + 2
		return ret


#################################################
#################################################


class SvgCommandBezierT(SvgCommandBezier):
	#def __init__(self, cmdString):
	#	super().__init__(cmdString)
	def checkArguments(self):
		return True


##########################################
##########################################


class SvgCommandLine(SvgCommand):
	def __init__(self, cmdString):
		super().__init__(cmdString)
		self.m_start = None
		self.m_stop = None


	def acceptNumbers(self, numbers):
		points = self.acceptPointsFrom(numbers)
		self.m_stop = points[0]
		return self.m_stop


	def checkArguments(self):
		return self.m_stop is not None


	def getDefaultFollowerName(self, numOfArgs):
		if numOfArgs == 2:
			return self.commandFor('L')
		return None


	def asPartPathCollection(self):
		return [ZLineSegment(self.m_start, self.m_stop)]


##############################################
##############################################


class SvgCommandHorizontal(SvgCommand):
	def __init__(self, cmdString):
		super().__init__(cmdString)
		self.m_start = None
		self.m_stop = None


	def checkArguments(self):
		return True


	def getDefaultFollowerName(self, numOfArgs):
		if numOfArgs == 1:
			return self.commandFor('L')
		return None


	def acceptNumbers(self, numbers):
		num = numbers[0]
		start = self.m_start
		if self.m_isRelative:
			self.m_stop = Point(start.m_x + num, start.m_y)
		else:
			self.m_stop = Point(num, start.m_y)
		return self.m_stop


	def asPartPathCollection(self):
		return [ZLineSegment(self.m_start, self.m_stop)]


########################################################
########################################################


class SvgCommandVertical(SvgCommand):
	def __init__(self, cmdString):
		super().__init__(cmdString)
		self.m_start = None
		self.m_stop = None


	def getDefaultFollowerName(self, numOfArgs):
		if numOfArgs == 1:
			return self.commandFor('L')
		return None


	def checkArguments(self):
		return True


	def acceptNumbers(self, numbers):
		num = numbers[0]
		start = self.m_start
		if self.m_isRelative:
			self.m_stop = Point(start.m_x , start.m_y + num)
		else:
			self.m_stop = Point(start.m_x, num)
		return self.m_stop


	def asPartPathCollection(self):
		return [ZLineSegment(self.m_start, self.m_stop)]


##########################################
##########################################


class SvgCommandArc(SvgCommand):
	def __init__(self, cmdString):
		super().__init__(cmdString)
		self.m_rx = math.nan
		self.m_ry = math.nan
		self.m_xAngle = math.nan
		self.m_largeArcFlag = None
		self.m_sweepFlag = None
		self.m_stop = None


	def checkArguments(self):
		return True


	def acceptNumbers(self, numbers):
		self.m_rx = numbers[0]
		self.m_ry = numbers[1]
		self.m_xAngle = numbers[2]
		self.m_largeArcFlag = (numbers[3] > 0)
		self.m_sweepFlag = (numbers[4] > 0)
		s = Point(numbers[5], numbers[6])
		if self.m_isRelative:
			s = s + self.m_start
		self.m_stop = s
		return self.m_stop


	def asPartPathCollection(self):
		#ret = ZArcSegment(self.m_rx, self.m_ry, self.m_xAngle, self.m_start, self.m_stop, self.m_largeArcFlag, self.m_sweepFlag)
		ret = ZArcSegment.createZArcFromSvg(self.m_rx, self.m_ry, self.m_xAngle, self.m_start, self.m_stop, self.m_largeArcFlag, self.m_sweepFlag)
		return [ret]
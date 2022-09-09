"""
	Helper script to create a qt i18n .ts file from a simple description file.
	Syntax example:
	Some.Symbol: nls text
	TT: detailed text

	the TT line is not needed, but when given, the line is expanded to:
	Some.SymbolTT: detailed text
	(using the last used given symbol)
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

#############################################################


def addXmlNode(defLine, parent):
	global lastKey
	defLine = defLine.strip()
	if defLine == '':
		return
	if defLine[0] == '#':
		return
	idx = defLine.find(':')
	if idx < 0:
		print(f'suspicious line: {defLine}')
		return
	key = defLine[0:idx]
	val = (defLine[(idx+1):]).strip()
	if key == 'TT':
		key = lastKey + 'TT'
	messageNode = ET.SubElement(parent, 'message')
	srcNode = ET.SubElement(messageNode, 'source')
	srcNode.text = key
	trNode = ET.SubElement(messageNode, 'translation')
	lastKey = key
	trNode.text = val


################################################################
#	main program

# read the input parameters:
inFile = sys.argv[1]
outFile = sys.argv[2]


rootNode = ET.Element('TS')
contextNode = ET.SubElement(rootNode, 'context')
nameNode = ET.SubElement(contextNode, 'name')
nameNode.text = 'QApplication'

lastKey = ''

with open(inFile, 'r', encoding='utf-8') as fIn:
	for line in fIn:
		addXmlNode(line, contextNode)

# transform xml node to a nice string
rough_string = ET.tostring(rootNode, 'utf-8')
reparsed = minidom.parseString(rough_string)
nice = reparsed.toprettyxml(indent="	", newl='\n')
nice = nice.replace('<?xml version="1.0" ?>', '<!DOCTYPE TS>')

# output the nice string to xml file
with  open(outFile, "w", encoding='utf-8') as fOut:
	fOut.write(nice)




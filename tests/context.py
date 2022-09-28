import os
import sys


zutilsFolder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

#testsFolder = os.path.abspath
testOutFolder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test-out'))
if not os.path.exists(testOutFolder):
	os.mkdir(testOutFolder)
	
testInFolder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test-in'))
if not os.path.exists(testInFolder):
	raise Exception('folder with test input does not exist: ' + testInFolder)

#print(zutilsFolder)
folderAbove = os.path.abspath(os.path.join(zutilsFolder, '..'))
#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, folderAbove)

#print(sys.path)

import zutils
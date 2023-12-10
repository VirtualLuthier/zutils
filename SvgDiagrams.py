#	Create some svg diagrams describing svg segments


from zutils.ZGeom import Point
from zutils.SvgPatcher import SvgWriter
from zutils.SvgReader import SvgPathReader


################################################################
################################################################

global writer

def createPath(dAttribute):
	return SvgPathReader.classParsePath(dAttribute)


def createSvgWriter(nameRoot, path):
	global writer
	factor = 0.2
	fName = '/d/python/zutils/diagrams/' + nameRoot
	writer = SvgWriter('mm', targetFile=fName)
	box = path.getSimpleBoundingBox()
	w = box.getWidthX()	# * (1 + 2*factor)
	h = box.getHeightY()	# * (1 + 2*factor)
	writer.setSize(w, h, left=box.m_origin.m_x, top=box.m_origin.m_y, addFactor=0.2)
	#writer.setSize(w*(1 + 2*factor), h*(1 + 2*factor), left=box.m_origin.m_x - factor*w, top=box.m_origin.m_y - factor*h)
	return writer



def createSvgPoint(point, text, offset=None):
	global writer
	r = 1.5
	l = point.m_x - r
	t = point.m_y - r
	w = 2 * r
	myOffset = Point(3*r)
	if offset is not None:
		myOffset = offset
	writer.addRect(None, l, t, w, w)
	writer.addText(None, text, point, offset=myOffset, fontSize='0.5em')


def createSvgLineThin(p1, p2):
	global writer
	writer.addLine(None, p1, p2, strokeWidth=0.5, strokeColor='blue')


######


def createBezier3Diagram():
	global writer
	dAttribute = 'M 0 100 C 0 0 80 0 100 90'
	path = createPath(dAttribute)

	writer = createSvgWriter('bezier3.svg', path)
	writer.addPath(None, path)

	seg = path.m_segments[0]
	createSvgPoint(seg.m_start, 'p1')
	createSvgPoint(seg.m_stop, 'p2')
	createSvgPoint(seg.m_handleStart, 'h1')
	createSvgPoint(seg.m_handleStop, 'h2')

	createSvgLineThin(seg.m_start, seg.m_handleStart)
	createSvgLineThin(seg.m_stop, seg.m_handleStop)

	writer.write()


def createBezier2Diagram():
	global writer
	dAttribute = 'M 0 100 Q 50 0 100 90'
	path = createPath(dAttribute)

	writer = createSvgWriter('bezier2.svg', path)
	writer.addPath(None, path)

	seg = path.m_segments[0]
	createSvgPoint(seg.m_start, 'p1')
	createSvgPoint(seg.m_stop, 'p2')
	createSvgPoint(seg.m_handle, 'h')

	createSvgLineThin(seg.m_start, seg.m_handle)
	createSvgLineThin(seg.m_stop, seg.m_handle)

	writer.write()
	
	
def createArcDiagram():
	global writer
	dAttribute = 'M 50 100 A 60 40 30 0 0 0 50'
	path = createPath(dAttribute)
	#path.printComment('the ellipse')

	writer = createSvgWriter('arc.svg', path)
	writer.addPath(None, path)
	seg = path.m_segments[0]
	createSvgPoint(seg.m_start, 'p1')
	createSvgPoint(seg.m_stop, 'p2')
	createSvgPoint(seg.m_center, 'c')
	createSvgPoint(seg.m_ellipse.m_vert1, 'd1')
	createSvgPoint(seg.m_ellipse.m_vert2, 'd2')

	#path2 = createPath(dAttribute)
	writer.addEllipse(None, seg.m_ellipse, seg.getXAngle(), strokeWidth=0.3, stroke='gray', fill='none')
	createSvgLineThin(seg.m_center, seg.m_ellipse.m_vert1)
	createSvgLineThin(seg.m_center, seg.m_ellipse.m_vert2)

	writer.write()


def createOsculatingCircle():
	global writer
	dAttribute = 'M 0 70 Q 50 -20 100 60'
	path = createPath(dAttribute)

	writer = createSvgWriter('osculating.svg', path)
	writer.addPath(None, path)

	seg = path.m_segments[0]
	#createSvgPoint(seg.m_start, 'p1')
	#createSvgPoint(seg.m_stop, 'p2')

	seg = path.m_segments[0]
	param = 0.6
	p = seg.pointAtParam(param)
	createSvgPoint(p, 'p')

	circle = seg.getOscilatingCircleAtParam(param)
	writer.addCircle(None, circle, strokeWidth=0.5)
	center = circle.m_center
	createSvgPoint(center, 'c')

	createSvgLineThin(center, p)
	middle = (center + p).scaledBy(0.5)
	writer.addText(None, 'r', middle, offset=Point(0, 5), fontSize='0.5em')

	writer.write()



def createLineSegment():
	global writer
	dAttribute = 'M 20 70 L 100 40'
	path = createPath(dAttribute)

	writer = createSvgWriter('line.svg', path)
	writer.addPath(None, path)

	seg = path.m_segments[0]
	createSvgPoint(seg.m_start, 'p1', offset=Point(3, 8))
	createSvgPoint(seg.m_stop, 'p2')

	writer.write()



################################################


if __name__ == '__main__':
	createLineSegment()
	createOsculatingCircle()
	createArcDiagram()
	createBezier3Diagram()
	createBezier2Diagram()
	

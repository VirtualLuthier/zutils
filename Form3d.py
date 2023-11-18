"""
	Contains one class of 3d bodies (Form3d), that are delimited by surfaces:
	- Form3d
	- SurfaceAbstract
	- SurfacePolygon
	- SurfacePathExtrusion
	- SurfaceBezierCubic
	- SurfacePath
"""
import math
#import pybind
from zutils.ZGeom 	import Point


#################################################################
#################################################################


class Form3d:
	"""
		Describes a body that is delimited by a list of Surfaces
	"""
	def __init__(self, massCenter=None):
		self.m_massCenter = massCenter
		self.m_surfaces = []


	def addSurface(self, surface):
		if self.m_massCenter is not None:
			surface.m_massCenter = self.m_massCenter
		self.m_surfaces.append(surface)


	def isCornerClosed(self):
		"""
			is each of my corner points contained (as a corner point) in at least 3 surfaces ?
			Makes no real sense
		"""
		for surface in self.m_surfaces:
			corners = surface.cornerPoints()
			for corner in corners:
				num = 0
				for surface2 in self.m_surfaces:
					if surface2.hasCorner(corner):
						num += 1
				if num < 3:
					print('has point with problem: ' + surface.m_name + ' (' + str(corner) + ')')
					return False
		return True


	def copy(self):
		ret = Form3d()
		for surface in self.m_surfaces:
			ret.addSurface(surface.copy())


	def transformBy(self, aff):
		for surface in self.m_surfaces:
			surface.transformBy(aff)



#############################################################
#############################################################


class SurfaceAbstract:
	"""
		The superclass for all the surfaces in this file
	"""
	def __init__(self, name):
		self.m_name = name
		self.m_isComplanar = None
		self.m_containingPlane = None
		self.m_isHidden = False
		self.m_massCenter = None

	
	def isComplanar(self):
		if self.m_isComplanar is not None:
			self.m_isComplanar = self.__isComplanar()
		return self.m_isComplanar


	def hasCorner(self, point):
		corners = self.cornerPoints()
		return point in corners


	def raiseException(self, msg):
		raise Exception(msg + ' in class: ' + self.__class__.__name__)


	def __isComplanar(self):
		self.raiseException('not implemented: __isComplanar()')
		return False


	def cornerPoints(self):
		self.raiseException('not implemented: cornerPoints()')
		return []


	def isClosed(self):
		self.raiseException('not implemented: isClosed()')
		return False


	def allFaces(self, _):
		"""
			Called from the OSCForm3d
		"""
		self.raiseException('not implemented: allFaces()')
		return []


##############################################################
##############################################################


class SurfacePolygon(SurfaceAbstract):
	"""
		Describes a polygone in D3
	"""
	def __init__(self, name, polygon):
		super().__init__(name)
		self.m_polygon = polygon


	def isComplanar(self):
		self.m_containingPlane = self.m_polygon.containingPlane()
		self.m_isComplanar = self.m_containingPlane is not None


	def cornerPoints(self):
		return self.m_polygon.m_points


	def isClosed(self):
		# a polygon can always be regarded as closed
		return True


	def allFaces(self, _):
		return [self.m_polygon.m_points]


	def copy(self):
		poly = [p.copy() for p in self.m_polygon]
		return SurfacePolygon(self.m_name, poly)


	def transformBy(self, aff):
		self.m_polygon = [aff * p for p in self.m_polygon]




###############################################################
###############################################################


class SurfacePathExtrusion(SurfaceAbstract):
	"""
		I hold 2 paths. Respective points are connected
		Makes only sense, if the both paths are 'similar'
	"""
	def __init__(self, name, path1, path2):
		super().__init__(name)
		self.m_path1 = path1
		self.m_path2 = path2


	def isClosed(self):
		# ask my paths
		return self.m_path1.isClosed() and self.m_path2.isClosed()


	def allFaces(self, quality):
		diff = 1.0 / int(quality)
		p1 = self.m_path1.getInterPoints(diff)
		p2 = self.m_path2.getInterPoints(diff)
		if len(p1) != len(p2):
			raise Exception('SurfacePathExtrusion: cannot calculate faces')
		if self.isClosed() and p1[-1].isSameAs(p1[0]):
			p1.pop()
			p2.pop()

		ret = []
		l = len(p1)
		for ii in range(l - 2):
			ret.append([p1[ii], p1[ii+1], p2[ii+1], p2[ii]])
		if self.isClosed():
			ret.append([p1[l-1], p1[0], p2[0], p2[l-1]])
		return ret


	def copy(self):
		p1 = self.m_path1.copy()
		p2 = self.m_path2.copy()
		return SurfacePathExtrusion(self.m_name, p1, p2)


	def transformBy(self, aff):
		self.m_path1.transformBy(aff)
		self.m_path2.transformBy(aff)


###################################################################
###################################################################


class SurfaceBezierCubic(SurfaceAbstract):
	"""
		Implements a Bezier Surface spanned up by 4x4 control points. We assume the same number of steps in u and v
	"""
	s_bernsteinSurfaceCoefficients = dict()


	def __init__(self, name, controlPoints):
		super().__init__(name)
		self.m_controlPoints = controlPoints


	@classmethod
	def getBernsteinSurfaceCoefficients(cls, numberOfStepsU, numberOfStepsV=math.nan):
		"""
			Return the Bernstein coefficients (in u and v) for this numberOfSteps. If neccessary, creates them.
			We assume the same number of steps in u and v
		"""
		if math.isnan(numberOfStepsV):
			numberOfStepsV = numberOfStepsU
		if (numberOfStepsU, numberOfStepsV) in cls.s_bernsteinSurfaceCoefficients:
			return cls.s_bernsteinSurfaceCoefficients[(numberOfStepsU, numberOfStepsV)]	#, cls.s_bernsteinDerivationsOne[numberOfSteps]]

		diff = 1.0 / numberOfStepsU
		paramsU = []
		for uIdx in range(numberOfStepsU+1):
			paramsU.append(uIdx * diff)
		if math.isnan(numberOfStepsV):
			paramsV = paramsU
		else:
			paramsV = []
			diff = 1.0 / numberOfStepsV
			for vIdx in range(numberOfStepsV+1):
				paramsV.append(vIdx * diff)

		coeffsOfSurface = []

		for uIdx in range(numberOfStepsU+1):
			# iterate over u
			u = paramsU[uIdx]
			listU = []
			coeffsOfSurface.append(listU)
			for vIdx in range(numberOfStepsV+1):
				# iterate over v:
				v = paramsV[vIdx]
				listU.append(cls.bernsteinSurfaceCoefficientsForUV(u, v))

		cls.s_bernsteinSurfaceCoefficients[(numberOfStepsU, numberOfStepsV)] = coeffsOfSurface
		
		return coeffsOfSurface


	@classmethod
	def bernsteinSurfaceCoefficientsForUV(cls, u, v):
		ret = []
		for ii in range(4):
			for jj in range(4):
				ret.append(cls.bernsteinSurfaceCoefficient(ii, jj, u, v))
		return ret


	@classmethod
	def bernsteinSurfaceCoefficient(cls, ii, jj, u, v):
		"""
			See https://en.wikipedia.org/wiki/B%C3%A9zier_surface
		"""
		biu = cls.bernsteinCurveCoefficient(ii, u)
		bjv = cls.bernsteinCurveCoefficient(jj, v)
		return biu * bjv


	@classmethod
	def bernsteinCurveCoefficient(cls, ii, u):
		"""
			See https://en.wikipedia.org/wiki/B%C3%A9zier_surface
		"""
		#	return math.comb(3, ii) * (u ** ii) * ((1-u) ** (3 - ii)), for speed use other formulae
		if ii == 3:
			return u ** 3
		u2 = 1.0 - u
		if ii == 0:
			return u2 ** 3
		if ii == 1:
			return 3 * u  * (u2 ** 2)
		return 3 * (u ** 2) * u2


	def getDerivationU(self, u, v):
		"""
			Returns the vector for partial derivation in u direction
		"""
		coeffs = []
		for ii in range(4):
			derivII = self.bernsteinCurveDerivationCoefficient(ii, u)
			for jj in range(4):
				curveJJ = self.bernsteinCurveCoefficient(jj, v)
				coeffs.append(derivII * curveJJ)
		#self.checkBernsteinSet(coeffs)		does not work (may be zero)
		return self.getPointCombination(coeffs)


	def getDerivationV(self, u, v):
		"""
			Returns the vector for partial derivation in v direction
		"""
		coeffs = []
		for ii in range(4):
			derivII = self.bernsteinCurveCoefficient(ii, u)
			for jj in range(4):
				curveJJ = self.bernsteinCurveDerivationCoefficient(jj, v)
				coeffs.append(derivII * curveJJ)
		return self.getPointCombination(coeffs)


	def getSurfaceNormal(self, u, v):
		"""
			Return the unit vector of the surface normale fpr parameters u, v
		"""
		derU = self.getDerivationU(u, v)
		derV = self.getDerivationV(u, v)
		normal = derU.crossProduct(derV)
		return normal.unit()


	@classmethod
	def bernsteinCurveDerivationCoefficient(cls, ii, u):
		"""
			See https://www.gamasutra.com/view/feature/3441/tessellation_of_4x4_bezier_patches_.php?print=1
		"""
		if ii == 3:
			return 3 * (u ** 2)
		u2 = 1.0 - u
		if ii == 0:
			return -3 * (u2 ** 2)
		if ii == 1:
			return 3 * (u2 ** 2) - 6 * u * u2
		return 6 * u * u2 - 3 * (u ** 2)


	@classmethod
	def checkBernsteinCoefficients(cls):
		for quality, coeffs in cls.s_bernsteinSurfaceCoefficients.items():
			#coeffs = cls.s_bernsteinSurfaceCoefficients[quality]
			for uIdx in range(quality[0]+1):
				for vIdx in range(quality[1]+1):
					theList = coeffs[uIdx][vIdx]
					cls.checkBernsteinSet(theList)


	@classmethod
	def checkBernsteinSet(cls, theList):
		"""
			check, if the bernstein set sums up to 1
		"""
		theSum = sum(theList)
		if theSum < 0.999 or theSum > 1.001:
			raise Exception('Illegal sum of bernstein coefficients: ' + str(theSum))


	def allFaces(self, quality):
		coeffsAll = self.getBernsteinSurfaceCoefficients(quality)
		allPoints = []

		# first calculate all the points:
		for ii in range(quality+1):
			uPoints = []
			allPoints.append(uPoints)
			for jj in range(quality + 1):
				coeffsUV = coeffsAll[ii][jj]
				uPoints.append(self.getPointCombination(coeffsUV))

		# now make the faces:
		ret = []
		pList1 = allPoints[0]
		for ii in range(1, quality+1):
			# iterate over u
			pList2 = allPoints[ii]
			for jj in range(quality):
				# iterate over v:
				p11 = pList1[jj]
				p12 = pList1[jj+1]
				p21 = pList2[jj+1]
				p22 = pList2[jj]
				ret.append([p11, p12, p21, p22])
			pList1 = pList2

		return ret


	def getPointForUV(self, u, v):
		"""
			Return the suface point for the given parameters u and v
		"""
		coeffs = self.bernsteinSurfaceCoefficientsForUV(u, v)
		return self.getPointCombination(coeffs)


	def getPointCombination(self, coeffs):
		"""
			Return the bezier linear combination of my control points with the given weights
		"""
		ret = Point()
		ii = 0
		for p in self.m_controlPoints:
			ret += p.scaledBy(coeffs[ii])
			ii += 1
		return ret


	def copy(self):
		cp = [p.copy for p in self.m_controlPoints]
		return SurfaceBezierCubic(self.m_name, cp)


	def transformBy(self, aff):
		self.m_controlPoints = [aff * p for p in self.m_controlPoints]


##################################################################
##################################################################


class SurfacePath(SurfaceAbstract):
	"""
		Makes one face from the path (possibly obsolete)
	"""
	def __init__(self, name, path, numPartsFactor):
		super().__init__(name)
		self.m_numPartsFactor = numPartsFactor
		self.m_path = path


	def allFaces(self, quality):
		diff = float(self.m_numPartsFactor) / int(quality)
		ps = self.m_path.getInterPoints(diff)
		return [ps]


	def copy(self):
		return SurfacePath(self.m_name, self.m_path.copy(), self.m_numPartsFactor)


	def transformBy(self, aff):
		self.m_path.transformBy(aff)

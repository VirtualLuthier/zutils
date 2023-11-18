"""
	Contains only the class with the same name
"""


class GMaterial:
	"""
		Collects names and colors of the mostly used materials (for the UI)
	"""
	s_allMaterials = dict()

	def __init__(self, name, color):
		self.m_name = name
		self.m_color = color
		GMaterial.addMaterial(self)


	@classmethod
	def addMaterial(cls, material):
		cls.s_allMaterials[material.m_name] = material


	@classmethod
	def getMaterialNamed(cls, name):
		cls.initialize()
		return cls.s_allMaterials.get(name, None)

	@classmethod
	def initialize(cls):
		"""
			see also https://en.wikipedia.org/wiki/File:SVG_Recognized_color_keyword_names.svg
		"""
		if len(cls.s_allMaterials) > 0:
			return

		#	wood:
		GMaterial('Ash','brown')
		GMaterial('Birch', [0.9, 0.8, 0.6])	
		GMaterial('Cedar','yellow')
		GMaterial('Ebony','black')
		GMaterial('Mahogany','red')
		GMaterial('Maple', 'white')
		GMaterial('Oak', [0.65, 0.5, 0.4])
		GMaterial('Pine', [0.85, 0.7, 0.45])
		GMaterial('Rosewood', 'maroon')
		GMaterial('Spruce','white')

		#	metal:
		GMaterial('Aluminum', [0.77, 0.77, 0.8])
		GMaterial('Brass', [0.88, 0.78, 0.5])
		GMaterial('Iron', [0.36, 0.33, 0.33])
		GMaterial('Stainless', [0.45, 0.43, 0.5])
		GMaterial('Steel', [0.65, 0.67, 0.72])

		#	other:
		GMaterial('BlackPaint', [0.2, 0.2, 0.2])
		GMaterial('Bone', 'white')
		GMaterial('CarbonFiber', 'gray')
		GMaterial('FiberBoard', [0.7, 0.67, 0.6])
		GMaterial('PlasticWhite', 'white')
		GMaterial('Transparent', [1, 1, 1, 0.2])
		
		


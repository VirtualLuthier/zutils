"""
	Contains the class ZUnits (support for mm, kg, inch, lb, N).
	Only class methods provided. Set ZUnits.s_isMetric at program start.
	Subsequent calls refer this class variable
	Or use ZGeom.adaptForInches(inchFlag)
"""

###########################################
###########################################


class ZUnits:
	"""
		Support for the conversion of m, mm, inch, kg, lb, N
	"""

	s_isMetric = True			# per default we assume the metric system, if set to False, we assume lb and inch (only for specific weight: foot)

	# the following factors are exact
	s_inToM = 0.0254			#	inch to meter
	s_lbToKg = 0.45359237		#	lb to kg
	s_ftToM = 0.3048			#	feet to meter

	# not exact:
	s_kgToN = 9.80665			#	kg to Newton (=g)

########

	@classmethod
	def svgLengthUnitString(cls):
		return 'mm' if cls.s_isMetric else 'in'


	@classmethod
	def changeMmToMmOrInch(cls, mm):
		"""
			Return the length (given in mm) in mm resp. in inch (depending on s_isMetric)
		"""
		if cls.s_isMetric:
			return mm
		# return the mm in inch
		return (mm / cls.s_inToM) / 1000.0

########### the variable input converters (depending on s_isMetric)

	@classmethod
	def changeLengthToMeter(cls, mmOrIn):
		"""
			Input must be mm (if s_isMetric) or in
		"""
		if cls.s_isMetric:			
			return mmOrIn / 1000.0	# change from mm to m
		return cls.changeInchToMeter(mmOrIn)


	@classmethod
	def changeWeightToKg(cls, gramOrLb):
		"""
			Use gram or lb as input, depending on is_metric
		"""
		if cls.s_isMetric:
			return gramOrLb / 1000.0
		return cls.changeLbToKg(gramOrLb)


	@classmethod
	def changeSpecificWeightToKgPerMeterCubic(cls, kgPerMeterCubicOrLbPerFootCubic):
		"""
			argument must be (kg per cubic meter) or (lb per cubic foot), depending on s_isMetric
		"""
		if cls.s_isMetric:
			return kgPerMeterCubicOrLbPerFootCubic
		return cls.changeLbPerF3ToKgPerMeterCubic(kgPerMeterCubicOrLbPerFootCubic)


############## special conversions to metric:

	@classmethod
	def changeKgToN(cls, kg):
		return kg * cls.s_kgToN

	@classmethod
	def changeNToKg(cls, newton):
		return newton / cls.s_kgToN


	@classmethod
	def changeInchToMeter(cls, inches):
		return inches * cls.s_inToM


	@classmethod
	def changeKgPerMmSquareToPa(cls, kgPerMMSquare):
		return kgPerMMSquare * cls.s_kgToN * 1e6


	@classmethod
	def changeLbToKg(cls, lb):
		return lb * cls.s_lbToKg


	@classmethod
	def changeLbPerF3ToKgPerMeterCubic(cls, lbPerF3):
		return lbPerF3 * cls.s_lbToKg / (cls.s_ftToM * cls.s_ftToM * cls.s_ftToM)


################ special conversions to imperial:

	@classmethod
	def changeMToInch(cls, m):
		return m / cls.s_inToM


	@classmethod
	def changeKgToLb(cls, kg):
		return kg / cls.s_lbToKg


	@classmethod
	def changeNToLb(cls, newton):
		return cls.changeKgToLb(cls.changeNToKg(newton))


	@classmethod
	def changeKgPerM3ToLbPerF3(cls, kgPerM3):
		iTm = cls.s_inToM
		return kgPerM3 * iTm * iTm * iTm / cls.s_lbToKg * (12*12*12)


	@classmethod
	def changeM2ToInch2(cls, m2):
		return (m2 / cls.s_inToM) / cls.s_inToM


################### dumping:

	@classmethod
	def dumpSpecificWeight(cls, comment, specWeightSI):
		print(f'{comment} {str(specWeightSI / 1000)} kg/dm^3')
		specWeightImp = cls.changeKgPerM3ToLbPerF3(specWeightSI)
		print(f'{comment} {str(specWeightImp)} lb/ft^3')


	@classmethod
	def dumpLength(cls, comment, lengthSI):
		print(f'{comment} {str(lengthSI * 1000)} mm')
		lengthImp = cls.changeMToInch(lengthSI)
		print(f'{comment} {str(lengthImp)} in')


	@classmethod
	def dumpArea(cls, comment, areaSI):
		print(f'{comment} {str(areaSI * 1e6)} mm^2')
		areaImp = cls.changeM2ToInch2(areaSI)
		print(f'{comment} {str(areaImp)} in^2')


	@classmethod
	def dumpForce(cls, comment, forceSI):
		print(f'{comment} {str(forceSI)} N')
		forceKg = cls.changeNToKg(forceSI)
		print(f'{comment} {str(forceKg)} kg')
		forceImp = cls.changeNToLb(forceSI)
		print(f'{comment} {str(forceImp)} lb')


	@classmethod

	def dumpPressure(cls, comment, forceSI, areaSI):
		"""
			Display pascal in N/mm^2 and lb/in^2
		"""
		pressureSI = forceSI / areaSI
		print(f'{comment} {str(pressureSI / 1e6)} N/mm^2')
		forceImp = cls.changeNToLb(forceSI)
		areaImp = cls.changeM2ToInch2(areaSI)
		pressureImp = forceImp / areaImp
		print(f'{comment} {str(pressureImp)} lb/in^2')
		#forceKg = cls.changeNToKg(forceSI)
		#print(comment + str(forceKg) + ' kg')
		#forceImp = cls.changeNToLb(forceSI)
		#print(comment + str(forceImp) + ' lb')


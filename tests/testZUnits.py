"""
	Code for unit testing the class ZUnits
"""



import unittest


from context import zutils, testInFolder, testOutFolder

from zutils.ZUnits import ZUnits


#########################################################
#########################################################


class TestZUnits(unittest.TestCase):


	def test_ZPysics(self):
		ZUnits.s_isMetric = False

		# pound to kilo
		kilos = ZUnits.changeWeightToKg(1)
		self.assertAlmostEqual(kilos, 0.45359237)

		# specific weight of water:
		swImperial = 62.42
		swSI = ZUnits.changeSpecificWeightToKgPerMeterCubic(swImperial)
		self.assertTrue(abs(swSI - 1000) < 0.2)
		ZUnits.s_isMetric = True


	def test_metricToImperial0(self):
		ZUnits.s_isMetric = False

		length = 1
		lengthImp = ZUnits.changeMToInch(length)
		length2 = ZUnits.changeLengthToMeter(lengthImp)
		self.assertAlmostEqual(length, length2)

		weightKg = 1000
		weightImp = ZUnits.changeKgToLb(weightKg)
		weight2 = ZUnits.changeWeightToKg(weightImp)
		self.assertAlmostEqual(weightKg, weight2)

		weightKg = 1
		weightLbCalculated = ZUnits.changeKgToLb(weightKg)
		weightLbWanted = 2.20462262185
		self.assertAlmostEqual(weightLbCalculated, weightLbWanted)
		weightKgCalculated = ZUnits.changeLbToKg(weightLbWanted)
		self.assertAlmostEqual(weightKgCalculated, 1)

		specWeightSI = 1000		# water
		specWeightImp = ZUnits.changeKgPerM3ToLbPerF3(specWeightSI)
		specWeight2 = ZUnits.changeSpecificWeightToKgPerMeterCubic(specWeightImp)
		self.assertAlmostEqual(specWeightSI, specWeight2)


	def test_metricToImperial1(self):
		ZUnits.s_isMetric = False
		length = 1
		lengthImp = ZUnits.changeMToInch(length)
		length2 = ZUnits.changeLengthToMeter(lengthImp)
		self.assertAlmostEqual(length, length2)

		weightKg = 1000
		weightImp = ZUnits.changeKgToLb(weightKg)
		weight2 = ZUnits.changeWeightToKg(weightImp)
		self.assertAlmostEqual(weightKg, weight2)

		specWeightSI = 1000		# water
		specWeightImp = ZUnits.changeKgPerM3ToLbPerF3(specWeightSI)
		specWeight2 = ZUnits.changeSpecificWeightToKgPerMeterCubic(specWeightImp)
		self.assertAlmostEqual(specWeightSI, specWeight2)


	def test_metricToImperial2(self):
		ZUnits.s_isMetric = False

		lengthImp = 1
		length2 = ZUnits.changeLengthToMeter(lengthImp)
		self.assertAlmostEqual(length2, 0.0254)

		wImp = 1
		wM = ZUnits.changeWeightToKg(wImp)
		self.assertAlmostEqual(wM, 0.45359237)


################################################
################################################


if __name__ == '__main__':
    unittest.main(verbosity=1)

print('----------------------------------')
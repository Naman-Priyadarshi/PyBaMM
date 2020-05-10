#
# Test for the Units class
#
import pybamm
import unittest


class TestUnits(unittest.TestCase):
    def test_unit_init(self):
        speed_str = pybamm.Units("[m.s-1]")
        speed_dict = pybamm.Units({"m": 1, "s": -1})
        self.assertEqual(speed_str.units_dict, {"m": 1, "s": -1})
        self.assertEqual(speed_dict.units_str, "[m.s-1]")

        # non-float units string
        diff_str = pybamm.Units("[m2.0.s-1.0]")
        self.assertEqual(diff_str.units_dict, {"m": 2, "s": -1})

        # empty units
        no_units = pybamm.Units(None)
        self.assertEqual(no_units.units_dict, {})
        self.assertEqual(no_units.units_str, "[-]")

        # errors
        with self.assertRaisesRegex(pybamm.UnitsError, "not recognized"):
            pybamm.Units("[notaunit]")
        with self.assertRaisesRegex(pybamm.UnitsError, "Units should start with"):
            pybamm.Units("m.s-1")

    def test_equality(self):
        self.assertTrue(pybamm.Units("[m.A.s-1]") == pybamm.Units("[A.m.s-1]"))
        self.assertFalse(pybamm.Units("[m.A.s-1]") == pybamm.Units("[A]"))

    def test_units_operations(self):
        speed = pybamm.Units("[m.s-1]")
        conc = pybamm.Units("[mol.m-3]")

        speed_sum = speed + speed
        self.assertEqual(speed_sum.units_str, "[m.s-1]")
        with self.assertRaisesRegex(pybamm.UnitsError, "Cannot add"):
            speed + conc

        speed_diff = speed - speed
        self.assertEqual(speed_diff.units_str, "[m.s-1]")
        with self.assertRaisesRegex(pybamm.UnitsError, "Cannot subtract"):
            speed - conc

        speed_times_conc = speed * conc
        self.assertEqual(speed_times_conc.units_dict, {"m": -2, "mol": 1, "s": -1})

        speed_over_conc = speed / conc
        self.assertEqual(speed_over_conc.units_dict, {"m": 4, "mol": -1, "s": -1})

        conc_over_speed = conc / speed
        self.assertEqual(conc_over_speed.units_dict, {"m": -4, "mol": 1, "s": 1})

        speed_cubed = speed ** 3.5
        self.assertEqual(speed_cubed.units_dict, {"m": 3.5, "s": -3.5})

    def test_reformat_units(self):
        # Test that some special units get recast in terms of other units
        joules = pybamm.Units("[J3]")
        self.assertEqual(joules.units_dict, {"A": 3, "s": 3, "V": 3})

        joules = pybamm.Units("[C]")
        self.assertEqual(joules.units_dict, {"A": 1, "s": 1})

        watts = pybamm.Units("[W-2]")
        self.assertEqual(watts.units_dict, {"A": -2, "V": -2})

        siemens = pybamm.Units("[S2]")
        self.assertEqual(siemens.units_dict, {"V": -2, "A": 2})

        ohms = pybamm.Units("[Ohm2]")
        self.assertEqual(ohms.units_dict, {"A": -2, "V": 2})

        # test combined
        combined = pybamm.Units("[J.C.s.m-1]")
        self.assertEqual(combined.units_dict, {"A": 2, "s": 3, "V": 1, "m": -1})

    def test_symbol_units(self):
        a = pybamm.Symbol("a")
        c = pybamm.Symbol("c", units="[mol.m-3]")
        v = pybamm.Symbol("v", units="[m.s-1]")

        self.assertIsInstance(a.units, pybamm.Units)
        self.assertEqual(str(a.units), "[-]")

        self.assertIsInstance(c.units, pybamm.Units)
        self.assertEqual(str(c.units), "[mol.m-3]")

        self.assertEqual(str((c + c).units), "[mol.m-3]")
        self.assertEqual(str((c - c).units), "[mol.m-3]")
        self.assertEqual(str((c * v).units), "[mol.m-2.s-1]")
        self.assertEqual(str((c / v).units), "[mol.s.m-4]")
        self.assertEqual(str((v / c).units), "[m4.mol-1.s-1]")

    def test_simplify_keeps_units(self):
        # test that simplification retains units
        s = pybamm.Scalar(1, units="[m]")
        self.assertEqual(str((s * 2).units), "[m]")


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    pybamm.settings.debug_mode = True
    unittest.main()

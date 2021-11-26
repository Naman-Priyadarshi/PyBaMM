#
# Base integration tests for lithium-ion models
#
import pybamm
import tests
import numpy as np


class BaseIntegrationTestLithiumIon:
    def run_basic_processing_test(self, options, **kwargs):
        model = self.model(options)
        modeltest = tests.StandardModelTest(model, **kwargs)
        modeltest.test_all()

    def test_basic_processing(self):
        options = {}
        # use Ecker parameters for nonlinear diffusion
        param = pybamm.ParameterValues("Ecker2015")
        self.run_basic_processing_test(options, parameter_values=param)

    def test_sensitivities(self):
        model = self.model()
        param = pybamm.ParameterValues("Ecker2015")
        modeltest = tests.StandardModelTest(model, parameter_values=param)
        modeltest.test_sensitivities(
            "Current function [A]",
            0.15652,
        )

    def test_basic_processing_1plus1D(self):
        options = {"current collector": "potential pair", "dimensionality": 1}
        var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 5, "r_p": 5, "y": 5, "z": 5}
        model = self.model(options)
        modeltest = tests.StandardModelTest(model, var_pts=var_pts)
        modeltest.test_all(skip_output_tests=True)

    def test_basic_processing_2plus1D(self):
        options = {"current collector": "potential pair", "dimensionality": 2}
        var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 5, "r_p": 5, "y": 5, "z": 5}
        model = self.model(options)
        modeltest = tests.StandardModelTest(model, var_pts=var_pts)
        modeltest.test_all(skip_output_tests=True)

    def test_optimisations(self):
        model = self.model()
        optimtest = tests.OptimisationsTest(model)

        original = optimtest.evaluate_model()
        using_known_evals = optimtest.evaluate_model(use_known_evals=True)
        to_python = optimtest.evaluate_model(to_python=True)
        np.testing.assert_array_almost_equal(original, using_known_evals)
        np.testing.assert_array_almost_equal(original, to_python)

        if pybamm.have_jax():
            to_jax = optimtest.evaluate_model(to_jax=True)
            np.testing.assert_array_almost_equal(original, to_jax)

    def test_set_up(self):
        model = self.model()
        optimtest = tests.OptimisationsTest(model)
        optimtest.set_up_model(to_python=True)
        optimtest.set_up_model(to_python=False)

    def test_charge(self):
        options = {"thermal": "isothermal"}
        parameter_values = pybamm.ParameterValues("Marquis2019")
        parameter_values.update({"Current function [A]": -1})
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_zero_current(self):
        options = {"thermal": "isothermal"}
        parameter_values = pybamm.ParameterValues("Marquis2019")
        parameter_values.update({"Current function [A]": 0})
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_lumped_thermal(self):
        options = {"thermal": "lumped"}
        self.run_basic_processing_test(options)

    def test_full_thermal(self):
        options = {"thermal": "x-full"}
        self.run_basic_processing_test(options)

    def test_particle_uniform(self):
        options = {"particle": "uniform profile"}
        self.run_basic_processing_test(options)

    def test_particle_quadratic(self):
        options = {"particle": "quadratic profile"}
        self.run_basic_processing_test(options)

    def test_particle_quartic(self):
        options = {"particle": "quartic profile"}
        self.run_basic_processing_test(options)

    def test_constant_utilisation(self):
        options = {"interface utilisation": "constant"}
        parameter_values = pybamm.ParameterValues(
            chemistry=pybamm.parameter_sets.Marquis2019
        )
        parameter_values.update(
            {
                "Initial negative electrode interface utilisation": 0.9,
                "Initial positive electrode interface utilisation": 0.8,
            },
            check_already_exists=False,
        )
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_current_driven_utilisation(self):
        options = {"interface utilisation": "current-driven"}
        parameter_values = pybamm.ParameterValues(
            chemistry=pybamm.parameter_sets.Marquis2019
        )
        parameter_values.update(
            {
                "Initial negative electrode interface utilisation": 0.9,
                "Initial positive electrode interface utilisation": 0.8,
                "Negative electrode current-driven interface utilisation factor "
                "[m3.mol-1]": -1e-5,
                "Positive electrode current-driven interface utilisation factor "
                "[m3.mol-1]": 1e-5,
            },
            check_already_exists=False,
        )
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_loss_active_material_reaction_both(self):
        options = {"loss of active material": "reaction-driven"}
        self.run_basic_processing_test(options)

    def test_surface_form_differential(self):
        options = {"surface form": "differential"}
        self.run_basic_processing_test(options)

    def test_surface_form_algebraic(self):
        options = {"surface form": "algebraic"}
        self.run_basic_processing_test(options)

    def test_irreversible_plating_with_porosity(self):
        options = {
            "lithium plating": "irreversible",
            "lithium plating porosity change": "true",
        }
        param = pybamm.ParameterValues("Chen2020_plating")
        self.run_basic_processing_test(options, parameter_values=param)

    def test_reaction_limited(self):
        options = {"SEI": "reaction limited"}
        self.run_basic_processing_test(options)

    def test_solvent_diffusion_limited(self):
        options = {"SEI": "solvent-diffusion limited"}
        self.run_basic_processing_test(options)

    def test_electron_migration_limited(self):
        options = {"SEI": "electron-migration limited"}
        self.run_basic_processing_test(options)

    def test_interstitial_diffusion_limited(self):
        options = {"SEI": "interstitial-diffusion limited"}
        self.run_basic_processing_test(options)

    def test_ec_reaction_limited(self):
        options = {"SEI": "ec reaction limited", "SEI porosity change": "true"}
        self.run_basic_processing_test(options)

    def test_loss_active_material_stress_negative(self):
        options = {"loss of active material": ("none", "stress-driven")}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_loss_active_material_stress_positive(self):
        options = {"loss of active material": ("stress-driven", "none")}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_loss_active_material_stress_both(self):
        options = {"loss of active material": "stress-driven"}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_negative_cracking(self):
        options = {"particle mechanics": ("swelling and cracking", "none")}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_positive_cracking(self):
        options = {"particle mechanics": ("none", "swelling and cracking")}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_both_cracking(self):
        options = {"particle mechanics": "swelling and cracking"}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

    def test_both_swelling_only(self):
        options = {"particle mechanics": "swelling only"}
        parameter_values = pybamm.ParameterValues("Ai2020")
        self.run_basic_processing_test(options, parameter_values=parameter_values)

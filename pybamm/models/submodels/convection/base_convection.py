#
# Base class for convection submodels
#
import pybamm


class BaseModel(pybamm.BaseSubModel):
    """Base class for convection submodels.

    **Extends:** :class:`pybamm.BaseSubModel`

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel
    options : dict, optional
        A dictionary of options to be passed to the model.
    """

    def __init__(self, param, options=None):
        super().__init__(param, options=options)

    def _get_standard_whole_cell_velocity_variables(self, variables):
        """
        A private function to obtain the standard variables which
        can be derived from the fluid velocity.

        Parameters
        ----------
        variables : dict
            The existing variables in the model

        Returns
        -------
        variables : dict
            The variables which can be derived from the volume-averaged
            velocity.
        """

        vel_scale = self.param.velocity_scale

        v_box_dict = {}
        for domain in self.options.whole_cell_domains:
            Domain = domain.capitalize()
            v_box_dict[domain] = variables[f"{Domain} volume-averaged velocity"]
        v_box = pybamm.concatenation(*v_box_dict.values())

        variables = {
            "Volume-averaged velocity": v_box,
            "Volume-averaged velocity [m.s-1]": vel_scale * v_box,
        }

        return variables

    def _get_standard_whole_cell_acceleration_variables(self, variables):
        """
        A private function to obtain the standard variables which
        can be derived from the fluid velocity.

        Parameters
        ----------
        variables : dict
            The existing variables in the model

        Returns
        -------
        variables : dict
            The variables which can be derived from the volume-averaged
            velocity.
        """

        acc_scale = self.param.velocity_scale / self.param.L_x

        div_v_box_dict = {}
        for domain in self.options.whole_cell_domains:
            Domain = domain.capitalize()
            div_v_box_dict[domain] = variables[f"{Domain} volume-averaged acceleration"]
        div_v_box = pybamm.concatenation(*div_v_box_dict.values())
        div_v_box_av = pybamm.x_average(div_v_box)

        variables = {
            "Volume-averaged acceleration": div_v_box,
            "X-averaged volume-averaged acceleration": div_v_box_av,
            "Volume-averaged acceleration [m.s-1]": acc_scale * div_v_box,
            "X-averaged volume-averaged acceleration [m.s-1]": acc_scale * div_v_box_av,
        }

        return variables

    def _get_standard_whole_cell_pressure_variables(self, variables):
        """
        A private function to obtain the standard variables which
        can be derived from the pressure in the fluid.

        Parameters
        ----------
        variables : dict
            The existing variables in the model

        Returns
        -------
        variables : dict
            The variables which can be derived from the pressure.
        """
        p_dict = {}
        for domain in self.options.whole_cell_domains:
            Domain = domain.capitalize()
            p_dict[domain] = variables[f"{Domain} pressure"]
        p = pybamm.concatenation(*p_dict.values())
        variables = {"Pressure": p}
        return variables

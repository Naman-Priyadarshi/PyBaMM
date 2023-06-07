#
# Concatenation classes
#
from __future__ import annotations
import copy
from collections import defaultdict

import numpy as np
import sympy
from scipy.sparse import issparse, vstack
from typing import Optional, Iterable, Sequence, TYPE_CHECKING

import pybamm


class Concatenation(pybamm.Symbol):
    """
    A node in the expression tree representing a concatenation of symbols.

    Parameters
    ----------
    children : iterable of :class:`pybamm.Symbol`
        The symbols to concatenate
    """

    def __init__(
        self,
        *children: Iterable[pybamm.Symbol],
        name=None,
        check_domain=True,
        concat_fun=None,
    ):
        # The second condition checks whether this is the base Concatenation class
        # or a subclass of Concatenation
        # (ConcatenationVariable, NumpyConcatenation, ...)
        if all(isinstance(child, pybamm.Variable) for child in children) and issubclass(
            Concatenation, type(self)
        ):
            raise TypeError(
                "'ConcatenationVariable' should be used for concatenating 'Variable' "
                "objects. We recommend using the 'concatenation' function, which will "
                "automatically choose the best form."
            )
        if name is None:
            name = "concatenation"
        if check_domain:
            domains = self.get_children_domains(children)
        else:
            domains = {"primary": []}
        self.concatenation_function = concat_fun

        super().__init__(name, children, domains=domains)

    def __str__(self):
        """See :meth:`pybamm.Symbol.__str__()`."""
        out = self.name + "("
        for child in self.children:
            out += "{!s}, ".format(child)
        out = out[:-2] + ")"
        return out

    def _diff(self, variable: pybamm.Symbol):
        """See :meth:`pybamm.Symbol._diff()`."""
        children_diffs = [child.diff(variable) for child in self.children]
        if len(children_diffs) == 1:
            diff = children_diffs[0]
        else:
            diff = self.__class__(*children_diffs)

        return diff

    def get_children_domains(self, children: Sequence[pybamm.Symbol]):
        # combine domains from children
        domain = []
        for child in children:
            if not isinstance(child, pybamm.Symbol):
                raise TypeError("{} is not a pybamm symbol".format(child))
            child_domain = child.domain
            if child_domain == []:
                raise pybamm.DomainError(
                    "Cannot concatenate child '{}' with empty domain".format(child)
                )
            if set(domain).isdisjoint(child_domain):
                domain += child_domain
            else:
                raise pybamm.DomainError("domain of children must be disjoint")

        auxiliary_domains = children[0].domains
        for level, dom in auxiliary_domains.items():
            if level != "primary" and dom != []:
                for child in children[1:]:
                    if child.domains[level] not in [dom, []]:
                        raise pybamm.DomainError(
                            "children must have same or empty auxiliary domains"
                        )

        domains = {**auxiliary_domains, "primary": domain}

        return domains

    def _concatenation_evaluate(self, children_eval):
        """See :meth:`Concatenation._concatenation_evaluate()`."""
        if len(children_eval) == 0:
            return np.array([])
        else:
            return self.concatenation_function(children_eval)

    def evaluate(
        self,
        t: Optional[float] = None,
        y: Optional[np.ndarray] = None,
        y_dot: Optional[np.ndarray] = None,
        inputs: Optional[dict] = None,
    ):
        """See :meth:`pybamm.Symbol.evaluate()`."""
        children = self.children
        children_eval = [None] * len(children)
        for idx, child in enumerate(children):
            children_eval[idx] = child.evaluate(t, y, y_dot, inputs)
        return self._concatenation_evaluate(children_eval)

    def create_copy(self):
        """See :meth:`pybamm.Symbol.new_copy()`."""
        new_children = [child.new_copy() for child in self.children]
        return self._concatenation_new_copy(new_children)

    def _concatenation_new_copy(self, children):
        """See :meth:`pybamm.Symbol.new_copy()`."""
        return concatenation(*children)

    def _concatenation_jac(self, children_jacs):
        """Calculate the Jacobian of a concatenation."""
        raise NotImplementedError

    def _evaluate_for_shape(self):
        """See :meth:`pybamm.Symbol.evaluate_for_shape`"""
        if len(self.children) == 0:
            return np.array([])
        else:
            # Default: use np.concatenate
            concatenation_function = self.concatenation_function or np.concatenate
            return concatenation_function(
                [child.evaluate_for_shape() for child in self.children]
            )

    def is_constant(self):
        """See :meth:`pybamm.Symbol.is_constant()`."""
        return all(child.is_constant() for child in self.children)

    def _sympy_operator(self, *children):
        """Apply appropriate SymPy operators."""
        self.concat_latex = tuple(map(sympy.latex, children))

        if self.print_name is not None:
            return sympy.Symbol(self.print_name)
        else:
            concat_str = r"\\".join(self.concat_latex)
            concat_sym = sympy.Symbol(r"\begin{cases}" + concat_str + r"\end{cases}")
            return concat_sym

    def to_equation(self):
        """Convert the node and its subtree into a SymPy equation."""
        eq_list = []
        for child in self.children:
            eq = child.to_equation()
            eq_list.append(eq)
        return self._sympy_operator(*eq_list)


class NumpyConcatenation(Concatenation):
    """
    A node in the expression tree representing a concatenation of equations, when we
    *don't* care about domains. The class :class:`pybamm.DomainConcatenation`, which
    *is* careful about domains and uses broadcasting where appropriate, should be used
    whenever possible instead.

    Upon evaluation, equations are concatenated using numpy concatenation.

    Parameters
    ----------
    children : iterable of :class:`pybamm.Symbol`
        The equations to concatenate
    """

    def __init__(self, *children: Sequence[pybamm.Symbol]):
        children = list(children)
        # Turn objects that evaluate to scalars to objects that evaluate to vectors,
        # so that we can concatenate them
        for i, child in enumerate(children):
            if child.evaluates_to_number():  # type:ignore
                children[i] = child * pybamm.Vector([1])
        super().__init__(
            *children,
            name="numpy_concatenation",
            check_domain=False,
            concat_fun=np.concatenate,
        )

    def _concatenation_jac(self, children_jacs):
        """See :meth:`pybamm.Concatenation.concatenation_jac()`."""
        children = self.children
        if len(children) == 0:
            return pybamm.Scalar(0)
        else:
            return SparseStack(*children_jacs)

    def _concatenation_new_copy(self, children):
        """See :meth:`pybamm.Symbol.new_copy()`."""
        return numpy_concatenation(*children)


class DomainConcatenation(Concatenation):
    """
    A node in the expression tree representing a concatenation of symbols, being
    careful about domains.

    It is assumed that each child has a domain, and the final concatenated vector will
    respect the sizes and ordering of domains established in mesh keys

    Parameters
    ----------

    children : iterable of :class:`pybamm.Symbol`
        The symbols to concatenate

    full_mesh : :class:`pybamm.Mesh`
        The underlying mesh for discretisation, used to obtain the number of mesh points
        in each domain.

    copy_this : :class:`pybamm.DomainConcatenation` (optional)
        if provided, this class is initialised by copying everything except the children
        from `copy_this`. `mesh` is not used in this case
    """

    def __init__(
        self,
        children: Iterable[pybamm.Symbol],
        full_mesh: pybamm.Mesh,
        copy_this: Optional[pybamm.DomainConcatenation] = None,
    ):
        # Convert any constant symbols in children to a Vector of the right size for
        # concatenation
        children = list(children)

        # Allow the base class to sort the domains into the correct order
        super().__init__(*children, name="domain_concatenation")

        if copy_this is None:
            # store mesh
            self._full_mesh = full_mesh

            # create dict of domain => slice of final vector
            self.secondary_dimensions_npts = self._get_auxiliary_domain_repeats(
                self.domains
            )
            self._slices = self.create_slices(self)

            # store size of final vector
            self._size = self._slices[self.domain[-1]][-1].stop

            # create disc of domain => slice for each child
            self._children_slices = [
                self.create_slices(child) for child in self.children
            ]
        else:
            self._full_mesh = copy.copy(copy_this._full_mesh)
            self._slices = copy.copy(copy_this._slices)
            self._size = copy.copy(copy_this._size)
            self._children_slices = copy.copy(copy_this._children_slices)
            self.secondary_dimensions_npts = copy_this.secondary_dimensions_npts

    def _get_auxiliary_domain_repeats(self, auxiliary_domains):
        """Helper method to read the 'auxiliary_domain' meshes."""
        mesh_pts = 1
        for level, dom in auxiliary_domains.items():
            if level != "primary" and dom != []:
                mesh_pts *= self.full_mesh[dom].npts
        return mesh_pts

    @property
    def full_mesh(self):
        return self._full_mesh

    def create_slices(self, node):
        slices = defaultdict(list)
        start = 0
        end = 0
        second_pts = self._get_auxiliary_domain_repeats(self.domains)
        if second_pts != self.secondary_dimensions_npts:
            raise ValueError(
                """Concatenation and children must have the same number of
                points in secondary dimensions"""
            )
        for i in range(second_pts):
            for dom in node.domain:
                end += self.full_mesh[dom].npts
                slices[dom].append(slice(start, end))
                start = end
        return slices

    def _concatenation_evaluate(self, children_eval):
        """See :meth:`Concatenation._concatenation_evaluate()`."""
        # preallocate vector
        vector = np.empty((self._size, 1))

        # loop through domains of children writing subvectors to final vector
        for child_vector, slices in zip(children_eval, self._children_slices):
            for child_dom, child_slice in slices.items():
                for i, _slice in enumerate(child_slice):
                    vector[self._slices[child_dom][i]] = child_vector[_slice]

        return vector

    def _concatenation_jac(self, children_jacs):
        """See :meth:`pybamm.Concatenation.concatenation_jac()`."""
        # note that this assumes that the children are in the right order and only have
        # one domain each
        jacs = []
        for i in range(self.secondary_dimensions_npts):
            for child_jac, slices in zip(children_jacs, self._children_slices):
                if len(slices) > 1:
                    raise NotImplementedError(
                        """jacobian only implemented for when each child has
                        a single domain"""
                    )
                child_slice = next(iter(slices.values()))
                jacs.append(pybamm.Index(child_jac, child_slice[i]))
        return SparseStack(*jacs)

    def _concatenation_new_copy(self, children):
        """See :meth:`pybamm.Symbol.new_copy()`."""
        new_symbol = simplified_domain_concatenation(
            children, self.full_mesh, copy_this=self
        )
        return new_symbol


class SparseStack(Concatenation):
    """
    A node in the expression tree representing a concatenation of sparse
    matrices. As with NumpyConcatenation, we *don't* care about domains.
    The class :class:`pybamm.DomainConcatenation`, which *is* careful about
    domains and uses broadcasting where appropriate, should be used whenever
    possible instead.

    Parameters
    ----------
    children : iterable of :class:`Concatenation`
        The equations to concatenate
    """

    def __init__(self, *children):  #: Iterable[pybamm.Concatenation]
        children = list(children)
        if not any(issparse(child.evaluate_for_shape()) for child in children):
            concatenation_function = np.vstack
        else:
            concatenation_function = vstack
        super().__init__(
            *children,
            name="sparse_stack",
            check_domain=False,
            concat_fun=concatenation_function,
        )

    def _concatenation_new_copy(self, children):
        """See :meth:`pybamm.Symbol.new_copy()`."""
        return SparseStack(*children)


class ConcatenationVariable(Concatenation):
    """A Variable representing a concatenation of variables."""

    def __init__(self, *children):
        # Name is the intersection of the children names (should usually make sense
        # if the children have been named consistently)
        name = intersect(children[0].name, children[1].name)
        for child in children[2:]:
            name = intersect(name, child.name)
        if len(name) == 0:
            name = None
        # name is unchanged if its length is 1
        elif len(name) > 1:
            name = name[0].capitalize() + name[1:]

        if len(children) > 0:
            if all(child.scale == children[0].scale for child in children):
                self._scale = children[0].scale
            else:
                raise ValueError("Cannot concatenate symbols with different scales")
            if all(child.reference == children[0].reference for child in children):
                self._reference = children[0].reference
            else:
                raise ValueError("Cannot concatenate symbols with different references")
            if all(
                child.bounds[0] == children[0].bounds[0] for child in children
            ) and all(child.bounds[1] == children[0].bounds[1] for child in children):
                self.bounds = children[0].bounds
            else:
                raise ValueError("Cannot concatenate symbols with different bounds")
        super().__init__(*children, name=name)

        print_name = intersect(children[0]._raw_print_name, children[1]._raw_print_name)
        for child in children[2:]:
            print_name = intersect(print_name, child._raw_print_name)
        if print_name.endswith("_"):
            print_name = print_name[:-1]

        self.print_name = print_name


def substrings(s: str):
    for i in range(len(s)):
        for j in range(i, len(s)):
            yield s[i : j + 1]


def intersect(s1: str, s2: str):
    # find all the common strings between two strings
    all_intersects = set(substrings(s1)) & set(substrings(s2))
    # intersect is the longest such intercept
    if len(all_intersects) == 0:
        return ""
    intersect = max(all_intersects, key=len)
    # remove leading and trailing white space
    return intersect.lstrip().rstrip()


def simplified_concatenation(*children):
    """Perform simplifications on a concatenation."""
    # remove children that are None
    children = list(filter(lambda x: x is not None, children))
    # Simplify concatenation of broadcasts all with the same child to a single
    # broadcast across all domains
    if len(children) == 0:
        raise ValueError("Cannot create empty concatenation")
    elif len(children) == 1:
        return children[0]
    elif all(isinstance(child, pybamm.Variable) for child in children):
        return pybamm.ConcatenationVariable(*children)
    else:
        # Create Concatenation to easily read domains
        concat = Concatenation(*children)
        if all(
            isinstance(child, pybamm.Broadcast) and child.child == children[0].child
            for child in children
        ):
            unique_child = children[0].orphans[0]
            if isinstance(children[0], pybamm.PrimaryBroadcast):
                return pybamm.PrimaryBroadcast(unique_child, concat.domain)
            else:
                return pybamm.FullBroadcast(
                    unique_child, broadcast_domains=concat.domains
                )
        else:
            return concat


def concatenation(*children):
    """Helper function to create concatenations."""
    # TODO: add option to turn off simplifications
    return simplified_concatenation(*children)


def simplified_numpy_concatenation(*children):
    """Perform simplifications on a numpy concatenation."""
    # Turn a concatenation of concatenations into a single concatenation
    new_children = []
    for child in children:
        # extract any children from numpy concatenation
        if isinstance(child, NumpyConcatenation):
            new_children.extend(child.orphans)
        else:
            new_children.append(child)
    return pybamm.simplify_if_constant(NumpyConcatenation(*new_children))


def numpy_concatenation(*children):
    """Helper function to create numpy concatenations."""
    # TODO: add option to turn off simplifications
    return simplified_numpy_concatenation(*children)


def simplified_domain_concatenation(children, mesh, copy_this=None):
    """Perform simplifications on a domain concatenation."""
    # Create the DomainConcatenation to read domain and child domain
    concat = DomainConcatenation(children, mesh, copy_this=copy_this)
    # Simplify Concatenation of StateVectors to a single StateVector
    # The sum of the evalation arrays of the StateVectors must be exactly 1
    if all(isinstance(child, pybamm.StateVector) for child in children):
        longest_eval_array = len(children[-1]._evaluation_array)
        eval_arrays = {}
        for child in children:
            eval_arrays[child] = np.concatenate(
                [
                    child.evaluation_array,
                    np.zeros(longest_eval_array - len(child.evaluation_array)),
                ]
            )
        first_start = children[0].y_slices[0].start
        last_stop = children[-1].y_slices[-1].stop
        if all(
            sum(array for array in eval_arrays.values())[first_start:last_stop] == 1
        ):
            return pybamm.StateVector(
                slice(first_start, last_stop), domains=concat.domains
            )

    return pybamm.simplify_if_constant(concat)


def domain_concatenation(children, mesh):
    """Helper function to create domain concatenations."""
    # TODO: add option to turn off simplifications
    return simplified_domain_concatenation(children, mesh)

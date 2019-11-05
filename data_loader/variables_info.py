"""Stores metadata on the variables.

Contains
--------
VariablesInfo:
    Stores various info in IterDict.
"""

from typing import Iterator, List, Union

import copy

from data_loader.iter_dict import IterDict

# TODO: kwargs


class VariablesInfo():
    """Gives various info about all variables.

    Each info is stored in an IterDict and can be accessed
    as an attribute. Same for kwargs.

    Parameters
    ----------
    var_list: List[str]
        Variables names
    infos: Dict[str, Dict[str: Any]]
        Info specific to a variable
        {'variable name': {'fullname': 'variable fullname', ...}, ...}
    **kwargs: Dict[str: Any]
        Any additional information

    Attributes
    ----------
    var: List[str]
        Variables names
    idx: Dict[name: str, int]
        Index of variables in the data
    n: int
        Number of variables
    'infos': IterDict[variable: str, Any]
    'kwargs': Any
    """
    def __init__(self, var_list, infos, **kwargs):
        # Add the var and idx attributes
        self.var = tuple(var_list)
        self.idx = IterDict({k: i for i, k in enumerate(var_list)})
        self.n = len(var_list)

        self._infos = []
        for var, info in infos.items():
            self.add_infos_per_variable(var, info)

        self.__dict__.update(kwargs)
        self._kwargs = list(kwargs.keys())

    def __iter__(self) -> Iterator:
        # TODO: enumerate over idx ?
        """Enumerate over var."""
        return enumerate(self.var)

    def __getitem__(
            self, item: Union[str, int, List[int], List[str]]
    ) -> "VariablesInfo":
        # REVIEW
        """Return VariableInfo slice."""

        keys = self.idx[item]
        if not isinstance(keys, list):
            keys = [keys]

        var = [self.var[i] for i in keys]

        infos = {}
        for key in self._infos:
            value = getattr(self, key).copy()
            for name in self.var:
                if name not in var:
                    value.pop(name)
            infos.update({key: value})

        kwargs = {k: self.__dict__[k] for k in self._kwargs}

        vi = VariablesInfo(var, {}, **kwargs)

        for name, info in infos.items():
            vi.add_info(name, info)

        return vi

    def copy(self) -> "VariablesInfo":
        """Copy this instance."""

        var_list = copy.copy(self.var)

        infos = {}
        for key in self._infos:
            value = getattr(self, key).copy()
            infos.update({key: value})

        kwargs = {}
        for key in self._kwargs:
            value = getattr(self, key)
            try:
                value = copy.copy(value)
            except AttributeError:
                pass
            kwargs.update({key: value})

        vi = VariablesInfo(var_list, {}, **kwargs)

        for name, info in infos.items():
            vi.add_info(name, info)

        return vi

    def add_info(self, info, values):
        """Add info.

        Parameters
        ----------
        info: str
            Info name
        values: Dict[variable: str, Any]
            Values
        """
        if info not in self._infos:
            self._infos.append(info)
            self.__dict__.update({info: IterDict(
                dict(zip(self.var, [None]*self.n)))})

        self.__dict__[info].update(values)

    def add_infos_per_variable(self, var, infos):
        """Add infos for a single variable.

        Parameters
        ----------
        var: str
            Variable name
        infos: Dict[str, Any]
            Infos name and values
            {name: value, ...}
        """
        for k, z in infos.items():
            self.add_info(k, {var: z})

    def add_variable(self, var, **kwargs):
        """Add a variable with corresponding info.

        Parameters
        ----------
        var: str
            Variable name
        **kwargs: Dict[str, Any]
            Infos name and values
            {name: value, ...}

        If info is not provided, it is filled with None
        """

        var_list = list(self.var) + [var]
        self.var = tuple(var_list)

        self.n += 1

        self.idx.update({var: self.n-1})
        d = self.__dict__
        keys = self._infos

        for k in keys:
            if k not in list(kwargs.keys()):
                kwargs.update({k: None})
        for k, z in kwargs.items():
            if k in d:
                d[k].update({var: z})
            else:   # The info is new
                L = [None]*self.n
                L[-1] = z
                d.update({k: IterDict(zip(self.var, L))})

    def pop_variables(self, variables: List[str]):
        """Remove variables from vi."""

        if not isinstance(variables, list):
            variables = [variables]

        d = {k: self.__dict__[k] for k in self._infos}
        var_list = list(self.var)
        for v in variables:
            var_list.remove(v)
            self.n -= 1
            for z in d.values():
                z.pop(v)
        self.var = tuple(var_list)
        self.idx = IterDict({k: i for i, k in enumerate(var_list)})

"""Plot evolution of average of a variable."""

from typing import List

from data_loader.db_types.plotting.average_abc import PlotObjectAvgABC
from data_loader.db_types.plotting.line import PlotObjectLine


class PlotObjectLineAvg(PlotObjectAvgABC, PlotObjectLine):
    """Plot evolution of average of a variable."""

    def find_axes(self, axes: List[str] = None) -> List[str]:
        if axes is not None:
            axes_ = axes
        else:
            dims = [d for d in self.keyring.get_high_dim()
                    if d not in self.avg_dims]
            axes_ = [dims[0], self.scope.var[0]]

        if len(axes_) != 2:
            raise IndexError("Number of axes not 2 (%s)" % axes_)

        if axes_[0] in self.scope.coords:
            self.axis_var = 1

        return axes_
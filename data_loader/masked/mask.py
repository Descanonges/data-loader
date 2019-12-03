"""Manages some aspects of masked data.

Computation of land mask from Natural Earth using cartopy.
"""

import numpy as np
import scipy.ndimage as ndimage

from data_loader.masked._rasterize_polygon import shp_mask


def compute_land_mask(root, lat, lon):
    """Compute land mask.

    According to Cartopy data (from naturalearthdata.com)
    for a regular grid save it in wd

    Parameters
    ----------
    root: str
        Directory
    lat: Coord
    lon: Coord
    """
    from shapely.ops import unary_union
    from cartopy.feature import LAND
    from shapely.geometry.polygon import Polygon

    # Extent
    lon_min, lon_max = lon.get_limits()
    lat_min, lat_max = lat.get_limits()

    d = abs(lon_max - lon_min)/10.
    lon_min = lon_min - d
    lon_max = lon_max + d
    lat_min = lat_min - d
    lat_max = lat_max + d
    extent = [(lon_min, lat_min), (lon_max, lat_min),
              (lon_max, lat_max), (lon_min, lat_max)]

    P = Polygon(extent)
    global_land = unary_union(tuple(LAND.geometries()))
    land = global_land.intersection(P)

    mask = shp_mask(land, lon, lat)
    np.save(root + 'land_mask.npy', mask)


def do_stack(func, ndim, array, *args, axes=None, output=None, **kwargs):
    # TODO: wtf is this doing here ?
    """Apply func over certain axes of array. Loop over remaining axes.

    func: function which takes args and kwargs
    ndim: the number of dimensions func works on. The remaining dimension
        in input array will be treated as stacked and looped over
    array:
    axes: axes that func should work over, default is the last ndim axes
    output: result passed to output. default to np.zeros
    args and kwargs passed to func
    """

    if axes is None:
        axes = list(range(-ndim, 0))
    lastaxes = list(range(-ndim, 0))

    # Swap axes to the end
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])

    # Save shape
    stackshape = array.shape[:-ndim]

    if output is None:
        output = np.zeros(array.shape)

    # Place all stack into one dimension
    array = np.reshape(array, (-1, *array.shape[-ndim:]))
    output = np.reshape(output, (-1, *output.shape[-ndim:]))

    for i in range(array.shape[0]):
        output[i] = func(array[i], *args, **kwargs)

    array = np.reshape(array, (*stackshape, *array.shape[-ndim:]))
    output = np.reshape(output, (*stackshape, *output.shape[-ndim:]))

    # Reswap axes
    for i in range(ndim):
        array = np.swapaxes(array, axes[i], lastaxes[i])
        output = np.swapaxes(output, axes[i], lastaxes[i])

    return output


def get_circle_kernel(n):
    """Return circular kernel for convolution of size nxn."""
    kernel = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            kernel[i, j] = (i-(n-1)/2)**2 + (j-(n-1)/2)**2 <= (n/2)**2

    return kernel


def enlarge_mask(mask, n_neighbors, axes=None):
    """Enlarge a stack of boolean mask by n_neighbors."""
    N = 2*n_neighbors + 1
    kernel = get_circle_kernel(N)

    mask = do_stack(ndimage.convolve, 2, 1.*mask, kernel, axes) > 0

    return mask
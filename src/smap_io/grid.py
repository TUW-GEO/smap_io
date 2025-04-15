from pygeogrids.grids import CellGrid, BasicGrid, lonlat2cell
from ease_grid import EASE2_grid
import numpy as np
from pygeogrids.netcdf import load_grid
import os

class EASE36CellGrid(CellGrid):
    """ CellGrid version of EASE36 Grid as used in SMAP 36km """

    def __init__(self, bbox=None, margin=(None, 1), only_land=False):
        """
        Parameters
        ----------
        bbox: tuple, optional (default: None)
            (min_lon, min_lat, max_lon, max_lat)
            Bounding box to create subset for, if None is passed a global
            grid is used.
        margin: tuple, optional (default: (2,2))
            Removes x,y lines/columns from the global Ease grid
            can also be e.g. (None, 1) to only remove the top/bottom line and
            leave columns unchanged.
        only_land: bool, optional (default: False)
            Drop all points over oceans in the selected subset.
        """

        ease36 = EASE2_grid(36000)
        lons, lats = ease36.londim, ease36.latdim

        if margin is not None:
            lons = lons[margin[0]:-margin[0]] if margin[0] is not None else lons
        lats = ease36.latdim
        if margin is not None:
            lats = lats[margin[1]:-margin[1]] if margin[1] is not None else lats

        lons, lats = np.meshgrid(lons, lats)
        assert lons.shape == lats.shape
        shape = lons.shape

        lats = np.flipud(lats)  # flip lats, so that origin in bottom left
        lons, lats = lons.flatten(), lats.flatten()

        globgrid = BasicGrid(lons, lats, shape=shape)
        sgpis = globgrid.activegpis

        self.bbox = bbox
        if self.bbox:
            sgpis = globgrid.get_bbox_grid_points(
                latmin=self.bbox[1],
                latmax=self.bbox[3],
                lonmin=self.bbox[0],
                lonmax=self.bbox[2])

        self.only_land = only_land
        if self.only_land:
            lgpis = load_grid(
                os.path.join(
                    os.path.dirname(__file__), 'grids',
                    'ease36land.nc')).activegpis
            sgpis = np.intersect1d(sgpis, lgpis)

        self.cellsize = 5.

        super().__init__(
            lon=globgrid.arrlon,
            lat=globgrid.arrlat,
            subset=sgpis,
            cells=lonlat2cell(globgrid.arrlon, globgrid.arrlat, self.cellsize),
            shape=shape)

        self.subset_shape = (len(np.unique(self.activearrlat)),
                             len(np.unique(self.activearrlon)))

    def cut(self) -> CellGrid:
        dy = len(np.unique(self.activearrlat))
        dx = len(np.unique(self.activearrlon))
        # create a new grid from the active subset
        shape = self.subset_shape if np.prod(self.subset_shape) == len(
            self.activegpis) else None
        return BasicGrid(
            lon=self.activearrlon,
            lat=self.activearrlat,
            gpis=self.activegpis,
            subset=None,
            shape=shape).to_cell_grid(self.cellsize)

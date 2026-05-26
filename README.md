# isobath

A GUI tool for computing slope angles along depth contours (isobaths) from NetCDF bathymetry data.

## Features

- Load NetCDF bathymetry files and interactively select a region of interest
- Visualise depth contours on a map
- Compute slope angles at each coordinate interval along a chosen isobath using linear regression
- Step through intervals with Previous / Next navigation
- Remove outlier points using a lasso selector and recompute
- Export results as a two-column text file (coordinate, angle)

## Installation

```bash
pip install isobath
```

## Usage

Launch the GUI from the terminal:

```bash
isobath
```

Or run as a module:

```bash
python -m isobath
```

### Workflow

1. Click **Open** to load a NetCDF file, or **Sample File** to load the bundled example dataset.
2. In the Area Selector window, choose the variable and its latitude/longitude dimensions, then draw a rectangle to subset the region of interest.
3. In the Settings panel (right dock), set the **Contour Depth** and adjust the coordinate axis, start/end points, averaging interval, and coordinate interval.
4. Click **Compute Angle** to perform the first linear regression and view the slope angle.
5. Use **Next** / **Previous** to step through coordinate intervals.
6. Use **Lasso** to select outlier points, then **Delete** to remove them and recompute. **Undo** restores the previous point set.
7. Click **Save** or **Save As** to export the results.

## Output

Results are saved as a plain text file with two columns:

```
coordinate   angle (degrees)
8.0000       127.4396
9.0000       125.5481
...
```

## Dependencies

- [PyQt6](https://pypi.org/project/PyQt6/)
- [matplotlib](https://matplotlib.org/)
- [numpy](https://numpy.org/)
- [netCDF4](https://unidata.github.io/netcdf4-python/)
- [scipy](https://scipy.org/)

## License

MIT License. See [LICENSE](LICENSE) for details.

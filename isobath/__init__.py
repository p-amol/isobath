__version__ = "0.1.0"

# Load matplotlib's FreeType bindings before any Qt module. If PyQt6 (pip
# wheel) is imported first, its Qt loads the system libfreetype, and a
# conda-forge matplotlib that links libfreetype dynamically then renders text
# with that mismatched library, failing with "FT_Render_Glyph ... raster
# overflow".
import matplotlib.ft2font  # noqa: E402, F401

import numpy as np
from datetime import datetime

from .server import app

def dt_to_dec(dt):
    """Convert a datetime to decimal year."""
    year_start = datetime(dt.year, 1, 1)
    year_end = year_start.replace(year=dt.year + 1)
    return dt.year + ((dt - year_start).total_seconds() /  # seconds so far
                      float((year_end - year_start).total_seconds()))  # seconds in year

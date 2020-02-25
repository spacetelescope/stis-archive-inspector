from dash import Dash
from .config import config

stylesheets=config['inspector']['stylesheets']
app = Dash(external_stylesheets=stylesheets, suppress_callback_exceptions=True)


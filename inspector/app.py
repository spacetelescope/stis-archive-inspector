
import dash_html_components as html
import dash_core_components as dcc
import json
import numpy as np
from datetime import datetime

from .config import config
from .fetch_metadata import generate_dataframe_from_csv, generate_csv_from_mast
from .server import app
from .utils import dt_to_dec
from . import overview_callbacks, mode_callbacks, aperture_callbacks


# Read in Config file
outdir = config['inspector']['outdir']
csv_name = config['inspector']['csv_name']
gen_csv = config['inspector']['gen_csv']
datatype = config['inspector']['datatype']
instrument = config['inspector']['instrument']
stylesheets = config['inspector']['stylesheets']
mast = config['inspector']['mast']

# Overview Parameters -- affected by callbacks
overview_detectors = ["STIS/CCD", "STIS/NUV-MAMA", "STIS/FUV-MAMA"]
overview_daterange = []
overview_metric = "n-obs"

# Mode Parameters -- affected by callbacks
selected_modes = ["Spectroscopic"]
mode_daterange = []
mode_detectors = ["STIS/CCD", "STIS/NUV-MAMA", "STIS/FUV-MAMA"]
mode_metric = "n-obs"

# Aperture Parameters -- affected by callbacks
aperture_obstype = ["Spectroscopic"]
aperture_daterange = []
aperture_detectors = ["STIS/CCD",
                           "STIS/NUV-MAMA", "STIS/FUV-MAMA"]
aperture_metric = "n-obs"
mast = generate_dataframe_from_csv(outdir+csv_name)

# Overview Page Plots --------------------------------------------
overview_df = mast[["Start Time", "obstype","Instrument Config","Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in overview_df['Start Time']])

overview_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
overview_df = overview_df[["Decimal Year",
                     "obstype", "Instrument Config", "Exp Time"]]

# Plot 1: Modes --------------------------------------------------
spec_mode_groups = config['modes']['spec_groups']
spec_mode_labels = config['modes']['spec_labels']

im_mode_groups = config['modes']['im_groups']
im_mode_labels = config['modes']['im_labels']

mode_groups = []
mode_labels = []
if "Imaging" in selected_modes:
    mode_groups += im_mode_groups
    mode_labels += im_mode_labels
if "Spectroscopic" in selected_modes:
    mode_groups += spec_mode_groups
    mode_labels += spec_mode_labels

modes_df = mast[["Filters/Gratings", "Start Time",
                      "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in modes_df['Start Time']])

# Convert to Start Times to Decimal Years
modes_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
modes_df = modes_df[["Filters/Gratings", "Decimal Year",
                     "obstype", "Instrument Config", "Exp Time"]]

# Plot 2: Apertures ------------------------------------------------
aperture_groups = config['apertures']['groups']
aperture_labels = config['apertures']['labels']

apertures_df = mast[["Apertures", "Start Time",
                          "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in apertures_df['Start Time']])
# Convert to Start Times to Decimal Years
apertures_df['Decimal Year'] = [
    dt_to_dec(time) for time in start_times]
apertures_df = apertures_df[[
    "Apertures", "Decimal Year", "obstype", "Instrument Config", "Exp Time"]]

# App Layout

# Header
app.layout = html.Div(children=[
    html.H1(f'{instrument} Archive Inspector'),

    # Modes Tab
    dcc.Tabs(id="tabs", children=[

        dcc.Tab(label='Overview', children=[
            # Div Container for metric chooser (positioned far right)


            html.Div(children=[
                html.H4(id="stis-intro",children="Introduction to STIS"),

                html.P("""
                The Space Telescope Imaging Spectrograph(STIS), 
                installed on the Hubble Space Telescope during Servicing Mission 2 (1997).
                STIS provides spatially resolved spectroscopy from 1150 to 10,300 Å at low 
                to medium spectral resolution, high spatial resolution echelle 
                spectroscopy in the ultraviolet (UV), solar-blind imaging in the UV, 
                time tagging of photons in the UV for high time resolution, 
                and direct and coronagraphic imaging in the optical. 

                STIS was successfully repaired during the fourth HST servicing mission (SM4) 
                in May 2009 and has resumed science operations with all channels. 
                This followed a nearly five year long suspension of science operations 
                that began in August 2004, when a power supply in the Side-2 electronics had failed.
                """),

                html.H4(id="stis-stats", children="STIS Archive Statistics"),

                html.P(f"""Total STIS Observations: {len(mast)}"""),
                html.P(f"""Total STIS Exposure Time: {np.round(np.sum(mast['Exp Time'])/60/60,2)} Hours"""),
                html.P(f"""Earliest Observation in Archive: {min(mast['Start Time'])}"""),
                html.P(f"""Most Recent Observation in Archive: {max(mast['Start Time'])}""")
                ],
                style={'width': '40%', 'display': 'inline-block', 
                       'padding': 20, 'vertical-align': 'top'}),

            html.Div(children=[dcc.Dropdown(id="detector-metric-dropdown",
                                            options=[{'label': "Total Number of Observations", 'value': 'n-obs'},
                                                     {'label': "Total Exposure Time (Hours)", 'value': 'exptime'}],
                                            value=overview_metric, clearable=False),
                dcc.Graph(id='detector-pie-chart'),
                              ],
                     style={'width': '40%', 'display': 'inline-block', 'padding': 20}),

            html.Div(children=[
                dcc.RangeSlider(id='detector-date-slider',
                                min=int(min(overview_df['Decimal Year'])),
                                max=int(max(overview_df['Decimal Year'])) + 1,
                                value=[int(min(overview_df['Decimal Year'])),
                                       int(max(overview_df['Decimal Year'])) + 1],
                                marks={str(int(year)): str(int(year))
                                       for year in overview_df['Decimal Year'].unique()},
                                included=True)
            ])]),

            

        dcc.Tab(label='Modes', children=[html.Div(children=[

            # Div Container for detector checklist (positioned far left)
            html.Div(children=[
                dcc.Checklist(id="modes-detector-checklist",
                              options=[{'label': "CCD", 'value': 'STIS/CCD'},
                                       {'label': "NUV-MAMA",'value': 'STIS/NUV-MAMA'},
                                       {'label': "FUV-MAMA",'value': 'STIS/FUV-MAMA'}],
                                      value=mode_detectors)
                              ], style={'width': '25%', 'display': 'inline-block'}),

            # Div Container for obstype checklist (positioned middle)
            html.Div(children=[
                dcc.Checklist(id="modes-type-checklist",
                              options=[{'label': "Imaging Modes", 'value': 'Imaging'},
                                       {'label': "Spectroscopic Modes",'value': 'Spectroscopic'}], 
                                       value=selected_modes)
                              ], style={'width': '25%', 'display': 'inline-block'}),

            # Div Container for metric chooser (positioned far right)
            html.Div(children=[
                dcc.Dropdown(id="modes-metric-dropdown",
                             options=[{'label': "Total Number of Observations", 'value': 'n-obs'},
                                      {'label': "Total Exposure Time",'value': 'exptime'}], 
                                      value=mode_metric, clearable=False)
                              ], style={'width': '40%', 'display': 'inline-block'}),

            # Div Container for Graph and Range Slider
            html.Div(children=[
                dcc.Graph(id='modes-plot-with-slider'),
                dcc.RangeSlider(id='modes-date-slider',
                                min=int(min(modes_df['Decimal Year'])),
                                max=int(max(modes_df['Decimal Year'])) + 1,
                                value=[int(min(modes_df['Decimal Year'])), 
                                       int(max(modes_df['Decimal Year'])) + 1],
                                marks={str(int(year)): str(int(year)) 
                                        for year in modes_df['Decimal Year'].unique()},
                                included=True)],
                          style={'padding': 20}),
            # Div Container for Mode Timeline
            html.Div(children=[
                dcc.Graph(id='mode-timeline')],
                          style={'width': '50%', 'display': 'inline-block'}),

            # Div Container for Mode Pie Chart
            html.Div(children=[
                dcc.Graph(id='mode-pie-chart')],
                          style={'width': '40%', 'display': 'inline-block'}),
                          ])]),

        # Apertures Tab
        dcc.Tab(label='Apertures', children=[html.Div(children=[

            # Div Container for detector checklist (positioned far left)
            html.Div(children=[
                dcc.Checklist(id="apertures-detector-checklist",
                              options=[{'label': "CCD", 'value': 'STIS/CCD'},
                                       {'label': "NUV-MAMA",
                                        'value': 'STIS/NUV-MAMA'},
                                       {'label': "FUV-MAMA",
                                        'value': 'STIS/FUV-MAMA'}
                                       ],
                              value=aperture_detectors)
            ], style={'width': '25%', 'display': 'inline-block'}),

            # Div Container for obstype checklist (positioned middle)
            html.Div(children=[
                dcc.Checklist(id="apertures-type-checklist",
                              options=[{'label': "Imaging Observations", 'value': 'Imaging'},
                                       {'label': "Spectroscopic Observations",
                                        'value': 'Spectroscopic'},
                                       {'label': "Coronagraphic Observations",
                                        'value': 'Coronagraphic'}
                                       ], value=aperture_obstype)
            ], style={'width': '25%', 'display': 'inline-block'}),
            # Div Container for metric chooser (positioned far right)
            html.Div(children=[
                dcc.Dropdown(id="apertures-metric-dropdown",
                             options=[{'label': "Total Number of Observations", 'value': 'n-obs'},
                                      {'label': "Total Exposure Time",
                                       'value': 'exptime'}
                                      ], value=aperture_metric, clearable=False)
            ], style={'width': '40%', 'display': 'inline-block'}),
            # Div Container for Graph and Range Slider
            html.Div(children=[
                dcc.Graph(id='apertures-plot-with-slider'),
                dcc.RangeSlider(id='apertures-date-slider',
                                min=int(min(modes_df['Decimal Year'])),
                                max=int(
                                    max(modes_df['Decimal Year'])) + 1,
                                value=[int(min(modes_df['Decimal Year'])),
                                       int(max(modes_df['Decimal Year'])) + 1],
                                marks={str(int(year)): str(int(year)) for year in
                                       modes_df['Decimal Year'].unique()},
                                included=True)],
                     style={'padding': 20}),

            # Div Container for Mode Timeline
            html.Div(children=[
                dcc.Graph(id='aperture-timeline')],
                style={'width': '50%', 'display': 'inline-block'}),

            # Div Container for Mode Pie Chart
            html.Div(children=[
                dcc.Graph(id='aperture-pie-chart')],
                style={'width': '40%', 'display': 'inline-block'}),

        ])]),
        html.Div(id='tabs-content')
    ])])

import numpy as np
import pandas as pd
import datetime
import urllib.request
import urllib.parse
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go


class Inspector:
    """Class for interactive inspection of the STIS archive"""
    def __init__(self, outdir='./', use_csv=False, gen_csv=True, datatype='S', instrument='STIS'):
        self.outdir = outdir
        self.use_csv = use_csv
        self.csv_name = "stis_archive.csv"
        self.gen_csv = gen_csv
        self.datatype = datatype
        self.instrument = instrument
        self.stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
        self.mast = []

        # Mode Parameters
        self.selected_modes = ["Spectroscopic"]
        self.mode_daterange = []
        self.mode_detectors = ["STIS/CCD", "STIS/NUV-MAMA", "STIS/FUV-MAMA"]
        self.mode_metric = "n-obs"

    def generate_from_csv(self):
        """Generate a Pandas DataFrame from an existing csv metadata file"""
        self.mast = pd.read_csv(self.csv_name)
        self.mast = self.mast[self.mast.keys()[1:]]

        return self.mast

    def generate_from_mast(self):
        """Generate a Pandas DataFrame from querying MAST"""

        # Determine if we want 'science', 'calibration', or 'all' datasets:
        datatype = self.datatype.upper()
        assert datatype in ['S', 'C', '%', 'ALL'], "'datatype' is not a valid selection."
        if datatype == 'ALL':
            datatype = '%'

        url = 'https://archive.stsci.edu/hst/search.php'

        # Output columns
        selectedColumnsCsv = \
            'sci_data_set_name,' + \
            'sci_obset_id,' + \
            'sci_targname,' + \
            'sci_start_time,' + \
            'sci_stop_time,' + \
            'sci_actual_duration,' + \
            'sci_instrume,' + \
            'sci_instrument_config,' + \
            'sci_operating_mode,' + \
            'sci_aper_1234,' + \
            'sci_spec_1234,' + \
            'sci_central_wavelength,' + \
            'sci_fgslock,' + \
            'sci_mtflag,' + \
            'sci_pep_id,' + \
            'sci_aec,' + \
            'sci_obs_type,' + \
            'scp_scan_type'

        # Loop year-by-year to avoid data limits:
        all_years = []
        for year in np.arange(1997, datetime.datetime.now().year + 1):
            print ('Working on {}...'.format(year))
            data = [ \
                ('sci_instrume', self.instrument),
                ('sci_aec', datatype),
                ('sci_start_time', 'Jan 1 {} .. Jan 1 {}'.format(year, year + 1)),
                ('max_records', '25000'),
                ('ordercolumn1', 'sci_start_time'),
                ('outputformat', 'JSON'),
                ('selectedColumnsCsv', selectedColumnsCsv),
                ('nonull', 'on'),
                ('action', 'Search'), ]

            try:
                url_values = urllib.parse.urlencode(data)
                full_url = url + '?' + url_values
                # print (full_url)
                with urllib.request.urlopen(full_url) as response:
                    json_file = response.read()

                # Convert to Pandas table:
                all_years.append(pd.read_json(json_file.decode()))
            except ValueError:
                pass  # Sad years with no data

        # Concatenate individual years together:
        mast = pd.concat(all_years)

        # Modify/add some rows:
        mast['Start Time'] = [datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in mast['Start Time']]
        mast['obstype'] = ['Imaging' if 'MIR' in x else 'Spectroscopic' for x in mast['Filters/Gratings']]
        mast.loc[mast['Apertures'] == '50CORON', 'obstype'] = 'Coronagraphic'
        mast['Instrument Config'] = [x.strip() for x in mast['Instrument Config']]
        self.mast = mast
        return self.mast

    def dt_to_dec(self, dt):
        """Convert a datetime to decimal year."""
        year_start = datetime.datetime(dt.year, 1, 1)
        year_end = year_start.replace(year=dt.year + 1)
        return dt.year + ((dt - year_start).total_seconds() /  # seconds so far
                          float((year_end - year_start).total_seconds()))  # seconds in year

    def load_dataframe_into_dash(self):
        """Load the mast dataframe into an interactive dash instance"""

        # Plot 1: Modes --------------------------------------------------
        spec_mode_groups = [["G140L", "G140M", "G230M", "G230L"],
                       ["G230LB", "G230MB", "G430L", "G430M", "G750L", "G750M"],
                       ["E140M", "E140H", "E230M", "E230H"],
                       ["PRISM"]]
        spec_mode_labels = ["MAMA First Order Spectroscopy",
                  "CCD First Order Spectroscopy",
                  "MAMA Echelle Spectroscopy",
                  "MAMA Prism Spectroscopy"]

        im_mode_groups = [["MIRVIS", "MIRNUV", "MIRFUV"]]
        im_mode_labels = ["Imaging"]

        mode_groups = []
        mode_labels = []
        if "Imaging" in self.selected_modes:
            mode_groups += im_mode_groups
            mode_labels += im_mode_labels
        if "Spectroscopic" in self.selected_modes:
            mode_groups += spec_mode_groups
            mode_labels += spec_mode_labels

        modes_df = self.mast[["Filters/Gratings", "Start Time", "obstype", "Instrument Config", "Exp Time"]]
        start_times = np.array([datetime.datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                                for start_time in modes_df['Start Time']])
        # Convert to Start Times to Decimal Years
        modes_df['Decimal Year'] = [self.dt_to_dec(time) for time in start_times]
        modes_df = modes_df[["Filters/Gratings", "Decimal Year", "obstype", "Instrument Config", "Exp Time"]]

        # Plot 2: Apertures ------------------------------------------------
        apertures = np.array(self.mast["Apertures"], dtype=str)

        # Layout Dash App
        app = dash.Dash(__name__, external_stylesheets=self.stylesheets)

        # Header
        app.layout = html.Div(children=[
            html.H1(f'{self.instrument} Archive Inspector'),
            dcc.Tabs(id="tabs", children=[

                dcc.Tab(label='Modes', children=[html.Div(children=[

                    # Div Container for detector checklist (positioned far left)
                    html.Div(children=[
                        dcc.Checklist(id="modes-detector-checklist",
                                      options=[{'label': "CCD", 'value': 'STIS/CCD'},
                                               {'label': "NUV-MAMA", 'value': 'STIS/NUV-MAMA'},
                                               {'label': "FUV-MAMA", 'value': 'STIS/FUV-MAMA'}
                                               ],
                                      values=self.mode_detectors)
                    ], style={'width': '25%', 'display': 'inline-block'}),
                    # Div Container for obstype checklist (positioned middle)
                    html.Div(children=[
                        dcc.Checklist(id="modes-type-checklist",
                                      options=[{'label': "Imaging Modes", 'value': 'Imaging'},
                                               {'label': "Spectroscopic Modes", 'value': 'Spectroscopic'}
                                               ], values=self.selected_modes)
                                        ], style={'width': '25%', 'display': 'inline-block'}),
                    # Div Container for metric chooser (positioned far right)
                    html.Div(children=[
                        dcc.Dropdown(id="modes-metric-dropdown",
                                      options=[{'label': "Total Number of Observations", 'value': 'n-obs'},
                                               {'label': "Total Exposure Time", 'value': 'exptime'}
                                               ], value=self.mode_metric, clearable=False)
                    ], style={'width': '40%', 'display': 'inline-block'}),
                    # Div Container for Graph and Range Slider
                    html.Div(children=[
                        dcc.Graph(id='modes-plot-with-slider'),
                        dcc.RangeSlider(id='modes-date-slider',
                                        min=int(min(modes_df['Decimal Year'])),
                                        max=int(max(modes_df['Decimal Year'])) + 1,
                                        value=[int(min(modes_df['Decimal Year'])), int(max(modes_df['Decimal Year'])) + 1],
                                        marks={str(int(year)): str(int(year)) for year in modes_df['Decimal Year'].unique()},
                                        included=True)],
                        style={'padding': 20}),
                    # Div Container for Graph and Range Slider
                    html.Div(children=[
                        dcc.Graph(id='mode-timeline')],
                        style={'width': '50%', 'display': 'inline-block'})

                ], style={'marginLeft': 40, 'marginRight': 40})

                ]),
                dcc.Tab(label='Tab Two', value='apertures_tab'),
            ]),
            html.Div(id='tabs-content')
        ])

        # Callbacks
        @app.callback(dash.dependencies.Output('modes-plot-with-slider', 'figure'),
                      [dash.dependencies.Input('modes-date-slider', 'value'),
                       dash.dependencies.Input('modes-type-checklist', 'values'),
                       dash.dependencies.Input('modes-detector-checklist', 'values'),
                       dash.dependencies.Input('modes-metric-dropdown', 'value')])
        def update_mode_figure(year_range, selected_modes, mode_detectors, mode_metric):
            self.mode_detectors = mode_detectors
            self.mode_daterange = year_range
            self.selected_modes = selected_modes
            self.mode_metric = mode_metric

            mode_groups = []
            mode_labels = []
            if "Imaging" in self.selected_modes:
                mode_groups += im_mode_groups
                mode_labels += im_mode_labels
            if "Spectroscopic" in self.selected_modes:
                mode_groups += spec_mode_groups
                mode_labels += spec_mode_labels

            # Filter observations by detector
            filtered_df = modes_df[(modes_df['Instrument Config'].isin(self.mode_detectors))]
            # Filter observations by observation year (decimal)
            filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) &
                                                          (filtered_df['Decimal Year'] <= year_range[1])]
            # Filter modes by group
            if self.mode_metric == 'n-obs':
                filtered_df = filtered_df['Filters/Gratings']  # Just look at filters and gratings
                n_tots = []
                filtered_groups = []  # Need this for avoiding empty bars in plotting
                for grp, label in zip(mode_groups, mode_labels):
                    # grp is a list of modes, label is the category
                    mode_n_tots = []
                    for mode in grp:
                        n_tot = len(filtered_df[filtered_df.isin([mode])])
                        mode_n_tots.append(n_tot)

                    new_grp = np.array(grp)[np.array(mode_n_tots) != 0.0]
                    mode_n_tots = np.array(mode_n_tots)[np.array(mode_n_tots) != 0.0]
                    n_tots.append(mode_n_tots)
                    filtered_groups.append(list(new_grp))

                # A go.Histogram is better for here, but go.Bar is consistent with the other view in terms of layout so
                # it is the better choice in this case
                p1_data = [go.Bar(x=grp, y=n, name=label)
                           for grp, n, label in zip(filtered_groups, n_tots, mode_labels)]
                ylabel = "Number of Observations"

            elif self.mode_metric == 'exptime':
                filtered_df = filtered_df[['Filters/Gratings', "Exp Time"]]
                exp_tots = []
                filtered_groups = []  # Need this for avoiding empty bars in plotting
                for grp, label in zip(mode_groups, mode_labels):
                    # grp is a list of modes, label is the category
                    mode_exp_tots = []
                    for mode in grp:
                        exp_tot = np.sum(filtered_df['Exp Time'][filtered_df['Filters/Gratings'].isin([mode])])
                        mode_exp_tots.append(exp_tot)

                    new_grp = np.array(grp)[np.array(mode_exp_tots) != 0.0]
                    mode_exp_tots = np.array(mode_exp_tots)[np.array(mode_exp_tots) != 0.0]
                    exp_tots.append(mode_exp_tots)
                    filtered_groups.append(list(new_grp))

                p1_data = [go.Bar(x=grp, y=exp, name=label)
                           for grp, exp, label in zip(filtered_groups, exp_tots, mode_labels)]

                ylabel = "Total Exposure Time (Seconds)"

            return {
                    'data': p1_data,
                    'layout': go.Layout(title=f"{self.instrument} Mode Usage", hovermode='closest',
                                        xaxis={'title': 'Mode'},
                                        yaxis={'title': ylabel})
            }

        @app.callback(dash.dependencies.Output('mode-timeline', 'figure'),
                      [dash.dependencies.Input('modes-date-slider', 'value'),
                       dash.dependencies.Input('modes-type-checklist', 'values'),
                       dash.dependencies.Input('modes-detector-checklist', 'values'),
                       dash.dependencies.Input('modes-metric-dropdown', 'value'),
                       dash.dependencies.Input('modes-plot-with-slider', 'clickData')])
        def update_mode_timeline(year_range, selected_modes, mode_detectors, mode_metric, click_data):
            self.mode_detectors = mode_detectors
            self.mode_daterange = year_range
            self.selected_modes = selected_modes
            self.mode_metric = mode_metric
            if click_data is not None:
                mode = click_data['points'][0]['x']
                mode_timeline_df = modes_df[modes_df['Filters/Gratings'].isin([mode])]


        app.run_server(debug=True)

    if __name__ == "__main__":
        from inspector import Inspector
        inspec = Inspector()
        inspec.generate_from_csv()
        inspec.load_dataframe_into_dash()

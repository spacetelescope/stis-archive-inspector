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
        mode_groups = [["G140L", "G140M", "G230M", "G230L"],
                       ["G230LB", "G230MB", "G430L", "G430M", "G750L", "G750M"],
                       ["E140M", "E140H", "E230M", "E230H"],
                       ["PRISM"]]
        labels = ["MAMA First Order Spectroscopy",
                  "CCD First Order Spectroscopy",
                  "MAMA Echelle Spectroscopy",
                  "MAMA Prism Spectroscopy"]

        modes_df = self.mast[["Filters/Gratings", "Start Time"]]
        start_times = np.array([datetime.datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                                for start_time in modes_df['Start Time']])

        # Convert to Start Times to Decimal Years
        modes_df['Decimal Year'] = [self.dt_to_dec(time) for time in start_times]
        modes_df = modes_df[["Filters/Gratings", "Decimal Year"]]
        p1_data = [go.Histogram(x=np.array(modes_df['Filters/Gratings'][modes_df['Filters/Gratings'].isin(grp)],
                                  dtype=str),  name=label) for grp, label in zip(mode_groups, labels)]

        # Plot 2: Apertures ------------------------------------------------
        apertures = np.array(self.mast["Apertures"], dtype=str)

        #Layout Dash App
        app = dash.Dash(__name__, external_stylesheets=self.stylesheets)
        app.layout = html.Div(children=[
            html.H1(children=f'{self.instrument} Archive Inspector'),

            html.Div(children='''
                Dash: A web application framework for Python.
            '''),

            dcc.Graph(
                id='plot-1',
                figure={
                    'data': p1_data,
                    'layout': go.Layout(title="Modes",
                                        barmode='group')
                }
            ),
            dcc.RangeSlider(id='modes-date-slider',
                            min=min(start_times).year,
                            max=max(start_times).year + 1,
                            step=1,
                            value=[min(start_times).year, max(start_times).year + 1]
            ),
            html.Div(id="output-container-modes-slider"),
            dcc.Graph(
                id='plot-2',
                figure={
                    'data': [
                        {'x': apertures, 'type': 'histogram', 'name': 'Modes'},
                    ],
                    'layout': {
                        'title': 'Apertures'
                    }
                }
            )
        ])

        # Callbacks
        @app.callback(dash.dependencies.Output('output-container-modes-slider', 'children'),
            [dash.dependencies.Input('modes-date-slider', 'value')])
        def update_output(value):
            return 'Showing results from years {}'.format(value)
        app.run_server(debug=True)

    if __name__ == "__main__":
        from inspector import Inspector
        inspec = Inspector()
        inspec.generate_from_csv()
        inspec.load_dataframe_into_dash()

import numpy as np
import pandas as pd
import datetime
import urllib.request
import urllib.parse
import dash
import dash_core_components as dcc
import dash_html_components as html


class Inspector:
    """Class for interactive inspection of the STIS archive"""
    def __init__(self, outdir='./', use_csv=False, gen_csv=True, datatype='S', instrument='STIS'):
        self.outdir = outdir
        self.use_csv = use_csv
        self.csv_name = "stis_archive.csv"
        self.gen_csv = gen_csv
        self.datatype = datatype
        self.instrument = instrument
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

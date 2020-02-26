import pandas as pd
import numpy as np
from datetime import datetime
from urllib import parse, request

from .server import app

def generate_dataframe_from_csv(csv_name):
    """Generate a Pandas DataFrame from an existing csv metadata file"""
    mast = pd.read_csv(csv_name, low_memory=False)
    mast = mast[mast.keys()[1:]]

    return mast


def generate_csv_from_mast(csv_name, outdir, datatype, instrument):
    """Generate a csv file of the STIS archive from querying MAST"""

     # Determine if we want 'science', 'calibration', or 'all' datasets:
    datatype = datatype.upper()
    assert datatype in ['S', 'C', '%','ALL'], "'datatype' is not a valid selection."
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
    for year in np.arange(1997, datetime.now().year + 1):
        print('Working on {}...'.format(year))
        data = [
            ('sci_instrume', instrument),
            ('sci_aec', datatype),
            ('sci_start_time', 'Jan 1 {} .. Jan 1 {}'.format(year, year + 1)),
            ('max_records', '25000'),
            ('ordercolumn1', 'sci_start_time'),
            ('outputformat', 'JSON'),
            ('selectedColumnsCsv', selectedColumnsCsv),
            ('nonull', 'on'),
            ('action', 'Search'), ]

        try:
            url_values = parse.urlencode(data)
            full_url = url + '?' + url_values
            # print (full_url)
            with request.urlopen(full_url) as response:
                json_file = response.read()

            # Convert to Pandas table:
            all_years.append(pd.read_json(json_file.decode()))
        except ValueError:
            pass  # Sad years with no data

    # Concatenate individual years together:
    mast = pd.concat(all_years)

    # Modify/add some rows:
    mast['Start Time'] = [datetime.strptime(
        x, '%Y-%m-%d %H:%M:%S') for x in mast['Start Time']]
    mast['obstype'] = [
        'Imaging' if 'MIR' in x else 'Spectroscopic' for x in mast['Filters/Gratings']]
    mast.loc[mast['Apertures'] == '50CORON', 'obstype'] = 'Coronagraphic'
    mast['Instrument Config'] = [x.strip()
                                    for x in mast['Instrument Config']]

    mast = mast[(mast['Operating Mode'] != 'ACQ') & (mast['Operating Mode'] != 'ACQ/PEAK')]
    mast.to_csv("stis_archive.csv")

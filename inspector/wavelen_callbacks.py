import numpy as np
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime

from .server import app
from .config import config
from .fetch_metadata import generate_dataframe_from_csv, generate_csv_from_mast
from .utils import dt_to_dec

outdir = config['inspector']['outdir']
csv_name = config['inspector']['csv_name']
instrument = config['inspector']['instrument']
mast = generate_dataframe_from_csv(outdir+csv_name)

wav_df = mast[["Central Wavelength","Start Time", "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in wav_df['Start Time']])

wav_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
wav_df = wav_df[["Central Wavelength","Decimal Year",
                 "obstype", "Instrument Config", "Exp Time"]]

# Wavelength Callbacks
@app.callback(Output('wavelength-histogram', 'figure'),
              [Input('wavelength-date-slider', 'value'),
               Input('wavelength-type-checklist', 'value'),
               Input('wavelength-detector-checklist', 'value'),
               Input('wavelength-metric-dropdown', 'value')])
def update_wavelength_figure(year_range, wav_obstype, wav_detectors, wav_metric):
    wav_daterange = year_range

    # Filter observations by obstype
    filtered_df = wav_df[(
        wav_df['obstype'].isin(wav_obstype))]
    # Filter observations by detector
    filtered_df = filtered_df[(
        filtered_df['Instrument Config'].isin(wav_detectors))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) & (
        filtered_df['Decimal Year'] <= year_range[1])]

    wav_data = []
    for detector in wav_detectors:
        detector_df = filtered_df[filtered_df['Instrument Config'] == detector]
        wav_data.append(go.Histogram(x=detector_df['Central Wavelength'],
        name=detector,
        nbinsx=10*len(wav_detectors),
        opacity=0.7))

    ylabel = "Counts"
    return {
        'data': wav_data,
        'layout': go.Layout(title=f"{instrument} Central Wavelength Usage", hovermode='closest',
                            xaxis={'title': "Wavelength (Angstroms)"},
                            yaxis={'title': ylabel},
                            bargap=0.2,
                            bargroupgap=0.1)
    }

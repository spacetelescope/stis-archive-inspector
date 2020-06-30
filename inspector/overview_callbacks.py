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
mast = generate_dataframe_from_csv(outdir+csv_name)

overview_df = mast[["Start Time", "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in overview_df['Start Time']])

overview_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
overview_df = overview_df[["Decimal Year",
                           "obstype", "Instrument Config", "Exp Time"]]

# Overview callbacks
@app.callback(Output('detector-pie-chart', 'figure'),
              [Input('detector-date-slider', 'value'),
              Input('detector-metric-dropdown','value')])
def update_detector_pie_figure(year_range, overview_metric):
    mode_daterange = year_range

    instrument = config['inspector']['instrument']

    # Filter observations by observation year (decimal)
    filtered_df = overview_df[(overview_df['Decimal Year'] >= year_range[0]) &
                              (overview_df['Decimal Year'] <= year_range[1])]
    # Filter modes by group
    if overview_metric == 'n-obs':
        n_tots = []
        detectors = np.sort(filtered_df['Instrument Config'].unique())
        for detector in detectors:
            n_tots.append(np.sum(filtered_df['Instrument Config'] == detector))
        print(detectors, n_tots)
        # A go.Histogram is better for here, but go.Bar is consistent with the other view in terms of layout so
        # it is the better choice in this case
        pie_data = [go.Pie(labels=detectors, values=n_tots, opacity=0.8,sort=False)]

    elif overview_metric == 'exptime':
        exp_tots = []
        detectors = np.sort(filtered_df['Instrument Config'].unique())
        for detector in detectors:
            exp_tots.append(np.sum(filtered_df['Exp Time'][filtered_df['Instrument Config'] == detector])/60/60)
        print(detectors, exp_tots)
        pie_data = [go.Pie(labels=detectors, values=exp_tots, opacity=0.8,sort=False)]

    return {
        'data': pie_data,
        'layout': go.Layout(title=f"Relative STIS Detector Usage", hovermode='closest')
    }

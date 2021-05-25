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

aperture_groups = config['apertures']['groups']
aperture_labels = config['apertures']['labels']

apertures_df = mast[["Apertures", "Start Time",
                     "obstype", "Instrument Config", "Exp Time"]].copy()
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in apertures_df['Start Time']])
# Convert to Start Times to Decimal Years
apertures_df.loc[:,'Decimal Year'] = [
    dt_to_dec(time) for time in start_times]
apertures_df = apertures_df[[
    "Apertures", "Decimal Year", "obstype", "Instrument Config", "Exp Time"]]

aperture_groups = config['apertures']['groups']
aperture_labels = config['apertures']['labels']

mode_detectors = ["STIS/CCD", "STIS/NUV-MAMA", "STIS/FUV-MAMA"]


# Aperture Callbacks
@app.callback(Output('apertures-plot-with-slider', 'figure'),
            [Input('apertures-date-slider', 'value'),
            Input('apertures-type-checklist', 'value'),
            Input('apertures-detector-checklist', 'value'),
            Input('apertures-metric-dropdown', 'value')])
def update_aperture_figure(year_range, aperture_obstype, aperture_detectors, aperture_metric):
    aperture_daterange = year_range

    # Filter observations by obstype
    filtered_df = apertures_df[(apertures_df['obstype'].isin(aperture_obstype))]
    # Filter observations by detector
    filtered_df = filtered_df[(filtered_df['Instrument Config'].isin(aperture_detectors))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) & (filtered_df['Decimal Year'] <= year_range[1])]

    # Filter apertures by group
    filtered_df = filtered_df[['Apertures', "Exp Time"]]
    ylabel=''
    n_tots = []
    filtered_groups = []  # Need this for avoiding empty bars in plotting
    for grp, label in zip(aperture_groups, aperture_labels):
        # grp is a list of apertures, label is the category
        aperture_n_tots = []
        for aperture in grp:
            if aperture_metric == "n-obs":
                n_tot = len(filtered_df[filtered_df['Apertures'].isin([aperture])])
                aperture_n_tots.append(n_tot)
                ylabel = "Number of Observations"
            else:
                n_tot = np.sum(filtered_df['Exp Time'][filtered_df['Apertures'].isin([aperture])])
                aperture_n_tots.append(n_tot/60/60)
                ylabel = "Total Exposure Time (Hours)"

        new_grp = np.array(grp)[np.array(aperture_n_tots) != 0.0]
        aperture_n_tots = np.array(aperture_n_tots)[np.array(aperture_n_tots) != 0.0]
        n_tots.append(aperture_n_tots)
        filtered_groups.append(list(new_grp))

    # A go.Histogram is better for here, but go.Bar is consistent with the other view in terms of layout so
    # it is the better choice in this case
    aper_data = [go.Bar(x=grp, y=n, name=label, opacity=0.8)
                     for grp, n, label in zip(filtered_groups, n_tots, aperture_labels)]

    return {
        'data': aper_data,
        'layout': go.Layout(title=f"{instrument} Aperture Usage", hovermode='closest',
                            xaxis={'title': 'Aperture'},
                            yaxis={'title': ylabel})
            }

@app.callback(Output('aperture-timeline', 'figure'),
            [Input('apertures-date-slider', 'value'),
            Input('apertures-metric-dropdown', 'value'),
            Input('apertures-plot-with-slider', 'clickData'),
            Input("apertures-type-checklist", 'value')])
def update_aperture_timeline(year_range, aperture_metric, click_data, aperture_obstype):
    aperture_daterange = year_range
    bins = np.arange(aperture_daterange[0], aperture_daterange[1]+1, 1)
    if click_data is not None:
        aperture = click_data['points'][0]['x']
    else:
        return {
            'data': None,
            'layout': go.Layout(title=f"Click on an aperture from the left plot", hovermode='closest')
        }

    # Filter observations by obstype
    filtered_df = apertures_df[(apertures_df['obstype'].isin(aperture_obstype))]
    # Filter observations by aperture
    filtered_df = filtered_df[(filtered_df['Apertures'].isin([aperture]))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) &
                              (filtered_df['Decimal Year'] <= year_range[1])]

    filtered_df = filtered_df[['Decimal Year', "Exp Time"]]
    ylabel=''
    n_tots = []
    for i, bin in enumerate(bins):
        if bin == bins[-1]:
            continue
        mask = (np.array(filtered_df['Decimal Year']) >= bins[i]) * \
                (np.array(filtered_df['Decimal Year']) <= bins[i+1])

        if aperture_metric == "n-obs":
            n_tots.append(len(filtered_df[mask]))
            ylabel = "Number of Observations"
        else:
            n_tots.append(np.sum(filtered_df['Exp Time'][mask])/60/60)
            ylabel = "Total Exposure Time (Hours)"
    timeline_data = [go.Bar(x=bins, y=n_tots, opacity=0.8)]

    return {
        'data': timeline_data,
        'layout': go.Layout(title=f"{aperture} Usage Timeline", hovermode='closest',
                                xaxis={'title': 'Aperture'},
                                yaxis={'title': ylabel})
    }

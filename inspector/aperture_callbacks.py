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
                     "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in apertures_df['Start Time']])
# Convert to Start Times to Decimal Years
apertures_df['Decimal Year'] = [
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
    if aperture_metric == 'n-obs':
        filtered_df = filtered_df['Apertures']  # Just look at apertures
        n_tots = []
        filtered_groups = []  # Need this for avoiding empty bars in plotting
        for grp, label in zip(aperture_groups, aperture_labels):
            # grp is a list of apertures, label is the category
            aperture_n_tots = []
            for aperture in grp:
                n_tot = len(filtered_df[filtered_df.isin([aperture])])
                aperture_n_tots.append(n_tot)

            new_grp = np.array(grp)[np.array(aperture_n_tots) != 0.0]
            aperture_n_tots = np.array(aperture_n_tots)[np.array(aperture_n_tots) != 0.0]
            n_tots.append(aperture_n_tots)
            filtered_groups.append(list(new_grp))

        # A go.Histogram is better for here, but go.Bar is consistent with the other view in terms of layout so
        # it is the better choice in this case
        aper_data = [go.Bar(x=grp, y=n, name=label, opacity=0.8)
                     for grp, n, label in zip(filtered_groups, n_tots, aperture_labels)]
        ylabel = "Number of Observations"

    elif aperture_metric == 'exptime':
        filtered_df = filtered_df[['Apertures', "Exp Time"]]
        exp_tots = []
        filtered_groups = []  # Need this for avoiding empty bars in plotting
        for grp, label in zip(aperture_groups, aperture_labels):
            # grp is a list of apertures, label is the category
            aperture_exp_tots = []
            for aperture in grp:
                exp_tot = np.sum(filtered_df['Exp Time'][filtered_df['Apertures'].isin([aperture])])
                aperture_exp_tots.append(exp_tot)

            new_grp = np.array(grp)[np.array(aperture_exp_tots) != 0.0]
            aperture_exp_tots = np.array(aperture_exp_tots)[np.array(aperture_exp_tots) != 0.0]
            exp_tots.append(aperture_exp_tots)
            filtered_groups.append(list(new_grp))

        aper_data = [go.Bar(x=grp, y=exp, name=label, opacity=0.8)
                    for grp, exp, label in zip(filtered_groups, exp_tots, aperture_labels)]

        ylabel = "Total Exposure Time (Seconds)"

    return {
        'data': aper_data,
        'layout': go.Layout(title=f"{instrument} Aperture Usage", hovermode='closest',
                            xaxis={'title': 'Aperture'},
                            yaxis={'title': ylabel},
                            width=1600, height=800)
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
        aperture = "52X0.2"

    # Filter observations by obstype
    filtered_df = apertures_df[(apertures_df['obstype'].isin(aperture_obstype))]
    # Filter observations by aperture
    filtered_df = filtered_df[(filtered_df['Apertures'].isin([aperture]))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) &
                              (filtered_df['Decimal Year'] <= year_range[1])]

    # Filter apertures by group
    if aperture_metric == 'n-obs':
        filtered_df = filtered_df['Decimal Year']
        n_tots = []
        for i, bin in enumerate(bins):
            if bin == bins[-1]:
                continue
            mask = (np.array(filtered_df) >= bins[i]) * \
                   (np.array(filtered_df) <= bins[i + 1])
            n_tots.append(len(filtered_df[mask]))
        timeline_data = [go.Bar(x=bins, y=n_tots, opacity=0.8)]

        ylabel = "Number of Observations"
        return {
            'data': timeline_data,
            'layout': go.Layout(title=f"{aperture} Usage Timeline", hovermode='closest',
                                xaxis={'title': 'Observing Date'},
                                yaxis={'title': ylabel})
                }
    elif aperture_metric == 'exptime':

        filtered_df = filtered_df[['Decimal Year', "Exp Time"]]
        exp_tots = []
        for i, bin in enumerate(bins):
            if bin == bins[-1]:
                continue
            mask = (np.array(filtered_df['Decimal Year']) >= bins[i]) * \
                   (np.array(filtered_df['Decimal Year']) <= bins[i+1])
            exp_tots.append(np.sum(filtered_df['Exp Time'][mask]))
        timeline_data = [go.Bar(x=bins, y=exp_tots, opacity=0.8)]
        ylabel = "Total Exposure Time (Seconds)"

    return {
            'data': timeline_data,
            'layout': go.Layout(title=f"{aperture} Usage Timeline", hovermode='closest',
                                xaxis={'title': 'Aperture'},
                                yaxis={'title': ylabel})
            }

@app.callback(Output('aperture-pie-chart', 'figure'),
            [Input('apertures-date-slider', 'value'),
            Input('apertures-type-checklist', 'value'),
            Input('apertures-detector-checklist', 'value'),
            Input('apertures-metric-dropdown', 'value')])
def update_aperture_pie_figure(year_range, aperture_obstype, aperture_detectors, aperture_metric):
    aperture_daterange = year_range

    # Filter observations by obstype
    filtered_df = apertures_df[(apertures_df['obstype'].isin(aperture_obstype))]
    # Filter observations by detector
    filtered_df = filtered_df[(filtered_df['Instrument Config'].isin(mode_detectors))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) &
                              (filtered_df['Decimal Year'] <= year_range[1])]
    # Filter apertures by group
    if aperture_metric == 'n-obs':
        # Just look at filters and gratings
        filtered_df = filtered_df['Apertures']
        n_tots = []
        apertures = []
        for grp, label in zip(aperture_groups, aperture_labels):
            # grp is a list of apertures, label is the category
            for aperture in grp:
                n_tot = len(filtered_df[filtered_df.isin([aperture])])
                n_tots.append(n_tot)
                apertures.append(aperture)

        # A go.Histogram is better for here, but go.Bar is consistent with the other view in terms of layout so
        # it is the better choice in this case
        pie_data = [go.Pie(labels=apertures, values=n_tots, opacity=0.8)]

    elif aperture_metric == 'exptime':
        filtered_df = filtered_df[['Apertures', "Exp Time"]]
        exp_tots = []
        apertures = []  # Need this for avoiding empty bars in plotting
        for grp, label in zip(aperture_groups, aperture_labels):
            # grp is a list of apertures, label is the category
            aperture_exp_tots = []
            for aperture in grp:
                exp_tot = np.sum(filtered_df['Exp Time'][filtered_df['Apertures'].isin([aperture])])
                exp_tots.append(exp_tot)
                apertures.append(aperture)

        pie_data = [go.Pie(labels=apertures, values=exp_tots, opacity=0.8)]

    return {
            'data': pie_data,
            'layout': go.Layout(title=f"Relative Usage", hovermode='closest')
            }

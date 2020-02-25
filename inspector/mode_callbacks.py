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

modes_df = mast[["Filters/Gratings", "Start Time",
                 "obstype", "Instrument Config", "Exp Time"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in modes_df['Start Time']])
# Convert to Start Times to Decimal Years
modes_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
modes_df = modes_df[["Filters/Gratings", "Decimal Year",
                     "obstype", "Instrument Config", "Exp Time"]]

# Mode Callbacks
@app.callback(Output('modes-plot-with-slider', 'figure'),
             [Input('modes-date-slider', 'value'),
              Input('modes-type-checklist', 'value'),
              Input('modes-detector-checklist', 'value'),
              Input('modes-metric-dropdown', 'value')])
def update_mode_figure(year_range, selected_modes, mode_detectors, mode_metric):

    #mast = config['inspector']['mast']
    instrument = config['inspector']['instrument']

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

    # Filter observations by detector
    filtered_df = modes_df[(modes_df['Instrument Config'].isin(mode_detectors))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) & 
                              (filtered_df['Decimal Year'] <= year_range[1])]
    # Filter modes by group
    if mode_metric == 'n-obs':
        
        # Just look at filters and gratings
        filtered_df = filtered_df['Filters/Gratings']
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
        p1_data = [go.Bar(x=grp, y=n, name=label, opacity=0.8)
                   for grp, n, label in zip(filtered_groups, n_tots, mode_labels)]
        ylabel = "Number of Observations"

    elif mode_metric == 'exptime':
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

        p1_data = [go.Bar(x=grp, y=exp, name=label, opacity=0.8)
                   for grp, exp, label in zip(filtered_groups, exp_tots, mode_labels)]

        ylabel = "Total Exposure Time (Seconds)"

    return {
            'data': p1_data,
            'layout': go.Layout(title=f"{instrument} Mode Usage", hovermode='closest',
                                xaxis={'title': 'Mode'},
                                yaxis={'title': ylabel},
                                width=1600, height=800)
            }

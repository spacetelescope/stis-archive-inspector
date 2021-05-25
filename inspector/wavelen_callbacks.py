import numpy as np
from dash.dependencies import Input, Output, State
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

wav_df = mast[["Central Wavelength","Start Time", "obstype", "Instrument Config", "Exp Time", "Filters/Gratings"]].copy()
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in wav_df['Start Time']])

wav_df.loc[:,'Decimal Year'] = [dt_to_dec(time) for time in start_times]
wav_df = wav_df[["Central Wavelength","Decimal Year",
                 "obstype", "Instrument Config", "Exp Time", "Filters/Gratings"]]

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

    min_wav = min(filtered_df['Central Wavelength'])
    max_wav = max(filtered_df['Central Wavelength'])
    binsize = (max_wav - min_wav)/(15*np.sqrt(len(wav_detectors)))

    wav_data = []
    for detector in wav_detectors:
        detector_df = filtered_df[filtered_df['Instrument Config'] == detector]
        
        if wav_metric == 'n-obs':
            histbins = np.arange(
                min_wav, max_wav, binsize)
            counts, bin_edges = np.histogram(detector_df['Central Wavelength'], bins=histbins)

            wav_data.append(go.Bar(x=bin_edges, y = counts, opacity=0.7, name=detector))

        else: # mode metric is 'exptime'
            histbins = np.arange(
                min_wav, max_wav, binsize)
            counts, bin_edges = np.histogram(
                detector_df['Central Wavelength'], bins=histbins, weights=detector_df['Exp Time']/60./60.)

            wav_data.append(go.Bar(x=bin_edges, y=counts,
                                   opacity=0.7, name=detector))
            
            #wav_data[0].data = wav_data[0].data/60/60 # convert to hours

    if wav_metric == "n-obs":
        ylabel = "Counts"
    else:
        ylabel = "Total Exposure Time (Hours)"
    
    return {
        'data': wav_data,
        'bindata':{'start': min_wav, 
                   'end': max_wav,
                   'size': binsize},
        'layout': go.Layout(title=f"{instrument} Central Wavelength Usage", hovermode='closest',
                            xaxis={'title': "Wavelength (Angstroms)"},
                            yaxis={'title': ylabel},
                            bargap=0.1,
                            barmode='stack')
    }

@app.callback(Output('wavelength-bin-timeline', 'figure'),
              [Input('wavelength-date-slider', 'value'),
               Input('wavelength-metric-dropdown', 'value'),
               Input('wavelength-histogram', 'clickData'),
               Input("wavelength-type-checklist", 'value'),
               Input('wavelength-detector-checklist', 'value')],
               [State("wavelength-histogram", "figure")])
def update_wav_bin_timeline_figure(year_range, wav_metric, click_data,
wav_obstype, wav_detectors, figure):
    if click_data is not None:
        bincen = click_data['points'][0]['x']
    else:
        return {
            'data': None,
            'layout': go.Layout(title=f"Click on a wavelength bin from the left plot", hovermode='closest')
        }

    bins = np.arange(figure['bindata']['start'],
                    figure['bindata']['end'],
                    figure['bindata']['size'])

    timeline_bins = np.arange(year_range[0], year_range[1]+2, 1)

    bin_lower = bins[max(np.where(bins <= bincen)[0])]
    bin_upper = bins[min(np.where(bins > bincen)[0])]

    wav_daterange = year_range

    # Filter observations by obstype
    filtered_df = wav_df[(
        wav_df['obstype'].isin(wav_obstype))]
    # Filter observations by detector
    filtered_df = filtered_df[(
        filtered_df['Instrument Config'].isin(wav_detectors))]
    # Filter observations by observation year (decimal)
    filtered_df = filtered_df[(filtered_df['Decimal Year'] >= year_range[0]) & (
        filtered_df['Decimal Year'] <= year_range[1]+2)]
    # Filter observations by selected bin
    bin_df = filtered_df[(filtered_df['Central Wavelength'] >= bin_lower) & (
        filtered_df['Central Wavelength'] <= bin_upper)]

    # Find the unique instrument config/ cenwave combinations
    cenwave_df = bin_df[['Instrument Config','Central Wavelength',"Filters/Gratings"]].drop_duplicates(subset=['Filters/Gratings','Central Wavelength'])
    timeline_data = []
    ylabel = ''
    for index, row in cenwave_df.iterrows():
        inst, det = row['Instrument Config'].lower().split('/')
        if det != 'ccd':
            det = det.split('-')
            det = det[0]+det[1]
        mode = row['Filters/Gratings'].lower()
        cenwave = f'c{int(row["Central Wavelength"])}'

        #For each unique cenwave, search bin df for all observations and create a year on year line plot
        setting_df = bin_df[(bin_df['Filters/Gratings'] == row['Filters/Gratings']) & (bin_df['Central Wavelength'] == row['Central Wavelength'])]
        
        n_tots = []
        for i, time_bin in enumerate(timeline_bins):
            if time_bin == timeline_bins[-1]:
                continue
            mask = (np.array(setting_df['Decimal Year']) >= timeline_bins[i]) * \
                   (np.array(setting_df['Decimal Year']) <= timeline_bins[i + 1])
            if wav_metric == "n-obs":
                n_tots.append(len(setting_df[mask]))
                ylabel = "Number of Observations"
            else:
                n_tots.append(np.sum(setting_df['Exp Time'][mask])/60/60)
                ylabel = "Total Exposure Time (Hours)"

        timeline_data.append(go.Scatter(x=timeline_bins, y=n_tots,
                                  mode='lines',
                                  name=f'{inst},{det},{mode},{cenwave}',
                                  fill='tozeroy',
                                  opacity=0.6))

    
    return {
        'data': timeline_data,
        'layout': go.Layout(title=f"Cenwave Setting Usage in Bin", hovermode='closest',
                            xaxis={'title': "Year"},
                            yaxis={'title': ylabel,
                                   'type':'log'},
                            showlegend=True)
    }



    

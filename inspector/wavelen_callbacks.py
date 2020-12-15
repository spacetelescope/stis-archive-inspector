import numpy as np
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from datetime import datetime
import pysynphot
import math

from .server import app
from .config import config
from .fetch_metadata import generate_dataframe_from_csv, generate_csv_from_mast
from .utils import dt_to_dec

outdir = config['inspector']['outdir']
csv_name = config['inspector']['csv_name']
instrument = config['inspector']['instrument']
mast = generate_dataframe_from_csv(outdir+csv_name)

wav_df = mast[["Central Wavelength","Start Time", "obstype", "Instrument Config", "Exp Time", "Filters/Gratings"]]
start_times = np.array([datetime.strptime(str(start_time), "%Y-%m-%d %H:%M:%S")
                        for start_time in wav_df['Start Time']])

wav_df['Decimal Year'] = [dt_to_dec(time) for time in start_times]
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
    binsize = (max_wav - min_wav)/(30/np.sqrt(len(wav_detectors)))

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
                            bargap=0.2,
                            bargroupgap=0.1)
    }

@app.callback(Output('wav-throughputs', 'figure'),
              [Input('wavelength-date-slider', 'value'),
               Input('wavelength-metric-dropdown', 'value'),
               Input('wavelength-histogram', 'clickData'),
               Input("wavelength-type-checklist", 'value'),
               Input('wavelength-detector-checklist', 'value')],
               [State("wavelength-histogram", "figure")])
def update_wav_throughput_figure(year_range, wav_metric, click_data,
wav_obstype, wav_detectors, figure):
    if click_data is not None:
        bincen = click_data['points'][0]['x']
    else:
        bincen = 2300

    bins = np.arange(figure['bindata']['start'],
                     figure['bindata']['end'],
                     figure['bindata']['size'])

    bin_lower = bins[max(np.where(bins < bincen)[0])]
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
        filtered_df['Decimal Year'] <= year_range[1])]
    # Filter observations by selected bin
    bin_df = filtered_df[(filtered_df['Central Wavelength'] >= bin_lower) & (
        filtered_df['Central Wavelength'] <= bin_upper)]

    # Find the unique instrument config/ cenwave combinations
    cenwave_df = bin_df[['Instrument Config','Central Wavelength',"Filters/Gratings"]].drop_duplicates(subset=['Central Wavelength'])
    mjd = 'mjd#59038'
    bp_data = []
    for row in cenwave_df.iterrows():
        inst, det = row[1]['Instrument Config'].lower().split('/')
        if det != 'ccd':
            det = det.split('-')
            det = det[0]+det[1]
        mode = row[1]['Filters/Gratings'].lower()
        try:
            cenwave = f'c{int(row[1]["Central Wavelength"])}'
            bp = pysynphot.ObsBandpass(f'{inst},{det},{mode},{cenwave}')
            bp_mask = bp.throughput != 0.0
            bp_data.append(go.Scatter(x=bp.wave[bp_mask], y=bp.throughput[bp_mask], 
                                  mode='lines',
                                  name=f'{inst},{det},{mode},{cenwave}',
                                  fill='tozeroy',
                                  opacity=0.6))
                                  
        except ValueError:
            try:
                cenwave = f'i{int(row[1]["Central Wavelength"])}'
                bp = pysynphot.ObsBandpass(f'{inst},{det},{mode},{cenwave}')
                bp_mask = bp.throughput != 0.0
                bp_data.append(go.Scatter(x=bp.wave[bp_mask], y=bp.throughput[bp_mask],
                                      mode='lines',
                                      name=f'{inst},{det},{mode},{cenwave}',
                                      fill='tozeroy',
                                      opacity=0.6))
            except ValueError:
                print(f"failed to grab {det},{mode},{cenwave}")
                continue

    ylabel = "Throughputs"
    return {
        'data': bp_data,
        'layout': go.Layout(title=f"STIS Cenwave Throughputs", hovermode='closest',
                            xaxis={'title': "Wavelength (Angstroms)"},
                            yaxis={'title': ylabel,
                                   'type':'log'},
                            showlegend=True)
    }



    

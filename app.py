import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
import plotly.plotly as py
import plotly.graph_objs as go
import plotly
import os
import random
from flask import Flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import colorlover as cl
from dash.dependencies import Input, Output, State, Event

plotly.tools.set_credentials_file(username='straightsoup', api_key='aKCQfFygLpwLkuExldXI')

gf = pd.read_csv('Data/RankedHospitalInfo1.csv')
ziplocs = pd.read_csv('Data/zipcode.csv')
df = gf.copy()
df.set_index(['State', 'City', 'Hospital Name'], inplace=True)

mapbox_access_token = 'pk.eyJ1Ijoiam9leWtodWFuZyIsImEiOiJjamcwZ3RpZHkwcXBsMnpueDIwdW5iMHFxIn0.bI6yln2ALKcPSRYOgEaKNw'

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

def getHosRankings(usrMort, usrRatings, usrSaf, usrSpen, hosDf1):
    hosDf = hosDf1.copy()
    usrSum = float(usrMort + usrRatings + usrSaf + usrSpen)
    usrMort /= usrSum
    usrRatings /= usrSum
    usrSaf /= usrSum
    usrSpen /= usrSum

    hosDf['TotalRanking'] = 0
    for row in hosDf.itertuples():
        hosDf.loc[row.Index, 'TotalRanking'] = row[4] * usrMort + \
            row[5] * usrRatings + row[6] * usrSaf + row[7] * usrSpen
    hosDf['TotalRankingReranked'] = 0
    l_min = hosDf['TotalRanking'].min()
    l_max = hosDf['TotalRanking'].max()
    l_range = l_max - l_min
    if hosDf.iat[0, 10] != 0:
        for row in hosDf.itertuples():
            hosDf.loc[row.Index, 'TotalRankingReranked'] = 10 * (float(row[11]) - l_min) / l_range
    else:
        for row in hosDf.itertuples():
            hosDf.loc[row.Index, 'TotalRankingReranked'] = 10 * (float(row[10]) - l_min) / l_range
    hosDf.drop(['TotalRanking'], axis = 1)
    return hosDf


def getHosDistance(usrzip, numHospitals, hosDf1):
    hosDf = hosDf1.copy()
    for row in ziplocs.itertuples():
        if row[1] == usrzip:
            userState = row[3]
            userCity = row[2]
            userLat = row[4]
            userLon = row[5]
    stateHospitals = hosDf.xs(userState).copy()
    stateHospitals.loc[:, 'Distance'] = None
    for row in stateHospitals.itertuples():
        if row[8] is not None:
            stateHospitals.loc[row.Index, 'Distance'] = haversine(userLon, userLat, row[9], row[8])
    stateHospitals = stateHospitals.sort_values(['Distance'], ascending=True)
    if numHospitals <= len(stateHospitals) and numHospitals > 0:
        closeHospitals = stateHospitals[:numHospitals]
    return closeHospitals

app = dash.Dash(__name__, static_folder='assets')

app.scripts.config.serve_locally=True
app.css.config.serve_locally=True

app.layout = html.Div([
    html.Link(href='https://s3-ap-southeast-1.amazonaws.com/hospitalevaluationrankingsystem/main.css', rel='stylesheet'),
    html.Link(href='https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css', rel='stylesheet'),
    html.Link(href='https://fonts.googleapis.com/css?family=Raleway:400,400i,700,700i', rel = 'stylesheet'),
    html.Link(href='https://fonts.googleapis.com/css?family=Product+Sans:400,400i,700,700i', rel='stylesheet'),

    html.Div([
        html.H2("Hospital Evalutation Ranking System (HERS) -- IMMC18382352"),
        html.Img(src="https://s3-ap-southeast-1.amazonaws.com/hospitalevaluationrankingsystem/Logo.png"),
    ], className = 'banner'),
    html.Div([
        html.Div([
            html.Div([
                html.H3("Parameters")
            ], className='Title'),
            html.Div([
                html.P('Mortality Weight:'),
                dcc.Slider(
                    id='mortality-slider',
                    min=1,
					max=10,
					value=7,
                    step = 1,
					marks={str(mark): str(mark) for mark in range(1, 11)},
                    updatemode='drag'
                ),
            ], style={'width':400, 'margin':34}),

            html.Div([
                html.P('Patient Ratings Weight:'),
                dcc.Slider(
                    id='ratings-slider',
                    min=1,
					max=10,
					value=6,
                    step = 1,
					marks={str(mark): str(mark) for mark in range(1, 11)},
                    updatemode='drag'
                ),
            ], style={'width':400, 'margin':34}),

            html.Div([
                html.P('Patient Safety Weight:'),
                dcc.Slider(
                    id='safety-slider',
                    min=1,
					max=10,
					value=4,
                    step = 1,
					marks={str(mark): str(mark) for mark in range(1, 11)},
                    updatemode='drag'
                ),
            ], style={'width':400, 'margin':34}),

            html.Div([
                html.P('Cost Weight:'),
                dcc.Slider(
                    id='cost-slider',
                    min=1,
					max=10,
					value=5,
                    step = 1,
					marks={str(mark): str(mark) for mark in range(1, 11)},
                    updatemode='drag'
                ),
            ], style={'width':400, 'margin':34}),

            html.Div([
                dcc.Input(id='zip-id', value='', type='text', placeholder='Zip Code'),
                dcc.Input(id='num-hos', value='', type='text', placeholder='20'),
                html.Button(id='submit-button', n_clicks=0, children='Submit'),
            ], style={'width':900, 'margin':25})
        ], className='four columns wind-histogram'),


        html.Div([
            html.Div([
                html.H3("    Close Hospitals")
            ], className='Title'),

            dcc.Graph(id='close-hos-graph',
                        figure = {
                            'data': [
                                go.Scatter(
                                    x=random.sample(range(20), 10),
                                    y=random.sample(range(20), 10),
                                    mode='markers',
                                    opacity=0.7,
                                    marker={
                                        'size': 15,
                                        'line': {'width': 0.5, 'color': 'white'}
                                    },
                                )
                            ],
                            'layout': go.Layout(
                                xaxis={'type': 'linear', 'title': 'Distance (km)'},
                                yaxis={'title': 'Rankings'},
                                margin={'l': 100, 'b': 50, 't': 10, 'r': 10},
                                legend={'x': 0, 'y': 1},
                                hovermode='closest'
                            )
                        }
                ),
        ], className='eight columns wind-polar')
    ], className='row wind-histo-polar'),
    html.P(''),
    html.Div([
        html.Div([
            html.H3("Table")
        ], className='Title'),
        html.Div(html.P('')),
        html.Div([
            dt.DataTable(
                rows=[{}],
                filterable=False,
                editable=False,
                sortable=True,
                columns=['Hospital Name', 'ZIP Code', 'City', 'Ratings', 'Distance'],
                id='hos-table'
            ),
        ], className = 'twelve columns wind-histogram'),
        html.Div(html.P(''))
    ], className='row wind-speed-row'),
    html.P(''),
    html.Div([
        html.Div([
            html.H3("Hospital Map")
        ], className='Title'),
        html.Div([
            dcc.Graph(id='hos-map',
                      figure = {
                          'data': [
                              go.Scattermapbox(
                                  lat=['40.7128'],
                                  lon=['-74.0060'],
                                  mode='markers',
                                  marker=go.Marker(
                                      size=14,
                                      color='rgb(255, 68, 58)'
                                  )
                              )
                          ],
                          'layout': go.Layout(
                              autosize=True,
                              height=750,
                              margin=go.Margin(l=0, r=0, t=0, b=0),
                              hovermode='closest',
                              mapbox=dict(
                                  accesstoken=mapbox_access_token,
                                  bearing=0,
                                  center=dict(
                                        lat=40.7128,
                                        lon=-74.0060
                                    ),
                                  pitch=0,
                                  zoom=12
                                  )
                          )
                    }
                )
        ], className = 'twelve columns wind-speed')
    ], className='row wind-speed-row')
], style={'padding': '0px 10px 15px 10px',
          'marginLeft': 'auto', 'marginRight': 'auto', "width": "1600px",
          'boxShadow': '0px 0px 5px 5px rgba(204,204,204,0.4)'})

@app.callback(
    Output('close-hos-graph', 'figure'),
    [Input('submit-button', 'n_clicks')],
    [State('mortality-slider', 'value'),
     State('ratings-slider', 'value'),
     State('safety-slider', 'value'),
     State('cost-slider', 'value'),
     State('zip-id', 'value'),
     State('num-hos', 'value')]
)
def update_figure(n_clicks,mortalityWeight, ratingsWeight, safetyWeight, costWeight, zipCodeNumber, numHos):

    b = getHosDistance(int(zipCodeNumber), int(numHos), df)

    a = getHosRankings(mortalityWeight, ratingsWeight, safetyWeight, costWeight, b)
    a = a.reset_index()
    a = a.sort_values(['TotalRankingReranked'], ascending=False)
    colorVal = ['#ff7f7f']*int(numHos)
    colorVal[0] = '#ff0000'
    colorVal[1] = '#ff1414'
    colorVal[2] = '#ff2828'
    colorVal[3] = '#ff2a2a'
    colorVal[4] = '#ff5454'


    return {
        'data': [
            go.Scatter(
                x=a['Distance'],
                y=a['TotalRankingReranked'],
                text=a['Hospital Name'],
                customdata = a['Hospital Name'],
                mode='markers',
                opacity=1,
                marker={
                    'size': 15,
                    'line': {'width': 0.5, 'color': 'white'},
                    'color': colorVal
                },
            )
        ],
        'layout': go.Layout(
            xaxis={'type': 'linear', 'title': 'Distance (km)'},
            yaxis={'title': 'Rankings'},
            margin={'l': 100, 'b': 50, 't': 10, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest'
        )
    }

@app.callback(
    Output('hos-table', 'rows'),
    [Input('submit-button', 'n_clicks')],
    [State('mortality-slider', 'value'),
     State('ratings-slider', 'value'),
     State('safety-slider', 'value'),
     State('cost-slider', 'value'),
     State('zip-id', 'value'),
     State('num-hos', 'value')]
)
def update_figure(n_clicks,mortalityWeight, ratingsWeight, safetyWeight, costWeight, zipCodeNumber, numHos):

        b = getHosDistance(int(zipCodeNumber), int(numHos), df)

        a = getHosRankings(mortalityWeight, ratingsWeight, safetyWeight, costWeight, b)
        a = a.reset_index()
        a = a.drop(['TotalRanking', 'MortalityRanked', 'PatientRanked', 'County Name', 'PSIRanked', 'SpendingRanked', 'Longitude', 'Latitude', 'Phone Number'], axis=1)
        a.columns = ['City', 'Hospital Name', 'ZIP Code', 'Ratings', 'Distance']

        return a.to_dict('records')

@app.callback(
    Output('hos-map', 'figure'),
    [Input('submit-button', 'n_clicks')],
    [State('mortality-slider', 'value'),
     State('ratings-slider', 'value'),
     State('safety-slider', 'value'),
     State('cost-slider', 'value'),
     State('zip-id', 'value'),
     State('num-hos', 'value')]
)
def update_figure(n_clicks,mortalityWeight, ratingsWeight, safetyWeight, costWeight, zipCodeNumber, numHos):
    b = getHosDistance(int(zipCodeNumber), int(numHos), df)

    a = getHosRankings(mortalityWeight, ratingsWeight, safetyWeight, costWeight, b)
    a = a.reset_index()

    for row in ziplocs.itertuples():
        if row[1] == zipCodeNumber:
            usrLat = row[4]
            usrLon = row[5]

    return {
        'data': [
            go.Scattermapbox(
                lat=a['Latitude'],
                lon=a['Longitude'],
                mode='markers',
                marker=go.Marker(
                    size=14,
                    color='rgb(255, 68, 58)'
                ),
                hoverinfo="text",
                text=a['Hospital Name'],
            )
        ],
        'layout': go.Layout(
            autosize=True,
            height=750,
            margin=go.Margin(l=0, r=0, t=0, b=0),
            hovermode='closest',
            mapbox=dict(
                accesstoken=mapbox_access_token,
                bearing=0,
                center=dict(
                    lat=a['Latitude'][0],
                    lon=a['Longitude'][0]
                ),
            pitch=0,
            zoom=12
            )
        )
    }

if __name__ == '__main__':
    app.server.run(port=4000, host='127.0.0.1')

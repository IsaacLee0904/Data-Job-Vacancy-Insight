import os
from dash import dcc, html
from dash.dependencies import Input, Output
from dashboard_app import app
from pages import home_pages, education_pages, geography_pages, stack_pages

server = app.server

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/education':
        return education_pages.layout
    elif pathname == '/geography':
        return geography_pages.layout
    elif pathname == '/stack':
        return stack_pages.layout
    else:
        return home_pages.layout


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9100))
    app.run_server(debug=False, host='0.0.0.0', port=port)
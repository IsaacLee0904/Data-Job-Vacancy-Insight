## import packages
# import necessary libraries
import sys, os 
from datetime import datetime, timedelta
import pandas as pd
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from flask import Flask, send_from_directory
import plotly.express as px

# set up project root path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

# import modules
from utils.log_utils import set_logger
from utils.front_end_utils import load_css_files
from utils.dashboard_utils import FetchReportData

## Load data
# define fetch functions
def fetch_openings_statistics_for_dashboard(fetcher, crawl_date):
    """
    Fetch openings statistics metrics from the database for a given crawl date and verify if the data matches the crawl date.
    """
    data = fetcher.fetch_openings_statistics_metrics(crawl_date)
    if not data.empty:
        # Verify that all records have the correct crawl date
        if all(data['crawl_date'] == crawl_date):
            return data
        else:
            fetcher.logger.error("Data inconsistency detected: 'crawl_date' does not match the provided date.")
            # Return only consistent data or handle inconsistency here
            return pd.DataFrame()
    else:
        fetcher.logger.info("No data available for openings statistics on the provided crawl date.")
        return pd.DataFrame()

def fetch_historical_total_openings_for_dashboard(fetcher):
    """
    Fetch historical total openings data and ensure it includes the newest crawl date.
    """
    data = fetcher.fetch_openings_history()
    if not data.empty:
        newest_crawl_date = fetcher.get_newest_crawl_date()
        max_crawl_date = data['crawl_date'].max()
        if pd.to_datetime(max_crawl_date) == pd.to_datetime(newest_crawl_date):
            return data
        else:
            fetcher.logger.error(f"Data inconsistency detected: The newest data in historical openings (date: {max_crawl_date}) does not match the newest crawl date ({newest_crawl_date}).")
            return pd.DataFrame()  # Return empty DataFrame in case of inconsistency
    else:
        fetcher.logger.info("No historical data available for total openings.")
        return pd.DataFrame()

def fetch_data_role_for_dashboard(fetcher, crawl_date):
    """
    Fetch data role data from the database for a given crawl date and verify if the data matches the crawl date.
    """
    data = fetcher.fetch_data_role(crawl_date)
    if not data.empty:
        # Ensure date formats are consistent for comparison
        data['crawl_date'] = pd.to_datetime(data['crawl_date']).dt.date
        provided_date = pd.to_datetime(crawl_date).date()

        # Verify that all records have the correct crawl date
        if all(data['crawl_date'] == provided_date):
            return data
        else:
            fetcher.logger.error("Data inconsistency detected: 'crawl_date' does not match the provided date.")
            # Return only consistent data or handle inconsistency here
            return pd.DataFrame()
    else:
        fetcher.logger.info("No data available for data roles on the provided crawl date.")
        return pd.DataFrame()

def fetch_data_tools_for_dashboard(fetcher, crawl_date):
    """
    Fetch data tools data from the database for a given crawl date and verify if the data matches the crawl date.
    """
    data = fetcher.fetch_data_tool(crawl_date)
    if not data.empty:
        # Ensure date formats are consistent for comparison
        data['crawl_date'] = pd.to_datetime(data['crawl_date']).dt.date
        provided_date = pd.to_datetime(crawl_date).date()

        # Verify that all records have the correct crawl date
        if all(data['crawl_date'] == provided_date):
            fetcher.logger.info("Data tools information successfully validated for the provided crawl date.")
            return data
        else:
            fetcher.logger.error("Data inconsistency detected: 'crawl_date' does not match the provided date in data tools information.")
            # Optionally, return only consistent data or handle inconsistency here
            consistent_data = data[data['crawl_date'] == provided_date]
            return consistent_data if not consistent_data.empty else pd.DataFrame()
    else:
        fetcher.logger.info(f"No data tools information available for the crawl date: {crawl_date}.")
        return pd.DataFrame()

def fetch_openings_company_for_dashboard(fetcher, crawl_date):
    """
    Fetch job vacancy data from the database for a given crawl date and verify if the data matches the crawl date.
    """
    data = fetcher.fetch_openings_company(crawl_date)
    if not data.empty:
        # Ensure date formats are consistent for comparison
        data['crawl_date'] = pd.to_datetime(data['crawl_date']).dt.date
        provided_date = pd.to_datetime(crawl_date).date()

        # Verify that all records have the correct crawl date
        if all(data['crawl_date'] == provided_date):
            fetcher.logger.info("Job vacancy information successfully validated for the provided crawl date.")
            return data
        else:
            fetcher.logger.error("Data inconsistency detected: 'crawl_date' does not match the provided date in job vacancy data.")
            # Optionally, return only consistent data or handle inconsistency here
            consistent_data = data[data['crawl_date'] == provided_date]
            return consistent_data if not consistent_data.empty else pd.DataFrame()
    else:
        fetcher.logger.info(f"No job vacancy data available for the crawl date: {crawl_date}.")
        return pd.DataFrame()

def fetch_taiepi_area_openings_for_dashboard(fetcher, crawl_date):
    """
    Fetch job vacancy data for the Taipei and New Taipei area from the database for a given crawl date and verify if the data matches the crawl date.
    """
    data = fetcher.fetch_taiepi_area_openings(crawl_date)
    if not data.empty:
        # Ensure date formats are consistent for comparison
        data['crawl_date'] = pd.to_datetime(data['crawl_date']).dt.date
        provided_date = pd.to_datetime(crawl_date).date()

        # Verify that all records have the correct crawl date
        if all(data['crawl_date'] == provided_date):
            fetcher.logger.info("Job vacancy information for the Taipei area successfully validated for the provided crawl date.")
            return data
        else:
            fetcher.logger.error("Data inconsistency detected: 'crawl_date' does not match the provided date in job vacancy data for the Taipei area.")
            # Optionally, return only consistent data or handle inconsistency here
            consistent_data = data[data['crawl_date'] == provided_date]
            return consistent_data if not consistent_data.empty else pd.DataFrame()
    else:
        fetcher.logger.info(f"No job vacancy data available for the Taipei area on the crawl date: {crawl_date}.")
        return pd.DataFrame()

# Integrate the fetch functions into the load_home_page_data function
def load_home_page_data():
    """
    Load reporting data from the database for the dashboard home page.
    """
    # Setup logger
    logger = set_logger()

    # Initialize the FetchReportData class to handle database operations
    fetcher = FetchReportData(logger)

    # Get the newest crawl date
    newest_crawl_date = fetcher.get_newest_crawl_date()

    # Fetch the data for different metrics from the home page
    if newest_crawl_date:
        logger.info(f"Fetching data for the date: {newest_crawl_date}")
        # load data for openings statistics metrics
        openings_statistics = fetch_openings_statistics_for_dashboard(fetcher, newest_crawl_date)
        # load data for historical total openings line chart
        historical_total_openings = fetch_historical_total_openings_for_dashboard(fetcher)
        # load data for data role pie plot
        data_role = fetch_data_role_for_dashboard(fetcher, newest_crawl_date)
        # load data for data tools top 3 
        data_tools = fetch_data_tools_for_dashboard(fetcher, newest_crawl_date)
        # load data for openings company top 5
        openings_company = fetch_openings_company_for_dashboard(fetcher, newest_crawl_date)
        # load data fro taiepi area openings
        taiepi_area_openings = fetch_taiepi_area_openings_for_dashboard(fetcher, newest_crawl_date)
        
    else:
        logger.info("No newest crawl date available.")

    # Close the database connection safely
    if fetcher.connection:
        fetcher.connection.close()
        logger.info("Database connection closed.")
    
    return openings_statistics, historical_total_openings, data_role, data_tools, openings_company, taiepi_area_openings

## Plotting Data
# Create the data role pie chart
def create_data_role_pie(data_role):
    data_role_pie = px.pie(
        data_role, 
        values='count', 
        names='data_role', 
        hole=0.75,
        color='data_role',  
        color_discrete_map={
            'Data Analyst': '2E2E48',  
            'Data Engineer': '3C4A8A',  
            'Machine Learning Engineer': '5A6ACF',
            'Data Scientist': '8593ED',
            'Business Analyst': 'A5B3FF',
            'BI Engineer': 'C7CEFF',
            'Data Architect': 'E6ECFF',
        },
        custom_data=data_role[['data_role', 'count']]
    )

    data_role_pie.update_traces(textinfo='none', 
                                hovertemplate='<span style="font-size:12px; color:white; font-weight:bold;">%{customdata[0][0]}</span><br>' +
                                              '</br>'+
                                              '<span style="font-size:15px; color:white; font-weight:bold;">%{percent} (%{customdata[0][1]})</span><extra></extra>')

    # count date for the pie chart title
    crawl_date = data_role['crawl_date'][0]
    next_monday = crawl_date + timedelta(days=(7 - crawl_date.weekday()))

    title_text = f"From {crawl_date.strftime('%d')} - {next_monday.strftime('%d %B, %Y')}"
    data_role_pie.update_layout(
        width=350,  # setup chart width
        height=350,  # setup chart height
        margin=dict(l=20, r=20, t=30, b=20),  # setup chart margin
        paper_bgcolor='rgba(0,0,0,0)',  # setup chart paper background color as transparent
        plot_bgcolor='rgba(0,0,0,0)',  # setup chart plot background color as transparent
        showlegend=False,  # hide legend
        title={
            'text': title_text,  # setup chart title
            'font': {
                'size': 14,  # setup chart title font size
                'color': '#737b8b'  # setup chart title font color
            },
            'x': 0.25,  # setup chart title horizontal position
            'y': 0.98,  # setup chart title vertical position
            'xanchor': 'center',  # setup chart title horizontal alignment
            'yanchor': 'top'  # setup chart title vertical alignment
        },
        hoverlabel=dict(
            bgcolor="#2E2E48", # setup hover label background color
            font_size=12,      # setup hover label font size
            font_color="white",# setup hover label font color
            bordercolor="#2E2E48" # setup hover label border color
        )
    )
    return data_role_pie

# Create the historical total openings line chart
def create_historical_total_openings_line_chart(historical_total_openings):
    historical_total_openings_line = px.line(
        historical_total_openings, 
        x='crawl_date', 
        y='total_openings', 
        labels={'crawl_date': 'Date', 'total_openings': 'Total Openings'},
        color_discrete_sequence=['#ffa726'],
        template='plotly_white',
    )

    historical_total_openings_line.update_layout(
        width=750,  # setup chart width
        height=400,  # setup chart height
        margin=dict(l=95, r=20, t=143, b=50),  # setup chart margin
        paper_bgcolor='rgba(0,0,0,0)',  # setup chart paper background color as transparent
        plot_bgcolor='rgba(0,0,0,0)',  # setup chart plot background color as transparent
        legend=dict(
            orientation="h",  # Horizontal orientation
            x=-0.05,  # Horizontal position (left of the chart)
            y=-0.2,  # Vertical position (below the chart)
            xanchor="left",  # Anchor the legend horizontally at the left
            yanchor="top"  # Anchor the legend vertically at the top
        )
    )

    historical_total_openings_line.update_traces(
        mode='lines+text',  # Add 'text' to show data labels
        line={'width': 2.5}, 
        showlegend=True,  # Show legend
        name='Total Openings',  # Set legend name
        hoverinfo='all',  # Ensure hover information is shown
        hovertemplate='<span style="font-size:15px; font-weight:bold;">%{x|%Y-%m-%d}<br><br>Total openings : %{y}<extra></extra>',  # Custom hover template
        text=historical_total_openings['total_openings'],  # Add data labels
        textposition='middle left'  # Position data labels above the points
    )

    historical_total_openings_line.update_layout(
        hoverlabel=dict(
            bgcolor="#ffa726",  
            font_size=12,      
            font_color="white",
            bordercolor="#ffa726" 
        )
    )

    # Generate tick values for x-axis (e.g., every 2 weeks)
    tickvals = historical_total_openings['crawl_date'][::1]

    # Update x-axis to show every week and only show 12 points
    historical_total_openings_line.update_xaxes(
        dtick="W1",  # Set dtick to "W1" for weekly ticks
        tickformat="%b %d",  # Format to show month and day
        tickmode='array',  # Use array mode to specify tick values
        title='',  # Hide x-axis title
        tickvals=tickvals,  # Specify tick values
        showgrid=False,  # Hide grid lines for x-axis
        showline=True,  # Show x-axis line
        linewidth=1,  # Set the width of the x-axis line
        linecolor='lightgrey',  # Set the color of the x-axis line
        tickfont=dict(
            color='#737b8b'  # Set the color of the date labels
        )
    )

    # Update y-axis to hide grid lines
    historical_total_openings_line.update_yaxes(
        showgrid=True,  # Show grid lines for y-axis
        title='',  # Hide y-axis title
        showticklabels=False  # Hide y-axis tick labels
    )

    return historical_total_openings_line

# Extract openings statistics
def extract_openings_statistics(openings_statistics):
    total_openings = openings_statistics['total_openings'].values[0]
    total_openings_change = openings_statistics['total_openings_change_pct'].values[0]
    new_openings = openings_statistics['new_openings_count'].values[0]
    new_openings_change = openings_statistics['new_openings_change_pct'].values[0]
    fill_rate = openings_statistics['fill_rate'].values[0]
    fill_rate_change = openings_statistics['fill_rate_change_pct'].values[0]
    attf = openings_statistics['average_weeks_to_fill'].values[0]
    attf_change = openings_statistics['average_weeks_to_fill_change_pct'].values[0]

    return {
        'total_openings': total_openings,
        'total_openings_change': total_openings_change,
        'new_openings': new_openings,
        'new_openings_change': new_openings_change,
        'fill_rate': fill_rate,
        'fill_rate_change': fill_rate_change,
        'attf': attf,
        'attf_change': attf_change,
    }

## Web Application Configuration
# Sidebar Configuration
def sidebar():
    return html.Div(
        className="sidebar",
        children=[
            html.Div(
                className="profile",
                children=[
                    html.Div("MidnightGuy", className="watermark"),
                    html.Div(
                        className="watermark-icon",
                        children=[
                            html.Div(
                                className="watermark-icon-group",
                                children=[
                                    html.Div(className="watermark-icon-1"),
                                    html.Div(className="watermark-icon-2")
                                ]
                            )
                        ]
                    )
                ]
            ),
            html.Div(
                className="creator-info",
                children=[
                    html.Div("Isaac Lee", className="creator-name"),
                    html.Div("Data Engineer", className="creator-title")
                ]
            ),
            html.Div(
                className="home-component",
                children=[
                    html.Div(
                        className="selection-home",
                        children=[
                            html.A("Home", href="/", className="homepage-text"),
                            html.Img(src="assets/icons/home.svg", className="selection-icon")
                        ]
                    ),
                    # html.Div(className="selected-rectangle")
                ]
            ),
            html.Div(
                className="stack-component",
                children=[
                    html.Div(
                        className="selection-stack",
                        children=[html.A("Stack", href="/stack", className="stack-text")]
                    ),
                    html.Img(src="assets/icons/stack.svg", className="selection-icon")
                ]
            ),
            html.Div(
                className="geography-component",
                children=[
                    html.Div(
                        className="selection-geography",
                        children=[html.A("Geography", href="/geography", className="geography-text")]
                    ),
                    html.Img(src="assets/icons/geography.svg", className="selection-icon")
                ]
            ),
            html.Div(
                className="education-component",
                children=[
                    html.Div(
                        className="selection-education",
                        children=[html.A("Education", href="/education", className="education-text")]
                    ),
                    html.Img(src="assets/icons/education.svg", className="selection-icon")
                ]
            ),
            html.Div(
                className="connection-info",
                children=[
                    html.Div(
                        className="connection-info-group",
                        children=[
                            html.Div(className="connection-info-shape"),
                            html.Div(
                                className="connection-info-title",
                                children=[html.Div("About Author :", className="connection-info-title-text")]
                            ),
                            html.Div(
                                className="github",
                                children=[html.A("Github", href="https://github.com/IsaacLee0904", className="connection-info-content")]
                            ),
                            html.Div(
                                className="linkedin",
                                children=[html.A("Linkedin", href="https://www.linkedin.com/in/isaac-lee-459a15143/", className="connection-info-content")]
                            ),
                            html.Div(
                                className="email",
                                children=[html.A("Email", href="mailto:hool19965401@gmail.com", className="connection-info-content")]
                            ),
                            html.Img(src="assets/icons/github.svg", className="github-icon"),
                            html.Img(src="assets/icons/linkedin.svg", className="linkedin-icon"),
                            html.Img(src="assets/icons/email.svg", className="email-icon")
                        ]
                    )
                ]
            ),
            html.Div(
                className="project-source",
                children=[
                    html.Div(
                        className="project-source-group",
                        children=[html.A("project-source", href="https://github.com/IsaacLee0904/Data-Job-Vacancy-Insight", className="project-source-text")]
                    ),
                    html.Img(src="assets/icons/link.svg", className="link-icon")
                ]
            ),
            html.Div(
                className="profile-pic",
                children=[
                    html.Div(
                        className="profile-pic-shape",
                        children=[
                                html.Img(src="assets/img/profile.png", className="profile_img"),
                                html.Img(src="assets/img/sidebar_ellipse.svg", className="profile-ellipse-1")]
                    ),               
                ]
            ),
            html.Img(src="assets/img/sidebar_ellipse.png", className="profile-ellipse-2")
        ]
    )

# Change Icon
def get_change_icon(value):
        if value > 0:
            return html.Img(src="/assets/icons/arrow_up.svg", className="change-icon")
        else:
            return html.Img(src="/assets/icons/arrow_down.svg", className="change-icon")

# Page Content Configuration
def page_content():
    # Load data for the home page
    openings_statistics, historical_total_openings, data_role, data_tools, openings_company, taiepi_area_openings = load_home_page_data()

    # Extract statistics
    stats = extract_openings_statistics(openings_statistics)

    ## Create figure for the dashboard
    # Create the data role pie chart
    data_role_pie = create_data_role_pie(data_role)
    # Create the historical total openings line chart
    historical_total_openings_line = create_historical_total_openings_line_chart(historical_total_openings)

    return html.Div(
        className="page",
        children=[
            html.Div(
                className="div",
                children=[
                    html.Div(
                        className="overlap",
                        children=[
                            html.Div(
                                className="overlap-group",
                                children=[
                                    html.Hr(className="separator"),
                                    html.Hr(className="img")
                                ]
                            ),
                            html.Hr(className="separator-2"),
                            html.Div(
                                className="order-stats",
                                children=[
                                    html.Div("Openings in Taipei", className="title-data")
                                ]
                            ),
                            html.Div(
                                className="most-ordered",
                                children=[
                                    html.P("Top 5 Companies with Most Openings", className="title-data"),
                                    html.P("The companies that posted the highest number of job openings in the past week", className="desc")
                                ]
                            ),
                            html.Div(
                                className="rating",
                                children=[
                                    html.Div(
                                        className="overlap-2",
                                        children=[
                                            html.Div(
                                                className="overlap-3",
                                                children=[
                                                    html.Div(
                                                        className="chart",
                                                        children=[
                                                            html.Div(
                                                                className="overlap-group-2",
                                                                children=[
                                                                    html.Div(className="ellipse"),
                                                                    html.Img(className="ellipse-2", src="/assets/img/ellipse-17.svg")
                                                                ]
                                                            )
                                                        ]
                                                    ),
                                                    html.Div(
                                                        className="overlap-wrapper",
                                                        children=[
                                                            html.Div(
                                                                className="overlap-4",
                                                                children=[
                                                                    html.Div(className="ellipse-3"),
                                                                    html.Img(className="ellipse-4", src="/assets/img/ellipse-17-1.svg")
                                                                ]
                                                            )
                                                        ]
                                                    )
                                                ]
                                            ),
                                            html.Div(
                                                className="overlap-group-wrapper",
                                                children=[
                                                    html.Div(
                                                        className="overlap-5",
                                                        children=[
                                                            html.Div(className="ellipse-5"),
                                                            html.Img(className="ellipse-6", src="/assets/img/ellipse-17-2.svg")
                                                        ]
                                                    )
                                                ]
                                            )
                                        ]
                                    ),
                                    html.Div("Stacks of the week", className="title-data"),
                                    html.P("The most frequently required stacks in job openings for the week", className="text-wrapper")
                                ]
                            ),
                            html.Div(
                                className="order-time",
                                children=[
                                    html.Div("Data Role", className="title-data"),
                                    dcc.Graph(figure=data_role_pie, className="data-role-pie-chart")
                                ]
                            ),
                            html.Div(
                                className="overlap-6",
                                children=[
                                    html.Div(
                                        className="revenue",
                                        children=[
                                            html.Div("Total Openings", className="title-data"),
                                            html.Div(
                                                className="icon-and-value",
                                                children=[
                                                    html.Img(className="iconly-bold-profile", src="/assets/icons/person.svg"),
                                                    html.Div(f"{stats['total_openings']}", className="total-openings-value")
                                                ]
                                            ),
                                            html.Div(
                                                className="percentage-info",
                                                children=[
                                                    html.Span(
                                                        [
                                                            get_change_icon(stats['total_openings_change']),
                                                            html.Span(f"{stats['total_openings_change']:.1f}%", style={"color": "red" if stats['total_openings_change'] > 0 else "green"}),
                                                            html.Span(" vs last week")
                                                        ], 
                                                        className="element-vs-last-days"
                                                    )
                                                ]
                                            ),
                                            html.Div("New Openings", className="title-data-2"),
                                            html.Div(
                                                className="icon-and-value",
                                                children=[
                                                    html.Img(className="iconly-bold-profile", src="/assets/icons/person.svg"),
                                                    html.Div(f"{stats['new_openings']}", className="new-openings-value")
                                                ]
                                            ),
                                            html.Div(
                                                className="element-vs-last-days-wrapper",
                                                children=[
                                                    html.Span(
                                                        [
                                                            get_change_icon(stats['new_openings_change']),
                                                            html.Span(f"{stats['new_openings_change']:.1f}%", style={"color": "red" if stats['new_openings_change'] > 0 else "green"}),
                                                            html.Span(" vs last week")
                                                        ], 
                                                        className="element-vs-last-days"
                                                    )
                                                ]
                                            ),
                                            html.Div("Fill Rate", className="title-data-3"),
                                            html.Div(f"{stats['fill_rate']:.2f} %", className="fill-rate-value"),
                                            html.Div(
                                                className="div-wrapper",
                                                children=[
                                                    html.Span(
                                                        [
                                                            get_change_icon(stats['fill_rate_change']),
                                                            html.Span(f"{stats['fill_rate_change']:.1f}%", style={"color": "red" if stats['fill_rate_change'] > 0 else "green"}),
                                                            html.Span(" vs last week")
                                                        ], 
                                                        className="element-vs-last-days"
                                                    )
                                                ]
                                            ),
                                            html.Div("ATTF", className="title-data-4"),
                                            html.Div(f"{stats['attf']:.2f} Weeks", className="attf-value"),
                                            html.Div(
                                                className="percentage-info-2",
                                                children=[
                                                    html.Span(
                                                        [
                                                            get_change_icon(stats['attf_change']),
                                                            html.Span(f"{stats['attf_change']:.1f}%", style={"color": "red" if stats['attf_change'] > 0 else "green"}),
                                                            html.Span(" vs last week")
                                                        ], 
                                                        className="element-vs-last-days"
                                                    )
                                                ]
                                            ),
                                            html.P("Openings Metrics in the Last 3 Month", className="sales-info"),
                                            dcc.Graph(figure=historical_total_openings_line, className="historical-total-openings-line-chart")
                                        ]
                                    ),
                                    html.Img(className="iconly-bold-profile-2", src="/assets/icons/person.svg")
                                ]
                            ),
                            html.Div("Company", className="text-wrapper-2"),
                            html.Div("Openings", className="text-wrapper-3"),
                            html.Div("#", className="text-wrapper-4"),
                            html.Hr(className="line"),
                            html.Hr(className="line-2"),
                            html.Hr(className="line-3"),
                            html.Hr(className="line-4"),
                            html.Hr(className="line-5"),
                            html.Div("01", className="text-wrapper-5"),
                            html.Div("02", className="text-wrapper-6"),
                            html.Div("03", className="text-wrapper-7"),
                            html.Div("04", className="text-wrapper-8"),
                            html.Div("05", className="text-wrapper-9"),
                            html.Div(className="group"),
                            html.Div(className="group-2"),
                            html.Div(className="group-3"),
                            html.Div(className="group-4"),
                            html.Div(className="group-5")
                        ]
                    ),
                    html.Div("Dashboard", className="title-page")
                ]
            )
        ]
    )

layout = html.Div(
    children=[
        sidebar(),
        page_content()
    ]
)

# Run the server
if __name__ == '__main__':
    app.run_server(debug=True)
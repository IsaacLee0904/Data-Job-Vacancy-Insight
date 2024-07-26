import sys, os
import re
from datetime import datetime, timedelta
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.log_utils import set_logger
from utils.database_utils import DatabaseConnector, DatabaseOperation

def connect_to_database(logger):
    """
    Establish a connection to the database and return the connector and operation objects.
    """
    connector = DatabaseConnector(logger)
    connection = connector.connect_to_db('render_deploy') # need to change while deploy
    db_operation = DatabaseOperation(connection, logger)
    logger.info("Connected to the database successfully.")
    return connection, db_operation

class FetchReportData:
    def __init__(self, logger):
        """
        Initialize the FetchReportData object by establishing a connection to the database.
        """
        self.connection, self.db_operation = connect_to_database(logger)
        self.logger = logger

    def execute_query(self, query):
        """
        Execute a SQL query and return the results.
        """
        try:
            cursor = self.connection.cursor()  # Creating a new cursor as needed
            cursor.execute(query)
            result = cursor.fetchall()  # Fetch all the results
            cursor.close()  # Close the cursor after fetching data
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute query {query}: {str(e)}")
            return None

    def fetch_all_tables(self):
        """
        Fetch all tables from the 'reporting_data' schema.
        """
        try:
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'reporting_data'"
            tables = self.execute_query(query)  # Use self.execute_query to call the local method
            if tables:
                self.logger.info("Fetched all table names successfully.")
            return tables
        except Exception as e:
            self.logger.error(f"Error fetching table names: {str(e)}")
            return []

    def get_newest_crawl_date(self):
        """
        Fetch the newest crawl date from the 'rpt_job_openings_metrics' table in the 'reporting_data' schema.
        """
        try:
            # Prepare the SQL query to fetch the maximum crawl date
            query = "SELECT MAX(crawl_date) AS newest_crawl_date FROM reporting_data.rpt_job_openings_metrics;"
            
            # Execute the query and fetch the result
            crawl_date_result = self.execute_query(query)  # Use self.execute_query to call the local method
            
            # Check if any result is returned
            if crawl_date_result and crawl_date_result[0][0] is not None:
                newest_crawl_date = crawl_date_result[0][0]  # Assume it's already a string
                return newest_crawl_date
            else:
                self.logger.info("No crawl dates found.")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching the newest crawl date: {str(e)}")
            return None

    def fetch_openings_statistics_metrics(self, crawl_date):
        """
        Fetch data for openings statistics metrics within the 'reporting_data' schema using a given crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    AAAA.total_openings
                    , COALESCE(((AAAA.total_openings - AAAA.prev_total_openings) / NULLIF(CAST(AAAA.prev_total_openings AS FLOAT), 0)) * 100.0, 0) AS total_openings_change_pct
                    , AAAA.closed_openings_count
                    , COALESCE(((AAAA.closed_openings_count - AAAA.prev_closed_openings_count) / NULLIF(CAST(AAAA.prev_closed_openings_count AS FLOAT), 0)) * 100.0, 0) AS closed_openings_change_pct
                    , AAAA.new_openings_count
                    , COALESCE(((AAAA.new_openings_count - AAAA.prev_new_openings_count) / NULLIF(CAST(AAAA.prev_new_openings_count AS FLOAT), 0)) * 100.0, 0) AS new_openings_change_pct
                    , AAAA.fill_rate
                    , COALESCE(((AAAA.fill_rate - AAAA.prev_fill_rate) / NULLIF(CAST(AAAA.prev_fill_rate AS FLOAT), 0)) * 100.0, 0) AS fill_rate_change_pct
                    , AAAA.average_weeks_to_fill
                    , COALESCE(((AAAA.average_weeks_to_fill - AAAA.prev_average_weeks_to_fill) / NULLIF(CAST(AAAA.prev_average_weeks_to_fill AS FLOAT), 0)) * 100.0, 0) AS average_weeks_to_fill_change_pct
                    , AAAA.crawl_date
                FROM(
                    SELECT 
                        AAA.total_openings
                        , LEAD(AAA.total_openings) OVER (ORDER BY AAA.crawl_date DESC) AS prev_total_openings
                        , AAA.closed_openings_count
                        , LEAD(AAA.closed_openings_count) OVER (ORDER BY AAA.crawl_date DESC) AS prev_closed_openings_count
                        , AAA.new_openings_count
                        , LEAD(AAA.new_openings_count) OVER (ORDER BY AAA.crawl_date DESC) AS prev_new_openings_count
                        , AAA.fill_rate
                        , LEAD(AAA.fill_rate) OVER (ORDER BY AAA.crawl_date DESC) AS prev_fill_rate
                        , BBB.average_weeks_to_fill 
                        , LEAD(BBB.average_weeks_to_fill) OVER (ORDER BY AAA.crawl_date DESC) AS prev_average_weeks_to_fill 
                        , AAA.crawl_date
                    FROM reporting_data.rpt_job_openings_metrics AAA
                    LEFT JOIN (
                        SELECT BBB.*
                        FROM reporting_data.rpt_job_fill_time_statistics BBB
                        WHERE BBB.current_date BETWEEN TO_CHAR(CAST('{crawl_date}' AS date) - INTERVAL '7 days', 'YYYY-MM-DD') AND '{crawl_date}'   
                    ) BBB ON AAA.crawl_date = BBB.current_date
                    WHERE AAA.crawl_date BETWEEN TO_CHAR(CAST('{crawl_date}' AS date) - INTERVAL '7 days', 'YYYY-MM-DD') AND '{crawl_date}'
                    ORDER BY AAA.crawl_date DESC
                )AAAA
                WHERE AAAA.crawl_date = '{crawl_date}';
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method
            
            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['total_openings', 'total_openings_change_pct', 'closed_openings_count', 'closed_openings_change_pct', 'new_openings_count', 'new_openings_change_pct', 'fill_rate', 'fill_rate_change_pct', 'average_weeks_to_fill', 'average_weeks_to_fill_change_pct', 'crawl_date'])
                self.logger.info("Openings statistics metrics data converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No data found for the given crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching openings statistics metrics for crawl date {crawl_date}: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_openings_history(self):
        """
        Fetch data for history total openings within the 'reporting_data' schema.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = """
                SELECT 
                    AAA.total_openings
                    , AAA.crawl_date
                FROM(
                    SELECT AA.total_openings, AA.crawl_date 
                    FROM reporting_data.rpt_job_openings_metrics AA 
                    ORDER BY AA.crawl_date DESC
                    LIMIT 12
                )AAA
                ORDER BY AAA.crawl_date ASC;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['total_openings', 'crawl_date'])
                self.logger.info("Historical total openings data converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No historical total openingsdata found for openings statistics.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error("Error fetching historical openings statistics metrics: {error}".format(error=str(e)))
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_data_role(self, crawl_date):
        """
        Fetch data for data role pie plot within the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    AA.data_role,
                    AA.count,
                    (AA.count::float / total.total_count) * 100 AS percentage_of_total,
                    AA.crawl_date
                FROM 
                    reporting_data.rpt_data_role_vacancy_trends AA,
                    (SELECT SUM(count) AS total_count
                    FROM reporting_data.rpt_data_role_vacancy_trends
                    WHERE crawl_date = '{crawl_date}') AS total
                WHERE 
                    AA.crawl_date = '{crawl_date}';
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['data_role', 'count', 'percentage_of_total', 'crawl_date'])
                self.logger.info("Data role information for the pie plot converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No data role information found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching data role information: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_data_tool(self, crawl_date):
        """
        Fetch data for top three data tools within the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    AAA."rank",
                    AAA.category,
                    AAA.tool_name,
                    COALESCE(AAA.tool_count::float / NULLIF(BBB.total_openings, 0) * 100, 0) AS percentage_of_tool,
                    AAA.crawl_date
                FROM reporting_data.rpt_data_tools_trends AAA
                LEFT JOIN (
                    SELECT BB.total_openings, BB.crawl_date
                    FROM reporting_data.rpt_job_openings_metrics BB
                    WHERE BB.crawl_date = '{crawl_date}'
                ) BBB ON CAST(AAA.crawl_date AS date) = CAST(BBB.crawl_date AS date)
                WHERE AAA.crawl_date = '{crawl_date}'
                ORDER BY AAA."rank"
                LIMIT 3;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['rank', 'category', 'tool_name', 'percentage_of_tool', 'crawl_date'])
                self.logger.info("Top three data tools information converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No data tools information found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching data tools information: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_openings_company(self, crawl_date):
        """
        Fetch job vacancy data for the top five companies from the 'reporting_data' schema for a specific crawl date,
        adjusting company names with special characters.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT rank, company_name, opening_count, crawl_date
                FROM reporting_data.rpt_weekly_company_job_vacancies
                WHERE crawl_date = '{crawl_date}'
                ORDER BY opening_count DESC
                LIMIT 5;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['rank', 'company_name', 'opening_count', 'crawl_date'])
                
                # Adjust company names based on your specified conditions
                def adjust_company_name(name):
                    if '_' in name:
                        return name.split('_')[0]
                    elif '(' in name and ')' in name:
                        return re.search(r'\((.*?)\)', name).group(1)
                    else:
                        return name
                
                df['company_name'] = df['company_name'].apply(adjust_company_name)
                self.logger.info("Job vacancy data for the top five companies converted to DataFrame successfully with adjusted company names.")
                return df
            else:
                self.logger.info("No job vacancy data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching job vacancy data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_taiepi_area_openings(self, crawl_date):
        """
        Fetch job vacancy data for specified areas from the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    county_name_eng, 
                    district_name_eng, 
                    openings_count, 
                    crawl_date 
                FROM reporting_data.rpt_job_openings_geograph  
                WHERE crawl_date = '{crawl_date}' AND county_name_eng IN ('Taipei City', 'New Taipei City');
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['county_name_eng', 'district_name_eng', 'openings_count', 'crawl_date'])
                self.logger.info("Job vacancy data for specified areas converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No job vacancy data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching job vacancy data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        
    def fetch_tool_by_data_role(self):
        """
        Fetch tool usage data segmented by data role from the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    data_role,
                    category,
                    tool_name,
                    count,
                    crawl_date 
                FROM reporting_data.rpt_data_tools_by_data_role;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['data_role', 'category', 'tool_name', 'count', 'crawl_date'])
                self.logger.info("Tool data by data role converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No tool data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching tool data by data role: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        
    def fetch_tool_trends(self):
        """
        Fetch tool trends data from the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    "rank",
                    category,
                    tool_name,
                    tool_count,
                    crawl_date
                FROM reporting_data.rpt_data_tools_trends;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['rank', 'category', 'tool_name', 'tool_count', 'crawl_date'])
                self.logger.info("Tool data by data role converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No tool data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching tool trend data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

    def fetch_education_by_data_role(self, crawl_date):
        """
        Fetch education by data role data from the 'reporting_data' schema.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    data_role,
                    degree,
                    count
                FROM reporting_data.rpt_data_role_by_edu
                WHERE crawl_date = '{crawl_date}';
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['data_role', 'degree', 'count'])
                self.logger.info("Education by data role data converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No education data found for data roles.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching education by data role data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        
    def fetch_taiwan_openings(self, crawl_date):
        """
        Fetch job vacancy data for specified areas from the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    AAAA.county_name_ch
                    , AAAA.county_name_eng
                    , AAAA.district_name_ch
                    , AAAA.district_name_eng
                    , CASE 
                        WHEN CCCC.openings_count IS NULL THEN 0
                        ELSE CCCC.openings_count
                    END AS openings_count
                FROM(
                    SELECT 
                        BBB.county_name_ch
                        , BBB.county_name_eng
                        , AAA.district_name_ch
                        , AAA.district_name_eng	
                    FROM modeling_data.er_district AAA
                    LEFT JOIN(SELECT BB.county_id, BB.county_name_ch,  BB.county_name_eng FROM modeling_data.er_county BB)BBB
                    ON AAA.county = BBB.county_id
                )AAAA
                LEFT JOIN (SELECT CC.* FROM reporting_data.rpt_job_openings_geograph CC WHERE CC.crawl_date = '{crawl_date}')CCCC
                ON AAAA.county_name_eng = CCCC.county_name_eng AND AAAA.district_name_eng = CCCC.district_name_eng;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['county_name_ch', 'county_name_eng', 'district_name_ch', 'district_name_eng', 'openings_count'])
                self.logger.info("Job vacancy data for Taiwan converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No job vacancy data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching job vacancy data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        
    def fetch_major_city_openings(self, crawl_date):
        """
        Fetch job vacancy data for six major city openings data from the 'reporting_data' schema for a specific crawl date.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT 
                    CASE county_name_eng
                        WHEN 'Taipei City' THEN 1
                        WHEN 'New Taipei City' THEN 2
                        WHEN 'Taoyuan City' THEN 3
                        WHEN 'Taichung City' THEN 4
                        WHEN 'Tainan City' THEN 5
                        WHEN 'Kaohsiung City' THEN 6
                        ELSE NULL
                    END AS "#",
                    county_name_eng as County,  
                    SUM(openings_count) as Openings
                FROM reporting_data.rpt_job_openings_geograph rjog
                WHERE crawl_date = '{crawl_date}'
                    AND county_name_eng IN ('Taipei City', 'New Taipei City', 'Taoyuan City', 'Taichung City', 'Tainan City', 'Kaohsiung City')
                GROUP BY county_name_eng
                ORDER BY "#";
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['#', 'County', 'Openings'])
                self.logger.info("Job vacancy data for Taiwan six major city converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No job vacancy data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching job vacancy data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error
        
    def fetch_taipei_historical_openings(self):
        """
        Fetch job vacancy data for taipei openings trend from the 'reporting_data' schema.
        """
        try:
            # Prepare the SQL query to fetch the required data
            query = f"""
                SELECT county_name_eng, sum(openings_count) AS openings, crawl_date 
                FROM reporting_data.rpt_job_openings_geograph 
                WHERE county_name_eng = 'Taipei City'
                GROUP BY county_name_eng, crawl_date;
            """
            # Execute the query and fetch the result
            data = self.execute_query(query)  # Use self.execute_query to call the local method

            # Convert the data into a DataFrame if not empty
            if data:
                df = pd.DataFrame(data, columns=['county_name_eng', 'openings', 'crawl_date'])
                self.logger.info("Job vacancy data for Taipei openings trend converted to DataFrame successfully.")
                return df
            else:
                self.logger.info("No job vacancy data found for the specified crawl date.")
                return pd.DataFrame()  # Return an empty DataFrame if no data
        except Exception as e:
            self.logger.error(f"Error fetching job vacancy data: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame in case of an error

class CreateReportChart:
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

    # Create the taiepi area openings map
    def create_openings_map(taiepi_area_openings):
        # Load your GeoJSON file
        with open('src/dashboard_src/assets/geo_data/county_geo_info.geojson', 'r') as file:
            geojson_data = json.load(file)

        # Filter features for 'COUNTYNAME' of '臺北市' or '新北市'
        filtered_features = [feature for feature in geojson_data['features']
                            if feature['properties']['COUNTYNAME'] in ['臺北市', '新北市']]

        # Update GeoJSON data with filtered features
        filtered_geojson_data = dict(geojson_data)  # Make a copy of the original data
        filtered_geojson_data['features'] = filtered_features

        # Extract all districts from the GeoJSON data
        all_districts = [feature['properties']['TOWNENG'] for feature in filtered_features]

        # Ensure taiepi_area_openings contains all districts
        all_districts_df = pd.DataFrame({'district_name_eng': all_districts})
        taiepi_area_openings = all_districts_df.merge(taiepi_area_openings, on='district_name_eng', how='left')
        taiepi_area_openings['openings_count'] = taiepi_area_openings['openings_count'].fillna(0)
        taiepi_area_openings['openings_count'] = taiepi_area_openings['openings_count'].astype(float)

        # Define a custom color scale
        custom_color_scale = [
            [0, '#E6ECFF'],    # low
            [0.5, '#5A6ACF'],  # mid
            [1, '#2E2E48']     # high
        ]

        # Generate the map
        openings_map = px.choropleth_mapbox(
            taiepi_area_openings,
            geojson=filtered_geojson_data,
            locations='district_name_eng',  # Use 'district_name_eng' as location identifier
            featureidkey="properties.TOWNENG",  # Match with 'TOWNENG' in GeoJSON
            color='openings_count',  # Color by 'openings_count'
            color_continuous_scale=custom_color_scale,  # Use custom color scale
            range_color=(0, taiepi_area_openings['openings_count'].max()),  # Set color range
            mapbox_style="white-bg",  # Use a plain white background
            center={"lat": 25.008216635689223, "lon": 121.641468398647703},  # Centered around Taipei
            zoom=8.1,  # Adjust the zoom level to fit the desired area
        )

        # Update layout to ensure no other geographic information is shown
        openings_map.update_traces(
                marker_line_color='black', 
                marker_line_width=1,  # Only show outlines
                hovertemplate='<b><span style="font-size:15px;">%{location}</span></b><br><b><span style="font-size:12px;">Openings count: %{z}</span></b><extra></extra>'
            )
    
        openings_map.update_layout(
            coloraxis_showscale=False,  # Hide the color bar
            showlegend=True,  # Show legend
            margin={"r":0,"t":0,"l":0,"b":0},
            width=410,  # Adjust the width of the map to center it
            height=300,  # Adjust the height of the map to center it
            mapbox=dict(
                center={"lat": 25.008216635689223, "lon": 121.641468398647703},
                zoom=8.1  # Adjust zoom level as needed
            ),
            autosize=True,  # Automatically adjust the size of the map
            hovermode='closest',  # Hover mode closest to the cursor
            hoverlabel=dict(
                bgcolor="#2E2E48", # setup hover label background color
                font_size=12,      # setup hover label font size
                font_color="white",# setup hover label font color
                bordercolor="#2E2E48" # setup hover label border color
            )
        )

        return openings_map

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

    def extract_tools_ranker(data_tools):
        rank_1_tool_name = data_tools['tool_name'].values[0]
        rank_1_tool_percentage = data_tools['percentage_of_tool'].values[0]
        rank_2_tool_name = data_tools['tool_name'].values[1]
        rank_2_tool_percentage = data_tools['percentage_of_tool'].values[1]
        rank_3_tool_name = data_tools['tool_name'].values[2]
        rank_3_tool_percentage = data_tools['percentage_of_tool'].values[2]

        return {
            'rank_1_tool_name': rank_1_tool_name,
            'rank_1_tool_percentage': rank_1_tool_percentage,
            'rank_2_tool_name': rank_2_tool_name,
            'rank_2_tool_percentage': rank_2_tool_percentage,
            'rank_3_tool_name': rank_3_tool_name,
            'rank_3_tool_percentage': rank_3_tool_percentage
        }

    def extract_company_ranker(openings_company):
        rank_1_company_name = openings_company['company_name'].values[0]
        rank_1_openings = openings_company['opening_count'].values[0]
        rank_2_company_name = openings_company['company_name'].values[1]
        rank_2_openings = openings_company['opening_count'].values[1]
        rank_3_company_name = openings_company['company_name'].values[2]
        rank_3_openings = openings_company['opening_count'].values[2]
        rank_4_company_name = openings_company['company_name'].values[3]
        rank_4_openings = openings_company['opening_count'].values[3]
        rank_5_company_name = openings_company['company_name'].values[4]
        rank_5_openings = openings_company['opening_count'].values[4]

        return {
            'rank_1_company_name': rank_1_company_name,
            'rank_1_openings': rank_1_openings,
            'rank_2_company_name': rank_2_company_name,
            'rank_2_openings': rank_2_openings,
            'rank_3_company_name': rank_3_company_name,
            'rank_3_openings': rank_3_openings,
            'rank_4_company_name': rank_4_company_name,
            'rank_4_openings': rank_4_openings,
            'rank_5_company_name': rank_5_company_name,
            'rank_5_openings': rank_5_openings
        }
    
    def create_tool_trends_line_chart(tool_by_data_role, selected_datarole='All', selected_category='All'):
        filtered_data = tool_by_data_role.copy()

        # Handle the case where both selections are 'All'
        if selected_datarole == 'All' and selected_category == 'All':
            grouped_data = filtered_data.groupby(['tool_name', 'crawl_date'])['count'].sum().reset_index()
            top_tools = grouped_data.groupby('tool_name')['count'].sum().nlargest(10).index
            filtered_data = grouped_data[grouped_data['tool_name'].isin(top_tools)]
        
        # Handle the case where data_role is 'All' but category has a selected value
        elif selected_datarole == 'All':
            filtered_data = filtered_data[filtered_data['category'] == selected_category]
            grouped_data = filtered_data.groupby(['tool_name', 'crawl_date'])['count'].sum().reset_index()
            top_tools = grouped_data.groupby('tool_name')['count'].sum().nlargest(10).index
            filtered_data = grouped_data[grouped_data['tool_name'].isin(top_tools)]
        
        # Handle the case where category is 'All' but data_role has a selected value
        elif selected_category == 'All':
            filtered_data = filtered_data[filtered_data['data_role'] == selected_datarole]
            grouped_data = filtered_data.groupby(['tool_name', 'crawl_date'])['count'].sum().reset_index()
            top_tools = grouped_data.groupby('tool_name')['count'].sum().nlargest(10).index
            filtered_data = grouped_data[grouped_data['tool_name'].isin(top_tools)]
        
        # Handle the case where both selections are not 'All'
        else:
            filtered_data = filtered_data[(filtered_data['data_role'] == selected_datarole) & (filtered_data['category'] == selected_category)]
            grouped_data = filtered_data.groupby(['tool_name', 'crawl_date'])['count'].sum().reset_index()
            top_tools = grouped_data.groupby('tool_name')['count'].sum().nlargest(10).index
            filtered_data = grouped_data[grouped_data['tool_name'].isin(top_tools)]

        # Define color sequence based on your specified colors
        color_sequence = ['#2E2E48', '#42425F', '#565778', '#6C6E91', '#8285AC', '#989CC7', '#AFB5E3', '#C7CEFF', '#C7CEFF', '#C7CEFF']

        # Sort tools by total count and assign colors
        tool_order = filtered_data.groupby('tool_name')['count'].sum().sort_values(ascending=False).index
        tool_colors = {tool: color for tool, color in zip(tool_order, color_sequence)}

        # Sort filtered_data by tool_name to ensure legend order
        filtered_data['tool_name'] = pd.Categorical(filtered_data['tool_name'], categories=tool_order, ordered=True)
        filtered_data = filtered_data.sort_values(['tool_name', 'crawl_date'])

        # Create line chart
        tool_trends_line_chart = px.line(
            filtered_data, 
            x='crawl_date', 
            y='count', 
            color='tool_name',
            color_discrete_map=tool_colors,  # Apply the color mapping
            template='plotly_white',
        )

        # Define the y-axis range and tick values to ensure 5 grid lines
        y_max = filtered_data['count'].max()
        y_ticks = [0, y_max / 4, y_max / 2, 3 * y_max / 4, y_max]

        # Update chart layout and style
        tool_trends_line_chart.update_layout(
            width=1200,
            height=400,
            margin=dict(l=70, r=20, t=0, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,  # Remove x-axis title
            yaxis_title=None,  # Remove y-axis title
            legend_title=None,  # Remove legend title
            legend=dict(
                orientation="h",
                x=-0.02,
                y=-0.15,
                xanchor="left",
                yanchor="top"
            ),
            xaxis=dict(
                showgrid=False,  # Hide x-axis grid lines
                showline=True,  # Show x-axis line
                linewidth=1,
                linecolor='lightgrey',
                zeroline=False,  # Remove x-axis 0 line
                tickfont=dict(
                    color='#737b8b'
                )
            ),
            yaxis=dict(
                showgrid=True,  # Show y-axis grid lines
                showline=False,  # Hide y-axis line
                linewidth=1,
                linecolor='lightgrey',
                tickfont=dict(
                    color='#737b8b'
                ),
                zeroline=False,
                showticklabels=True,  # Show y-axis tick labels
                tickvals=y_ticks,  # Set the y-axis tick values to ensure 5 grid lines
                ticktext=['0', f'{y_max / 4:.0f}', f'{y_max / 2:.0f}', f'{3 * y_max / 4:.0f}', f'{y_max:.0f}']  # Set the tick text
            ),
            hoverlabel=dict(
                bgcolor="#2E2E48",
                font_size=12,
                font_color="white",
                bordercolor="#2E2E48"
            )
        )

        tool_trends_line_chart.update_traces(
            mode='lines+markers',
            line={'width': 2.5},
            showlegend=True,
            hovertemplate=(
                '<span style="font-size:15px; font-weight:bold;">%{fullData.name}</span>'
                '<span style="font-size:15px; font-weight:bold;">: %{y}</span><br><br>'
                '<span style="font-size:12px; font-weight:bold;">%{x|%Y-%m-%d}</span><extra></extra>'
            ),
        )

        tool_trends_line_chart.update_xaxes(
            dtick="M1",
            tickformat="%b %d",
        )

        return tool_trends_line_chart
    
    def create_tool_popularity_bar_chart(tool_by_data_role, selected_datarole='All', selected_category='All'):
        filtered_data = tool_by_data_role.copy()

        # Handle the data

        grouped_data = filtered_data.groupby('tool_name')['count'].sum().reset_index()
        top_tools = grouped_data.nlargest(5, 'count')

        # Create bar chart
        tool_popularity_bar_chart = go.Figure()

        tool_popularity_bar_chart.add_trace(go.Bar(
            x=top_tools['count'],
            y=top_tools['tool_name'],
            orientation='h',
            marker=dict(color='#2E2E48'),
            text=top_tools['count'],  
            texttemplate='%{text}  ',
            textposition='inside',  
            textfont=dict(color='white', size=14),
            insidetextanchor='end',
        ))

        tool_popularity_bar_chart.update_traces(width=0.7)  # adjust bar size 

        tool_popularity_bar_chart.update_layout(
            width=1100,  # Adjust the width to shorten the bar chart
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title=None,
            yaxis=dict(
                categoryorder='total ascending',
            ),
            hoverlabel=dict(
                bgcolor="#2E2E48",
                font_size=12,
                font_color="white",
                bordercolor="#2E2E48"
            ),
            xaxis=dict(
                showticklabels=False  # Hide the count axis at the bottom
            )
        )

        # Add annotations for most and least popular in roles
        annotations = []
        max_count = top_tools['count'].max()
        for i, row in top_tools.iterrows():
            tool_name = row['tool_name']
            tool_data = filtered_data[filtered_data['tool_name'] == tool_name]
            roles_count = tool_data.groupby('data_role')['count'].sum()

            most_popular_roles = roles_count[roles_count == roles_count.max()].index.tolist()
            least_popular_roles = roles_count[roles_count == roles_count.min()].index.tolist()

            # Calculate the position based on the length of the bar
            annotation_x = max_count + 100  # Adjust this offset as needed

            annotations.append(
            dict(
                x=annotation_x + 1700,  
                y=tool_name,
                text=f"<b>{', '.join(most_popular_roles)}</b>",  
                showarrow=False,
                font=dict(color='#737B8B', size=14),
                align='left'
                )
            )
            annotations.append(
                dict(
                    x=annotation_x + 5000,  
                    y=tool_name,
                    text=f"<b>{', '.join(least_popular_roles)}</b>",  
                    showarrow=False,
                    font=dict(color='#737B8B', size=14),
                    align='left'
                )
            )

        tool_popularity_bar_chart.update_layout(annotations=annotations)

        return tool_popularity_bar_chart

    def create_education_heatmap(edu_by_data_role):
        # Define the desired order for data roles and degrees
        data_role_order = [
            'MLE', 'Data Scientist', 'Data Engineer', 'Data Architect', 'Data Analyst', 'BI Engineer', 'Business Analyst'
        ]
        degree_order = [
            'PhD', 'Master', 'Bachelor', 'College', 'High School', 'Others'
        ]

        # Convert 'data_role' and 'degree' columns to categorical with the specified order
        edu_by_data_role['data_role'] = pd.Categorical(
            edu_by_data_role['data_role'], categories=data_role_order, ordered=True
        )
        edu_by_data_role['degree'] = pd.Categorical(
            edu_by_data_role['degree'], categories=degree_order, ordered=True
        )

        # Pivot the data for heatmap
        heatmap_data = edu_by_data_role.pivot(index='data_role', columns='degree', values='count')

        # Reindex the columns and rows to ensure the order
        heatmap_data = heatmap_data.reindex(index=data_role_order, columns=degree_order)

        # Fill NaN values with 'No Data'
        z_text = heatmap_data.fillna('No Data').values

        # Define colorscale
        colorscale = [
            [0, 'rgb(239,239,255)'],   # light color
            [0.5, 'rgb(102,102,153)'], # medium color
            [1, 'rgb(51,51,102)']      # dark color
        ]

        # Create heatmap
        edu_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale=colorscale,
            showscale=False,
            text=z_text,
            hovertemplate=
            '<b>Data role :</b> <b>%{y}</b> <br><br>' +
            '<b>Degree :</b> <b>%{x}</b> <br><br>' +
            '<b>Count :</b> <b>%{text}</b> <extra></extra>',
            hoverlabel=dict(
                bgcolor='rgb(51,51,102)',
                font_size=14,
                font_family='Arial, sans-serif',
                font_color='white'
            )
        ))

        # Update layout
        edu_heatmap.update_layout(
            width=1100,
            height=600,
            margin=dict(l=50, r=50, t=50, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                title=None,
                tickmode='array',
                tickvals=heatmap_data.columns,
                ticktext=heatmap_data.columns,
                tickfont=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color='#737b8b',
                )
            ),
            yaxis=dict(
                title=None,
                tickmode='array',
                tickvals=heatmap_data.index,
                ticktext=heatmap_data.index,
                tickfont=dict(
                    family='Arial, sans-serif',
                    size=14,
                    color='#737b8b',
                )
            )
        )

        return edu_heatmap
    
    def create_taiwan_openings_map(taiwan_openings):
        # Load your GeoJSON file
        with open('src/dashboard_src/assets/geo_data/county_geo_info.geojson', 'r') as file:
            geojson_data = json.load(file)

        for feature in geojson_data['features']:
            county = feature['properties']['COUNTYNAME']
            town = feature['properties']['TOWNNAME']
            feature['properties']['county_town'] = f"{county}{town}"

        # Ensure taiwan_openings contains all districts and counties
        taiwan_openings['county_name_ch'] = taiwan_openings['county_name_ch'].str.replace('台', '臺')  # Standardize county names
        taiwan_openings['district_name_ch'] = taiwan_openings['district_name_ch'].str.replace('台', '臺')  # Standardize county names

        # Fill district_name_eng with county_name_eng if district_name_eng is null
        taiwan_openings['district_name_eng'].fillna(taiwan_openings['county_name_ch'], inplace=True)

        # Drop rows where both district_name_eng and county_name_ch are null
        taiwan_openings.dropna(subset=['district_name_eng', 'county_name_ch'], how='all', inplace=True)

        taiwan_openings['openings_count'] = taiwan_openings['openings_count'].fillna(0)
        taiwan_openings['openings_count'] = taiwan_openings['openings_count'].astype(float)

        # Define a custom color scale
        custom_color_scale = [
            [0, '#E6ECFF'],    # low
            [0.5, '#5A6ACF'],  # mid
            [1, '#2E2E48']     # high
        ]

        # Generate the map
        taiwan_openings_map = px.choropleth_mapbox(
            taiwan_openings,
            geojson=geojson_data,
            locations='district_name_ch',  # Use 'district_name_eng' as location identifier
            featureidkey="properties.county_town",  # Match with 'county_town' in GeoJSON
            color='openings_count',  # Color by 'openings_count'
            color_continuous_scale=custom_color_scale,  # Use custom color scale
            range_color=(0, taiwan_openings['openings_count'].max()),  # Set color range
            mapbox_style="white-bg",  # Use a plain white background
            center={"lat": 23.6978, "lon": 120.9605},  # Centered around Taipei
            zoom=8.1,  # Adjust the zoom level to fit the desired area
        )

        # Update layout to ensure no other geographic information is shown
        taiwan_openings_map.update_traces(
            hovertemplate=(
                '<b><span style="font-size:15px;">%{customdata[0]}</span></b><br>' +  # County name
                '<b><span style="font-size:12px;">%{customdata[1]}</span></b><br>' +  # District name
                '<b><span style="font-size:12px;">Openings count: %{z}</span></b><extra></extra>'
            ),
            customdata=taiwan_openings[['county_name_eng', 'district_name_eng']].to_numpy()
        )

        taiwan_openings_map.update_layout(
            coloraxis_showscale=False,  # Hide the color bar
            showlegend=True,  # Show legend
            margin={"r":0,"t":0,"l":0,"b":0},
            width=430,  # Adjust the width of the map to center it
            height=780,  # Adjust the height of the map to center it
            mapbox=dict(
                center={"lat": 23.6978, "lon": 120.9605},
                zoom=7  # Adjust zoom level as needed
            ),
            autosize=True,  # Automatically adjust the size of the map
            hovermode='closest',  # Hover mode closest to the cursor
            hoverlabel=dict(
                bgcolor="#2E2E48", # setup hover label background color
                font_size=12,      # setup hover label font size
                font_color="white",# setup hover label font color
                bordercolor="#2E2E48" # setup hover label border color
            )
        )

        return taiwan_openings_map
    
    def create_county_openings_table(six_major_city_openings):
        # Create a figure with a table
        major_city_table = go.Figure(data=[go.Table(
            header=dict(
                values=['#', 'County', 'Openings'],
                fill_color='gray',
                align='center',
                font=dict(color='white', size=12)
            ),
            cells=dict(
                values=[six_major_city_openings['#'], six_major_city_openings['County'], six_major_city_openings['Openings']],
                fill_color='white',
                align='center',
                font=dict(color='black', size=11)
            )
        )])

        # Update layout
        major_city_table.update_layout(
            width=500,
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )

        return major_city_table        

    def create_taipei_openings_trend_chart(taipei_openings_trend):
        # Sort the data by crawl_date
        taipei_openings_trend = taipei_openings_trend.sort_values(by='crawl_date')

        # Creating the line chart using Plotly Express
        taipei_openings_trend_chart = px.line(
            taipei_openings_trend, 
            x='crawl_date', 
            y='openings', 
            labels={'crawl_date': 'Date', 'openings': 'Openings'},
            color_discrete_sequence=['#ffa726'],
        )

        # Adding the bar chart
        taipei_openings_trend_chart.add_bar(
            x=taipei_openings_trend['crawl_date'], 
            y=taipei_openings_trend['openings'], 
            name="Openings in Taipei",
            marker_color='rgba(46, 46, 72, 0.8)'  # Set the color of the bars
        )

        # Update layout
        taipei_openings_trend_chart.update_layout(
            width=650,
            height=500,
            margin=dict(l=95, r=20, t=143, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                x=-0.05,
                y=-0.2,
                xanchor="left",
                yanchor="top"
            ),
            hoverlabel=dict(
                font_size=12,
                font_color="white"
            ),
            xaxis=dict(
                title='',
                tickvals=taipei_openings_trend['crawl_date'][::1],
                tickformat="%b %d",
                tickmode='array',
                showgrid=False,
                showline=True,
                linewidth=1,
                linecolor='lightgrey',
                tickfont=dict(
                    color='#737b8b'
                )
            ),
            yaxis=dict(
                title='',
                showgrid=True,
                showticklabels=False
            ),
            yaxis2=dict(
                title='',
                overlaying='y',
                side='left',
                showgrid=False,
                showticklabels=True,
                tickfont=dict(
                    color='#737b8b'
                )
            )
        )

        # Update hover styles for bar chart and disable hover for line chart
        taipei_openings_trend_chart.update_traces(
            selector=dict(type='scatter'),
            hoverinfo='skip'
        )
        taipei_openings_trend_chart.update_traces(
            selector=dict(type='bar'),
            hoverlabel=dict(bgcolor="#2E2E48", bordercolor="#2E2E48")
        )

        return taipei_openings_trend_chart
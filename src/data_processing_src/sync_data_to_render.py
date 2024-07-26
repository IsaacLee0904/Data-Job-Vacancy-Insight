'''
This script will sync the data from the data processing to the render database
Those table below need to be sync :
    1. reporting_data.rpt_job_openings_metrics
    2. reporting_data.rpt_job_fill_time_statistics 
    3. reporting_data.rpt_data_role_vacancy_trends
    4. reporting_data.rpt_data_tools_trends
    5. reporting_data.rpt_weekly_company_job_vacancies
    6. reporting_data.rpt_job_openings_geograph [x]
    7. reporting_data.rpt_data_tools_by_data_role [x]
    8. reporting_data.rpt_data_role_by_edu
    9. modeling_data.er_district
    10.modeling_data.er_county
    11. 
'''

import os, sys
import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from utils.log_utils import set_logger
from utils.database_utils import DatabaseConnector, DatabaseOperation, RenderTablesCreator

TABLES_TO_SYNC = [
    ("reporting_data", "rpt_job_openings_metrics"),
    ("reporting_data", "rpt_job_fill_time_statistics"),
    ("reporting_data", "rpt_data_role_vacancy_trends"),
    ("reporting_data", "rpt_data_tools_trends"),
    ("reporting_data", "rpt_weekly_company_job_vacancies"),
    ("reporting_data", "rpt_job_openings_geograph"),
    ("reporting_data", "rpt_data_tools_by_data_role"),
    ("reporting_data", "rpt_data_role_by_edu"),
    ("modeling_data", "er_district"),
    ("modeling_data", "er_county")
]

def connect_to_database(logger, db_name):
    """
    Establish a connection to a specified database and return the connector and operation objects.
    """
    connector = DatabaseConnector(logger)
    connection = connector.connect_to_db(db_name)
    db_operation = DatabaseOperation(connection, logger)
    logger.info(f"Connected to {db_name} database successfully.")
    return connection, db_operation

def create_schemas(db_operation):
    """
    Create required schemas in the database if they do not exist.
    """
    db_operation.create_schema('reporting_data')
    db_operation.create_schema('modeling_data')

def fetch_data_from_table(db_operation, schema_table):
    """
    Fetch data from a specified table.
    """
    schema, table = schema_table
    return db_operation.fetch_data(f"{schema}.{table}")

def setup_remote_tables(remote_db_operation):
    """
    Setup remote tables based on the defined render table creation functions.
    """
    table_creation_map = {
        "rpt_job_openings_metrics": RenderTablesCreator.create_render_rpt_job_openings_metrics_table,
        "rpt_job_fill_time_statistics": RenderTablesCreator.create_render_rpt_job_fill_time_statistics_table,
        "rpt_data_role_vacancy_trends": RenderTablesCreator.create_render_rpt_data_role_vacancy_trends_table,
        "rpt_data_tools_trends": RenderTablesCreator.create_render_rpt_data_tools_trends_table,
        "rpt_weekly_company_job_vacancies": RenderTablesCreator.create_render_rpt_weekly_company_job_vacancies_table,
        "rpt_job_openings_geograph": RenderTablesCreator.create_rpt_job_openings_geograph_table,
        "rpt_data_tools_by_data_role": RenderTablesCreator.create_rpt_data_tools_by_data_role_table,
        "rpt_data_role_by_edu": RenderTablesCreator.create_rpt_data_role_by_edu_table,
        "er_district": RenderTablesCreator.create_er_district_table,
        "er_county": RenderTablesCreator.create_er_county_table
    }

    for table_name, creation_function in table_creation_map.items():
        creation_function(remote_db_operation)

def sync_data(local_db_operation, remote_db_operation):
    """
    Sync data from local to remote database for defined tables.
    """
    for schema, table in TABLES_TO_SYNC:
        data_df = fetch_data_from_table(local_db_operation, (schema, table))
        remote_db_operation.insert_overwrite_data(f"{schema}.{table}", data_df)

def main():
    logger = set_logger()

    local_conn, local_db_op = connect_to_database(logger, 'datawarehouse')
    remote_conn, remote_db_op = connect_to_database(logger, 'render_deploy')

    create_schemas(local_db_op)
    create_schemas(remote_db_op)
    
    setup_remote_tables(remote_db_op)

    sync_data(local_db_op, remote_db_op)

    # Close the database connections
    local_conn.close()
    remote_conn.close()

if __name__ == "__main__":
    main()
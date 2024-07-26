import toml
import pandas as pd
import psycopg2
import psycopg2.extras

class DatabaseConnector:
    def __init__(self, logger):
        """
        Initialize the DatabaseConnector class with the path to the configuration file and a logger.

        Parameters:
        - config_path (str): The file path to the TOML configuration file.
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        self.config = toml.load('config/database_config.toml')
        self.logger = logger

    def connect_to_db(self, db_name):
        """
        Establish a connection to the database specified in the configuration file.

        Parameters:
        - db_name (str): The database name to connect to, as defined in the TOML file.

        Returns:
        - A connection object if successful, None otherwise.
        """
        db_config = self.config[db_name]
        try:
            connection = psycopg2.connect(
                dbname=db_config['db'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                port=db_config['port']
            )
            self.logger.info(f"Successfully connected to {db_name}")
            return connection
        except Exception as e:
            self.logger.error(f"Error connecting to {db_name}: {e}")
            return None

class DatabaseOperation:
    def __init__(self, connection, logger):
        """
        Initialize the DatabaseOperation with a database connection and a logger.

        Parameters:
        - connection: The connection object to the database.
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.logger = logger

    def create_table(self, create_table_query):
        """
        Create a table in the database based on the provided SQL query.

        Parameters:
        - create_table_query (str): The SQL query to create a table.
        """
        try:
            self.cursor.execute(create_table_query)
            self.connection.commit()
            self.logger.info("Table created successfully.")
        except psycopg2.Error as e:
            self.logger.error(f"An error occurred while creating the table: {e}")
            self.connection.rollback()

    def create_schema(self, schema_name):
        """
        Create a schema in the database if it doesn't already exist.

        Parameters:
        - schema_name (str): The name of the schema to be created.
        """
        create_schema_query = f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
        try:
            self.cursor.execute(create_schema_query)
            self.connection.commit()
            self.logger.info(f"Schema '{schema_name}' created successfully.")
        except psycopg2.Error as e:
            self.logger.error(f"An error occurred while creating the schema '{schema_name}': {e}")
            self.connection.rollback()

    def insert_data(self, table_name, df, unique_cols):
        """
        Insert data from a pandas DataFrame into the specified table and handle duplicates.

        Parameters:
        - table_name (str): The name of the table to insert data into.
        - df (pd.DataFrame): The DataFrame containing the data to be inserted.
        - unique_cols (list or str): A column name or a list of column names that together define uniqueness.
        """
        cols = ','.join(list(df.columns))
        values = ','.join(['%s'] * len(df.columns))
        
        if isinstance(unique_cols, list):
            conflict_cols = ','.join(unique_cols)
        else:
            conflict_cols = unique_cols
        
        update_expr = ','.join([f"{col}=EXCLUDED.{col}" for col in df.columns if col not in unique_cols])
        insert_stmt = f"INSERT INTO {table_name} ({cols}) VALUES ({values}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_expr}"

        records = [tuple(x) for x in df.to_numpy()]

        try:
            psycopg2.extras.execute_batch(self.cursor, insert_stmt, records)
            self.connection.commit()
            self.logger.info(f"Successfully upserted data into {table_name}.")
        except Exception as e:
            self.logger.error(f"Error upserting data into {table_name}: {e}")
            self.connection.rollback()

    def insert_overwrite_data(self, table_name, df):
        """
        Clear the table before inserting data from a pandas DataFrame into the specified table.
        This operation will overwrite all existing records in the table.

        Parameters:
        - table_name (str): The name of the table where data will be inserted.
        - df (pd.DataFrame): The DataFrame containing the data to be inserted.
        """
        # Properly quote column names to handle any special characters or reserved words
        cols = ','.join([f'"{col}"' for col in df.columns])
        values = ','.join(['%s'] * len(df.columns))  # Placeholder for values to be inserted
        delete_stmt = f"DELETE FROM {table_name};"  # SQL statement to clear the table
        insert_stmt = f"INSERT INTO {table_name} ({cols}) VALUES ({values});"  # SQL statement to insert data
        
        try:
            # First, clear the table
            self.cursor.execute(delete_stmt)
            # Then, insert new data
            records = [tuple(x) for x in df.to_numpy()]  # Convert DataFrame rows to tuples
            psycopg2.extras.execute_batch(self.cursor, insert_stmt, records)  # Execute insert operation in batch
            self.connection.commit()  # Commit all changes to the database
            self.logger.info(f"Table '{table_name}' has been successfully updated.")
        except Exception as e:
            self.logger.error(f"Error updating table '{table_name}': {e}")
            self.connection.rollback()  # Rollback in case of any error

    def fetch_data(self, table_name, condition=None):
        """
        Fetch data from the specified table with an optional condition and return it as a pandas DataFrame.

        Parameters:
        - table_name (str): The name of the table to fetch data from.
        - condition (str, optional): A SQL condition string to be included in the WHERE clause.

        Returns:
        - pd.DataFrame: A DataFrame containing the data fetched from the table. Returns None if an error occurs.
        """
        base_query = f"SELECT * FROM {table_name}"
        query = base_query + (f" WHERE {condition}" if condition else "") + ";"

        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            self.logger.info(f"Successfully fetched data from {table_name} with condition '{condition}'.")
            return df
        except Exception as e:
            self.logger.error(f"Error fetching data from {table_name} with condition '{condition}': {e}")
            return None

# craete function 
def create_rawdata_table(logger):
    """
    Create a specified schema and a table within that schema in the 'datawarehouse' database.

    This function first establishes a connection to the 'datawarehouse' database, then creates a 
    schema named 'source_data'. After the schema is successfully created, it creates a 'job_listings_104' 
    table within this schema if it does not already exist.

    Parameters:
    - logger (logging.Logger): A Logger object for logging information and errors.

    The table 'job_listings_104' will have various fields such as id, job_title, company_name, etc.,
    with appropriate data types assigned to each field.
    """
    # Establish a connection to the 'datawarehouse' database.
    connector = DatabaseConnector(logger)
    connection = connector.connect_to_db('datawarehouse')
    db_operation = DatabaseOperation(connection, logger)

    # Create a new schema named 'datawarehouse'.
    schema_name = "source_data"  # Define the schema name to be created.
    db_operation.create_schema(schema_name)

    # Create the 'job_listings_104' table within the newly created schema.
    job_listings_104_table_query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.job_listings_104 (
        id SERIAL PRIMARY KEY,
        job_title VARCHAR(255) NOT NULL,
        company_name VARCHAR(255) NOT NULL,
        salary VARCHAR(255),
        location VARCHAR(255),
        job_description TEXT,
        job_type VARCHAR(50),
        degree_required VARCHAR(255),
        major_required VARCHAR(255),
        experience VARCHAR(255),
        skill TEXT,
        tools TEXT,
        others TEXT,
        url TEXT,
        crawl_date DATE,
        unique_col TEXT UNIQUE
        );
    """
    # Execute the SQL query to create the table.
    db_operation.create_table(job_listings_104_table_query)

    # Close the database connection.
    connection.close()

def create_stagedata_table(logger):
    """
    Create a specified schema and a table within that schema in the 'datawarehouse' database.

    This function first establishes a connection to the 'datawarehouse' database, then creates a 
    schema named 'staging_data'. After the schema is successfully created, it creates a 'job_listings_104' 
    table within this schema if it does not already exist.

    Parameters:
    - logger (logging.Logger): A Logger object for logging information and errors.
    """
    # Establish a connection to the 'datawarehouse' database.
    connector = DatabaseConnector(logger)
    connection = connector.connect_to_db('datawarehouse')
    db_operation = DatabaseOperation(connection, logger)

    # Create a new schema named 'staging_data'.
    schema_name = "staging_data"
    db_operation.create_schema(schema_name)

    # Create the 'job_listings_104' table within the newly created schema.
    job_listings_104_table_query = f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.job_listings_104 (
        id SERIAL PRIMARY KEY,
        data_role VARCHAR(255) NOT NULL,
        job_title VARCHAR(255) NOT NULL,
        company_name VARCHAR(255) NOT NULL,
        salary VARCHAR(255),
        county VARCHAR(255),
        location VARCHAR(255),
        job_description TEXT,
        job_type TEXT[], 
        degree_required TEXT[],  
        major_required TEXT[],  
        experience VARCHAR(255),
        skill TEXT[],  
        tools TEXT[],  
        others TEXT,
        url TEXT,
        crawl_date DATE,
        unique_col TEXT UNIQUE
        );
    """
    # Execute the SQL query to create the table.
    db_operation.create_table(job_listings_104_table_query)

    # Close the database connection.
    connection.close()

class RenderTablesCreator:
    def create_render_rpt_job_openings_metrics_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_job_openings_metrics' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_job_openings_metrics' table within the newly created schema.
        rpt_job_openings_metrics_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_job_openings_metrics (
                total_openings INT,
                closed_openings_count INT,
                new_openings_count INT,
                fill_rate FLOAT,
                crawl_date VARCHAR(255) PRIMARY KEY
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_job_openings_metrics_query)

    def create_render_rpt_job_fill_time_statistics_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_job_fill_time_statistics' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_job_fill_time_statistics' table within the newly created schema.
        rpt_job_fill_time_statistics_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_job_fill_time_statistics (
                average_weeks_to_fill FLOAT,
                "current_date" VARCHAR(255) PRIMARY KEY
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_job_fill_time_statistics_query)

    def create_render_rpt_data_role_vacancy_trends_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_data_role_vacancy_trends' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_data_role_vacancy_trends' table within the newly created schema.
        rpt_data_role_vacancy_trends_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_data_role_vacancy_trends (
                data_role VARCHAR(255),
                count INT,
                crawl_date VARCHAR(255),
                PRIMARY KEY (data_role, crawl_date)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_data_role_vacancy_trends_query)

    def create_render_rpt_data_tools_trends_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_data_tools_trends' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_data_tools_trends' table within the newly created schema.
        rpt_data_tools_trends_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_data_tools_trends (
                rank INT,
                category VARCHAR(255),
                tool_name VARCHAR(255),
                tool_count INT,
                crawl_date VARCHAR(255),
                PRIMARY KEY (tool_name, crawl_date)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_data_tools_trends_query)

    def create_render_rpt_weekly_company_job_vacancies_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'render_deploy' database.

        This function first establishes a connection to the 'render_deploy' database, then creates a 
        schema named 'remote_reporting_data'. After the schema is successfully created, it creates a 
        'rpt_weekly_company_job_vacancies' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_weekly_company_job_vacancies' table within the newly created schema.
        rpt_weekly_company_job_vacancies_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_weekly_company_job_vacancies (
                rank INT,
                company_name VARCHAR(255),
                opening_count INT,
                crawl_date VARCHAR(255),
                PRIMARY KEY (company_name, crawl_date)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_weekly_company_job_vacancies_query)

    def create_rpt_job_openings_geograph_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_job_openings_geograph' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_job_openings_geograph' table within the newly created schema.
        rpt_job_openings_geograph_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_job_openings_geograph (
                county_name_eng VARCHAR(255),
                district_name_eng VARCHAR(255),
                openings_count INT,
                crawl_date VARCHAR(255)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_job_openings_geograph_query)

    def create_rpt_data_tools_by_data_role_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_data_tools_by_data_role' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_data_tools_by_data_role' table within the newly created schema.
        rpt_data_tools_by_data_role_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_data_tools_by_data_role (
                data_role VARCHAR(255),
                category VARCHAR(255),
                tool_name VARCHAR(255),
                count INT,
                crawl_date VARCHAR(255)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_data_tools_by_data_role_query)

    def create_rpt_data_role_by_edu_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'reporting_data'. After the schema is successfully created, it creates a 
        'rpt_data_role_by_edu' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "reporting_data"

        # Create the 'rpt_data_role_by_edu' table within the newly created schema.
        rpt_data_role_by_edu_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.rpt_data_role_by_edu (
                data_role VARCHAR(255),
                degree VARCHAR(255),
                count INT,
                crawl_date VARCHAR(255),
                PRIMARY KEY (data_role, degree, crawl_date)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(rpt_data_role_by_edu_query)

    def create_er_district_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'modeling_data'. After the schema is successfully created, it creates a 
        'er_district' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "modeling_data"

        # Create the 'rpt_data_role_by_edu' table within the newly created schema.
        er_district_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.er_district (
                district_id VARCHAR(255) PRIMARY KEY ,
                district_name_ch VARCHAR(255),
                district_name_eng VARCHAR(255),
                county VARCHAR(255)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(er_district_query)

    def create_er_county_table(db_operation):
        """
        Create a specified schema and a table within that schema in the 'datawarehouse' database.

        This function first establishes a connection to the 'datawarehouse' database, then creates a 
        schema named 'modeling_data'. After the schema is successfully created, it creates a 
        'er_county' table within this schema if it does not already exist.

        Parameters:
        - logger (logging.Logger): A Logger object for logging information and errors.
        """
        schema_name = "modeling_data"

        # Create the 'rpt_data_role_by_edu' table within the newly created schema.
        er_county_query = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.er_county (
                county_id VARCHAR(255) PRIMARY KEY ,
                county_name_ch VARCHAR(255),
                county_name_eng VARCHAR(255)
            );
        """
        # Execute the SQL query to create the table.
        db_operation.create_table(er_county_query)
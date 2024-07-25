import sys, os
import toml

# setup project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from utils.log_utils import set_logger
from utils.database_utils import DatabaseConnector

logger = set_logger()
connector = DatabaseConnector(logger)
datawarehouse_conn = connector.connect_to_db('datawarehouse')
render_database_conn = connector.connect_to_db('render_deploy')
from google.cloud.logging import Client

logging_client = Client.from_service_account_json("sa.json")
gcp_logger = logging_client.logger("lawsy-gcp-logger")

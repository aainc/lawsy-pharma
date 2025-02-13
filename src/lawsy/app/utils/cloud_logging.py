from google.cloud.logging import Client

logging_client = Client()
gcp_logger = logging_client.logger("lawsy-gcp-logger")

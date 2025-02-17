import os
from pathlib import Path

from google.cloud.logging import Client

key_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "sa.json"

if Path(key_file).exists():
    logging_client = Client.from_service_account_json(key_file)
else:
    logging_client = Client()
gcp_logger = logging_client.logger("lawsy-gcp-logger")

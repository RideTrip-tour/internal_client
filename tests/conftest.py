import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from src.internal_client import InternalClient


@pytest.fixture
def initial_client():
    InternalClient._instance = None

    client = InternalClient(
        base_url="http://localhost",
        service_id="service_id",
        service_token="service_token",
        gateway_name="gateway_name",
        access_token_expire_sec=50,
        jwt_secret="jwt_secret",
    )

    yield client

    InternalClient._instance = None

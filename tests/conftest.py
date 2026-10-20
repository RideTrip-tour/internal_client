import pytest
import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from src.initial_client import InitialClient


@pytest.fixture
def initial_client():
    InitialClient._instance = None

    client = InitialClient(
        base_url="http://localhost",
        service_id="service_id",
        service_token="service_token",
        gateway_name="gateway_name",
        access_token_expire_sec=50,
        jwt_secret="jwt_secret",
    )

    yield client

    InitialClient._instance = None

import pytest

from agentpath.testing.mock_server import serve


@pytest.fixture
def mock_url():
    base_url, shutdown = serve()
    yield base_url
    shutdown()

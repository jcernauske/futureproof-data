import pytest

try:
    from fastapi.testclient import TestClient

    from app.main import app

    @pytest.fixture
    def client() -> TestClient:
        return TestClient(app)

except ModuleNotFoundError:
    # FastAPI isn't installed in the root CLI venv. Backend API tests
    # that need the `client` fixture will skip cleanly; service-layer
    # tests under ``tests/services/`` don't use it at all.
    pass

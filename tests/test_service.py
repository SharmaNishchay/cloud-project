import sys
sys.path.insert(0, "service")
import app as svc  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

GOOD = '{"intent": "alarm_set", "date": "tomorrow", "time": "seven am", "place": null}'
client = TestClient(svc.app)  # no `with`: startup (model download) is not run


def setup_function():
    svc.STATE["ready"] = True
    svc.generate = lambda text: GOOD


def test_readyz_503_until_loaded():
    svc.STATE["ready"] = False
    assert client.get("/readyz").status_code == 503
    assert client.get("/healthz").status_code == 200
    svc.STATE["ready"] = True
    assert client.get("/readyz").status_code == 200


def test_parse_ok_and_headers(monkeypatch):
    monkeypatch.setenv("MODEL_VERSION", "v1")
    r = client.post("/parse", json={"text": "set an alarm"})
    assert r.status_code == 200 and r.json()["intent"] == "alarm_set"
    assert r.headers["X-Model-Version"] == "v1" and r.headers["X-Served-By"]


def test_fault_injection(monkeypatch):
    monkeypatch.setenv("FAULT_INJECT", "1")
    r = client.post("/parse", json={"text": "x"})
    assert r.status_code == 500 and r.json() == {"error": "invalid_model_output"}


def test_broken_output_never_200():
    svc.generate = lambda text: '{"intent": "alarm_set", "date": "tomo'
    assert client.post("/parse", json={"text": "x"}).status_code == 500
    svc.generate = lambda text: '{"intent": "bogus", "date": null, "time": null, "place": null}'
    assert client.post("/parse", json={"text": "x"}).status_code == 500

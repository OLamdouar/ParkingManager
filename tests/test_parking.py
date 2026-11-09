from fastapi.testclient import TestClient

from app.main import app, parkings, spots

client = TestClient(app)


def setup_function():
    parkings.clear()
    spots.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_parking_generates_spots():
    r = client.post(
        "/parkings",
        json={"name": "Centre", "address": "1 rue A", "car_spots": 3, "motorcycle_spots": 2},
    )
    assert r.status_code == 201
    pid = r.json()["id"]
    all_spots = client.get(f"/parkings/{pid}/spots").json()
    assert len(all_spots) == 5
    motos = client.get(f"/parkings/{pid}/spots", params={"vehicle_type": "motorcycle"}).json()
    assert len(motos) == 2


def test_availability_updates_after_status_change():
    pid = client.post(
        "/parkings",
        json={"name": "Gare", "address": "2 rue B", "car_spots": 2, "motorcycle_spots": 1},
    ).json()["id"]
    spot_id = client.get(f"/parkings/{pid}/spots", params={"vehicle_type": "car"}).json()[0]["id"]
    r = client.patch(f"/spots/{spot_id}", json={"status": "occupied"})
    assert r.status_code == 200
    avail = client.get(f"/parkings/{pid}/availability").json()["availability"]
    assert avail["car"] == {"total": 2, "free": 1}
    assert avail["motorcycle"] == {"total": 1, "free": 1}


def test_unknown_parking_returns_404():
    assert client.get("/parkings/999").status_code == 404


def test_delete_parking_removes_spots():
    pid = client.post(
        "/parkings", json={"name": "X", "address": "Y", "car_spots": 2}
    ).json()["id"]
    assert client.delete(f"/parkings/{pid}").status_code == 204
    assert client.get(f"/parkings/{pid}").status_code == 404
    assert len(spots) == 0


def test_validation_rejects_negative_spots():
    r = client.post("/parkings", json={"name": "X", "address": "Y", "car_spots": -1})
    assert r.status_code == 422

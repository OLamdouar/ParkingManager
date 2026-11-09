"""Service Parkings : gère les parkings et leurs places (voiture / moto)."""


from enum import Enum
from itertools import count
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Parking Service", version="1.0.0")


class VehicleType(str, Enum):
    car = "car"
    motorcycle = "motorcycle"


class SpotStatus(str, Enum):
    free = "free"
    occupied = "occupied"
    reserved = "reserved"


class ParkingIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=200)
    car_spots: int = Field(ge=0, le=1000, default=0)
    motorcycle_spots: int = Field(ge=0, le=1000, default=0)


class Parking(ParkingIn):
    id: int


class Spot(BaseModel):
    id: int
    parking_id: int
    number: int
    vehicle_type: VehicleType
    status: SpotStatus = SpotStatus.free


class SpotStatusUpdate(BaseModel):
    status: SpotStatus


_parking_ids = count(1)
_spot_ids = count(1)
parkings: dict[int, Parking] = {}
spots: dict[int, Spot] = {}


def _create_spots(parking: Parking) -> None:
    number = 1
    for vehicle_type, qty in (
        (VehicleType.car, parking.car_spots),
        (VehicleType.motorcycle, parking.motorcycle_spots),
    ):
        for _ in range(qty):
            spot_id = next(_spot_ids)
            spots[spot_id] = Spot(
                id=spot_id,
                parking_id=parking.id,
                number=number,
                vehicle_type=vehicle_type,
            )
            number += 1


def _get_parking(parking_id: int) -> Parking:
    if parking_id not in parkings:
        raise HTTPException(status_code=404, detail="Parking introuvable")
    return parkings[parking_id]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/parkings", response_model=Parking, status_code=201)
def create_parking(data: ParkingIn) -> Parking:
    parking = Parking(id=next(_parking_ids), **data.model_dump())
    parkings[parking.id] = parking
    _create_spots(parking)
    return parking


@app.get("/parkings", response_model=list[Parking])
def list_parkings() -> list[Parking]:
    return list(parkings.values())


@app.get("/parkings/{parking_id}", response_model=Parking)
def get_parking(parking_id: int) -> Parking:
    return _get_parking(parking_id)


@app.delete("/parkings/{parking_id}", status_code=204)
def delete_parking(parking_id: int) -> None:
    _get_parking(parking_id)
    del parkings[parking_id]
    for spot_id in [s.id for s in spots.values() if s.parking_id == parking_id]:
        del spots[spot_id]


@app.get("/parkings/{parking_id}/spots", response_model=list[Spot])
def list_spots(
    parking_id: int,
    vehicle_type: Optional[VehicleType] = Query(default=None),
    status: Optional[SpotStatus] = Query(default=None),
) -> list[Spot]:
    _get_parking(parking_id)
    result = [s for s in spots.values() if s.parking_id == parking_id]
    if vehicle_type:
        result = [s for s in result if s.vehicle_type == vehicle_type]
    if status:
        result = [s for s in result if s.status == status]
    return result


@app.get("/parkings/{parking_id}/availability")
def availability(parking_id: int) -> dict:
    _get_parking(parking_id)
    summary = {t.value: {"total": 0, "free": 0} for t in VehicleType}
    for s in spots.values():
        if s.parking_id == parking_id:
            summary[s.vehicle_type.value]["total"] += 1
            if s.status == SpotStatus.free:
                summary[s.vehicle_type.value]["free"] += 1
    return {"parking_id": parking_id, "availability": summary}


@app.patch("/spots/{spot_id}", response_model=Spot)
def update_spot_status(spot_id: int, data: SpotStatusUpdate) -> Spot:
    if spot_id not in spots:
        raise HTTPException(status_code=404, detail="Place introuvable")
    spots[spot_id].status = data.status
    return spots[spot_id]

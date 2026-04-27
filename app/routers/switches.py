from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.switch_service import (
    freeze_port,
    list_campus_names,
    list_frozen_ports,
    list_switches_for_campus,
    unfreeze_port,
)
from app.services.sync_service import clear_batch_switches, sync_batch_switches

router = APIRouter()


class BatchSyncRequest(BaseModel):
    serials: list[str]
    nom_campus: str


@router.get("/campus", dependencies=[Depends(get_current_user)])
async def llistar_campus():
    return await list_campus_names()


@router.get("/campus/{nom_campus}/switches", dependencies=[Depends(get_current_user)])
async def switches_per_campus(nom_campus: str):
    return await list_switches_for_campus(nom_campus)


@router.get("/switch/{serial}/frozen-ports", dependencies=[Depends(get_current_user)])
async def llistar_congelats(serial: str):
    return await list_frozen_ports(serial)


@router.post("/switch/{serial}/port/{port}/freeze", dependencies=[Depends(get_current_user)])
async def congelar_port(serial: str, port: int):
    return await freeze_port(serial, port)


@router.post("/switch/{serial}/port/{port}/unfreeze", dependencies=[Depends(get_current_user)])
async def descongelar_port(serial: str, port: int):
    return await unfreeze_port(serial, port)


@router.post("/campus/sync-batch", dependencies=[Depends(get_current_user)])
async def sync_batch(request: BatchSyncRequest):
    return await sync_batch_switches(request.serials, request.nom_campus)


@router.post("/campus/clear-batch", dependencies=[Depends(get_current_user)])
async def clear_batch(request: BatchSyncRequest):
    return await clear_batch_switches(request.serials, request.nom_campus)

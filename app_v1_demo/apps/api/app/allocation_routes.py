"""Read-only endpoint for the allocation POC. It does not touch the V1 simulation engine."""
from fastapi import APIRouter

from packages.allocation.export_demo import build_demo

router = APIRouter()


@router.get("/api/allocation/demo")
def allocation_demo():
    return build_demo()

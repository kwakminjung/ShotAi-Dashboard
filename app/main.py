import logging
import subprocess
import sys
import time
import asyncio
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import NATS_SERVER, LOG_LEVEL
from app.database import (
    init_db, 
    save_monitor_metric, 
    get_latest_metric, 
    get_latest_triton_metric,
    save_inference_metric,
    get_latest_inference_metric,
)
from app.triton_metrics.triton_metrics_collector import start_metrics_collector

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("FastAPI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    metrics_collector_task = asyncio.create_task(start_metrics_collector())
    
    workers = []

    try:
        p1 = subprocess.Popen(
            [sys.executable, "app/nats/nats_stream.py", "--nats", NATS_SERVER]
        )
        workers.append(p1)
        logger.info(f"Started nats_stream.py (PID: {p1.pid})")

        p2 = subprocess.Popen(
            [sys.executable, "app/nats/nats_inference_worker.py", "--nats", NATS_SERVER]
        )
        workers.append(p2)
        logger.info(f"Started nats_inference_worker.py (PID: {p2.pid})")

    except Exception as e:
        logger.error(f"Failed to start workers: {e}")
        for p in workers:
            p.terminate()
        metrics_collector_task.cancel()
        yield 
        return

    yield
    
    logger.info("Shutting down workers...")
    
    metrics_collector_task.cancel()

    for p in workers:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception as e:
            logger.error(f"Error terminating worker {p.pid}: {e}")
            p.kill()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/ingest")
async def ingest_data(data: dict):
    msg_type = data.get("type")
    
    if msg_type == "monitor":
        await save_monitor_metric(data)
    elif msg_type == "inference":
        await save_inference_metric(data)
    
    await manager.broadcast(data)
    return {"status": "ok"}

@app.get("/api/metrics/latest")
async def get_latest_metrics():
    metric = get_latest_metric()
    if metric:
        return metric
    return {"error": "No metrics available"}

@app.get("/api/triton/metrics/latest")
async def get_latest_triton_metrics():
    metric = get_latest_triton_metric()
    if metric:
        return metric
    return {"error": "No triton metrics available"}

@app.get("/api/inference/latest")
async def get_latest_inference_metrics():
    metric = get_latest_inference_metric()
    if metric:
        return metric
    return {"error": "No inference metrics available"}

@app.get("/")
async def get():
    return FileResponse("static/index.html")
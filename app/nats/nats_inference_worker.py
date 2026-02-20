#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import json
import logging
import httpx
import time

import nats
from nats.errors import NoServersError
from app.config import API_BASE_URL, LOG_LEVEL

LOG = logging.getLogger("nats-inf-worker")

WEB_SERVER_URL = f"{API_BASE_URL}/api/ingest" 

def setup_logging(level_name=None):
    if level_name is None:
        level_name = LOG_LEVEL
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    LOG.setLevel(level)

async def send_to_web_server(payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(WEB_SERVER_URL, json=payload, timeout=5.0)
        except Exception as e:
            LOG.error(f"Failed to send inference data: {e}")

async def main_async():
    p = argparse.ArgumentParser(description="NATS Inference Worker")
    p.add_argument("--nats", required=True, help="NATS Server URL")
    p.add_argument("--subject", default="shotai.sbc.inference.*", help="Subject")
    p.add_argument("--log", default="INFO", help="Log level")
    args = p.parse_args()

    setup_logging(args.log)

    try:
        nc = await nats.connect(servers=args.nats)
    except NoServersError:
        LOG.error("Cannot connect to NATS")
        return

    LOG.info("Inference Worker Started. Listening on %s", args.subject)

    async def on_inference_msg(msg):
        try:
            raw_data = json.loads(msg.data.decode())

            ts = time.localtime(raw_data.get('timestamp', time.time()))
            formatted_ts = time.strftime('%Y-%m-%d %H:%M:%S', ts)
            
            payload = {
                "type": "inference",
                "client_id": raw_data.get('client_id', 'unknown'),
                "timestamp": formatted_ts,
                "frames_total": raw_data.get("frames_total", 0),
                "frames_visible": raw_data.get("frames_visible", 0),
                "frames_pred": raw_data.get("frames_pred", 0),
                "mae_px": raw_data.get("mae_px"),
                "rmse_px": raw_data.get("rmse_px"),
                "pck": raw_data.get("pck"),
                "pck_thresh_px": raw_data.get("pck_thresh_px"),
                "elapsed_sec": raw_data.get("elapsed_sec"),
                "pred_format": raw_data.get("pred_format"),
                "gt_format": raw_data.get("gt_format"),
            }
            await send_to_web_server(payload)
            LOG.info(f"Sent payload to web server: {payload['client_id']}")
            
        except Exception as e:
            LOG.error(f"Error processing inference msg: {e}")

    await nc.subscribe(args.subject, queue="inference_workers", cb=on_inference_msg)

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
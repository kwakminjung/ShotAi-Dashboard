import argparse
import asyncio
import json
import logging
import time
import httpx

import nats
from nats.errors import NoServersError

from config import API_BASE_URL, LOG_LEVEL

LOG = logging.getLogger("nats-sub-worker")

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
            await client.post(WEB_SERVER_URL, json=payload)
        except Exception as e:
            LOG.error(f"Failed to send data to web server: {e}")

async def main_async():
    p = argparse.ArgumentParser(description="NATS Subscriber & Web Forwarder")
    p.add_argument("--nats", required=True, help="nats://...")
    p.add_argument("--subject", default="shotai.demo.echo", help="listening subject")
    p.add_argument("--log", default="INFO", help="log level")
    args = p.parse_args()

    setup_logging(args.log)

    try:
        nc = await nats.connect(servers=args.nats)
    except NoServersError:
        LOG.error("cannot connect NATS: %s", args.nats)
        return 2

    LOG.info("connected to NATS: %s , subscriber started", args.nats)

    async def on_msg(msg):
        try:
            raw_data = json.loads(msg.data.decode())
            ts = time.localtime(raw_data.get('ts', time.time()))
            formatted_ts = time.strftime('%Y-%m-%d %H:%M:%S', ts)
            
            payload = {}

            if "heartbeat" in msg.subject:
                payload = {
                    "type": "heartbeat",
                    "client_id": raw_data.get('client_id', 'unknown'),
                    "timestamp": formatted_ts,
                    "uptime_sec": raw_data.get('uptime_sec', 0)
                }
                LOG.debug(f"Heartbeat received: {payload['client_id']}")

            elif "monitor" in msg.subject:
                payload = {
                    "type": "monitor",
                    "timestamp": formatted_ts,
                    "content": raw_data  # 원본 전체 데이터
                }
                LOG.debug("Monitor data received")

            if payload:
                await send_to_web_server(payload)

        except Exception as e:
            LOG.error(f"Error processing message: {e}")

    # 구독 시작
    await nc.subscribe("shotai.sbc.heartbeat.*", cb=on_msg)
    await nc.subscribe("shotai.sbc.monitor.*", cb=on_msg)

    # 무한 대기
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        LOG.info("exiting on user request")
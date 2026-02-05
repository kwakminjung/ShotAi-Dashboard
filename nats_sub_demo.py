import argparse
import asyncio
import json
import logging
import time

import nats
from nats.errors import NoServersError

LOG = logging.getLogger("nats-sub-demo")

def setup_logging(level_name="INFO"):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    LOG.setLevel(level)

async def main_async():
    p = argparse.ArgumentParser(description="NATS Subscriber")
    p.add_argument("--nats", required=True, help="nats://...")
    p.add_argument("--subject", default="shotai.demo.echo", help="listening subject")
    p.add_argument("--log", default="INFO", help="log level")
    p.add_argument("--count", type=int, default=999999, help="stop after n messages") 
    args = p.parse_args()

    setup_logging(args.log)

    try:
        nc = await nats.connect(servers=args.nats)
    except NoServersError:
        LOG.error("cannot connect NATS: %s", args.nats)
        return 2

    LOG.info("connected to NATS: %s , subscriber", args.nats)

    async def on_msg(msg):
        data = json.loads(msg.data.decode())

        ts = time.localtime(data['ts'])
        formatted_ts = time.strftime('%Y-%m-%d %H:%M:%S', ts)
        
        if "heartbeat" in msg.subject:
            print(f"[SUBJ: heartbeat] node_id:{data['client_id']} ts: {formatted_ts} Uptime:{data['uptime_sec']}s")
        elif "monitor" in msg.subject:
            print(f"[SUBJ: monitor] {json.dumps(data, indent=2, ensure_ascii=False)}")

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
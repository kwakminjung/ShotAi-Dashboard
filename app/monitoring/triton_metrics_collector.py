import logging
import asyncio
import re
from datetime import datetime, timezone, timedelta
import httpx

from app.config import TRITON_SERVER
from app.database import save_triton_metric

logger = logging.getLogger("triton_metrics_collector")
logging.basicConfig(level=logging.INFO)

METRICS_URL = f"{TRITON_SERVER}/metrics"
KST = timezone(timedelta(hours=9))

def parse_metrics(metrics_text: str) -> dict:
    metrics = {
        "timestamp": datetime.now(KST),
        "gpu": {
            "utilization": None,
            "memory_total_bytes": None,
            "memory_used_bytes": None,
            "power_usage": None,
            "power_limit": None,
        },
        "cpu": {
            "utilization": None,
            "memory_total_bytes": None,
            "memory_used_bytes": None,
        },
    }

    lines = metrics_text.split("\n")
    logger.debug(f"Total lines in metrics response: {len(lines)}")

    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        if "nv_gpu_utilization" in line:
            match = re.search(r"nv_gpu_utilization.*?}\s+([\d\.]+)", line)
            if match: metrics["gpu"]["utilization"] = float(match.group(1))

        elif "nv_gpu_memory_total_bytes" in line:
            match = re.search(r"nv_gpu_memory_total_bytes.*?}\s+(\d+)", line)
            if match: metrics["gpu"]["memory_total_bytes"] = int(match.group(1))

        elif "nv_gpu_memory_used_bytes" in line:
            match = re.search(r"nv_gpu_memory_used_bytes.*?}\s+(\d+)", line)
            if match: metrics["gpu"]["memory_used_bytes"] = int(match.group(1))

        elif "nv_gpu_power_usage" in line:
            match = re.search(r"nv_gpu_power_usage.*?}\s+([\d\.]+)", line)
            if match: metrics["gpu"]["power_usage"] = float(match.group(1))

        elif "nv_gpu_power_limit" in line and not line.startswith("#"):
            match = re.search(r"nv_gpu_power_limit.*?(\d+)", line)
            if match:
                metrics["gpu"]["power_limit"] = int(match.group(1))
                # logger.debug(f"GPU power limit: {match.group(1)}")

        # CPU 메트릭 파싱
        elif "nv_cpu_utilization" in line and not line.startswith("#"):
            match = re.search(r"nv_cpu_utilization.*?(\d+\.?\d*)", line)
            if match:
                metrics["cpu"]["utilization"] = float(match.group(1))
                # logger.debug(f"CPU utilization: {match.group(1)}")

        elif "nv_cpu_memory_total_bytes" in line and not line.startswith("#"):
            match = re.search(r"nv_cpu_memory_total_bytes.*?(\d+)", line)
            if match:
                metrics["cpu"]["memory_total_bytes"] = int(match.group(1))
                # logger.debug(f"CPU memory total: {match.group(1)}")

        elif "nv_cpu_memory_used_bytes" in line and not line.startswith("#"):
            match = re.search(r"nv_cpu_memory_used_bytes.*?(\d+)", line)
            if match:
                metrics["cpu"]["memory_used_bytes"] = int(match.group(1))
                # logger.debug(f"CPU memory used: {match.group(1)}")

    # logger.info(f"Parsed metrics - GPU: {metrics['gpu']}, CPU: {metrics['cpu']}")
    return metrics


async def fetch_triton_metrics() -> dict:
    try:
        logger.info(f"Fetching metrics from {METRICS_URL}")
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(METRICS_URL, timeout=10.0)
            response.raise_for_status()
            # logger.info("Successfully fetched metrics from Triton server")
            # logger.debug(f"Response (first 1000 chars):\n{response.text[:1000]}")
            return parse_metrics(response.text)
    except Exception as e:
        logger.error(f"Failed to fetch Triton metrics: {e}")
        return None


def convert_bytes_to_gb(bytes_value: int) -> float:
    if bytes_value is None:
        return None
    return bytes_value / (1024**3)


async def save_metrics_to_db(metrics: dict):
    if not metrics:
        logger.warning("No metrics to save")
        return

    # logger.info(f"Processing metrics: GPU={metrics.get('gpu', {})}, CPU={metrics.get('cpu', {})}")

    # GPU 메트릭 변환
    gpu_memory_total_gb = convert_bytes_to_gb(
        metrics["gpu"]["memory_total_bytes"]
    )
    gpu_memory_used_gb = convert_bytes_to_gb(metrics["gpu"]["memory_used_bytes"])
    gpu_memory_percent = None
    if (
        gpu_memory_total_gb
        and gpu_memory_used_gb
        and gpu_memory_total_gb > 0
    ):
        gpu_memory_percent = (gpu_memory_used_gb / gpu_memory_total_gb) * 100

    # CPU 메트릭 변환
    cpu_memory_total_gb = convert_bytes_to_gb(
        metrics["cpu"]["memory_total_bytes"]
    )
    cpu_memory_used_gb = convert_bytes_to_gb(metrics["cpu"]["memory_used_bytes"])
    cpu_memory_percent = None
    if (
        cpu_memory_total_gb
        and cpu_memory_used_gb
        and cpu_memory_total_gb > 0
    ):
        cpu_memory_percent = (cpu_memory_used_gb / cpu_memory_total_gb) * 100

    # 변환된 메트릭 추가
    metrics["gpu"]["memory_total_gb"] = gpu_memory_total_gb
    metrics["gpu"]["memory_used_gb"] = gpu_memory_used_gb
    metrics["gpu"]["memory_percent"] = gpu_memory_percent
    
    metrics["cpu"]["memory_total_gb"] = cpu_memory_total_gb
    metrics["cpu"]["memory_used_gb"] = cpu_memory_used_gb
    metrics["cpu"]["memory_percent"] = cpu_memory_percent

    logger.info("Calling save_triton_metric...")
    await save_triton_metric(metrics)
    
    # logger.info(
    #     f"Saved metrics - GPU: {metrics['gpu']['utilization']}%, "
    #     f"CPU: {metrics['cpu']['utilization']}%, "
    #     f"GPU Memory: {gpu_memory_used_gb:.2f}GB/{gpu_memory_total_gb:.2f}GB" if gpu_memory_used_gb and gpu_memory_total_gb else "N/A"
    # )


async def start_metrics_collector(interval: int = 1):
    """5초 간격으로 메트릭 수집 시작"""
    logger.info(f"Starting Triton metrics collector (interval: {interval}s)")

    while True:
        try:
            metrics = await fetch_triton_metrics()
            if metrics:
                await save_metrics_to_db(metrics)
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"Error in metrics collector loop: {e}")
            await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(start_metrics_collector())

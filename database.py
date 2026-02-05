import logging
from datetime import datetime, timezone, timedelta
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from config import DATABASE_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger("database")

# 데이터베이스 설정
engine = create_engine(DATABASE_URL, echo=False, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
KST = timezone(timedelta(hours=9))

def kst_now():
    return datetime.now(KST)

def create_database_if_not_exists():
    try:
        root_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
        root_engine = create_engine(root_url, echo=False)
        
        with root_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            conn.commit()
            logger.info(f"Database '{DB_NAME}' is ready")
        
        root_engine.dispose()
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

"""
def clear_metrics_table():
    # 서버 시작 시 metrics 테이블 초기화
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE metrics"))
            conn.execute(text("TRUNCATE TABLE triton_metrics"))
            conn.execute(text("TRUNCATE TABLE inference_metrics"))
            conn.commit()
            logger.info("Metrics tables cleared (all old data removed)")
    except Exception as e:
        logger.warning(f"Could not clear metrics tables (may not exist yet): {e}")
"""
        
class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=kst_now, index=True)
    client_id = Column(String(255), nullable=True, index=True)
    
    # Computing Resource
    cpu_percent = Column(Float, nullable=True)
    memory_total_gb = Column(Float, nullable=True)
    memory_used_gb = Column(Float, nullable=True)
    memory_percent = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    docker_top = Column(JSON, nullable=True)
    proc_top = Column(JSON, nullable=True)
    
    # Network Resource
    bandwidth_mbps = Column(Float, nullable=True)
    rx_rate = Column(Float, nullable=True)
    tx_rate = Column(Float, nullable=True)
    rtt = Column(Float, nullable=True)
    jitter = Column(Float, nullable=True)
    drops = Column(Integer, nullable=True)
    errors = Column(Integer, nullable=True)
    packet_loss_percent = Column(Float, nullable=True)
    
    # 원본 데이터
    raw_data = Column(JSON, nullable=True)


class TritonMetric(Base):
    """Triton 서버 메트릭 테이블"""
    __tablename__ = "triton_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=kst_now, index=True)
    
    # GPU 메트릭
    gpu_utilization = Column(Float, nullable=True)
    gpu_memory_total_gb = Column(Float, nullable=True)
    gpu_memory_used_gb = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_power_usage_watts = Column(Float, nullable=True)
    gpu_power_limit_watts = Column(Float, nullable=True)
    
    # CPU 메트릭
    cpu_utilization = Column(Float, nullable=True)
    cpu_memory_total_gb = Column(Float, nullable=True)
    cpu_memory_used_gb = Column(Float, nullable=True)
    cpu_memory_percent = Column(Float, nullable=True)
    
    # 원본 데이터
    raw_data = Column(JSON, nullable=True)

class InferenceMetric(Base):
    __tablename__ = "inference_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=kst_now, index=True)
    client_id = Column(String(255), nullable=True, index=True)
    mae_px = Column(Float, nullable=True)
    rmse_px = Column(Float, nullable=True)
    pck = Column(Float, nullable=True)
    pck_thresh_px = Column(Float, nullable=True)
    frames_total = Column(Integer, nullable=True)
    frames_visible = Column(Integer, nullable=True)
    frames_pred = Column(Integer, nullable=True)
    elapsed_sec = Column(Float, nullable=True)
    pred_format = Column(String(50), nullable=True)
    gt_format = Column(String(50), nullable=True)

    # 원본 데이터
    raw_data = Column(JSON, nullable=True)

def init_db():
    try:
        # 1. 데이터베이스가 없으면 생성
        create_database_if_not_exists()
        
        # 2. 모든 테이블 생성 (metrics, triton_metrics)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # 3. 기존 메트릭 데이터 초기화
        # clear_metrics_table()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def save_monitor_metric(data: dict):
    db = SessionLocal()
    try:
        try:
            from dateutil import parser
            timestamp = parser.parse(data.get("timestamp", datetime.utcnow().isoformat()))
        except:
            timestamp = datetime.utcnow()

        content = data.get("content", {})
        computing = content.get("computing_resource", {})
        network = content.get("network_resource", {})
        memory = computing.get("memory", {})
        
        metric = Metric(
            timestamp=timestamp,
            client_id=content.get("client_id", None),
            
            # Computing Resource
            cpu_percent=computing.get("cpu", None),
            memory_total_gb=memory.get("total_gb", None),
            memory_used_gb=memory.get("used_gb", None),
            memory_percent=memory.get("percent", None),
            disk_percent=computing.get("disk", None),
            gpu_percent=computing.get("gpu", None),
            temperature=computing.get("temperature", None),
            docker_top=computing.get("docker_top", None),
            proc_top=computing.get("proc_top", None),
            
            # Network Resource
            bandwidth_mbps=network.get("bandwidth", None),
            rx_rate=network.get("rx_rate", None),
            tx_rate=network.get("tx_rate", None),
            rtt=network.get("rtt", None),
            jitter=network.get("jitter", None),
            drops=network.get("drops", None),
            errors=network.get("errors", None),
            packet_loss_percent=network.get("packet_loss", None),
            
        )
        
        db.add(metric)
        db.commit()
        logger.debug(f"Metric saved for client: {content.get('client_id', 'unknown')}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save metric: {e}")
    finally:
        db.close()


async def save_triton_metric(metrics: dict):
    db = SessionLocal()
    try:
        logger.debug(f"Preparing to save triton metrics: {metrics}")

        ts = metrics.get("timestamp")

        if isinstance(ts, str):
            try:
                from dateutil import parser
                ts = parser.parse(ts)
            except:
                ts = datetime.now(KST)

        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        
        gpu_memory_total_gb = metrics.get("gpu", {}).get("memory_total_gb")
        gpu_memory_used_gb = metrics.get("gpu", {}).get("memory_used_gb")
        gpu_memory_percent = metrics.get("gpu", {}).get("memory_percent")
        
        cpu_memory_total_gb = metrics.get("cpu", {}).get("memory_total_gb")
        cpu_memory_used_gb = metrics.get("cpu", {}).get("memory_used_gb")
        cpu_memory_percent = metrics.get("cpu", {}).get("memory_percent")
        
        metric = TritonMetric(
            timestamp=ts,
            # GPU 메트릭
            gpu_utilization=metrics.get("gpu", {}).get("utilization"),
            gpu_memory_total_gb=gpu_memory_total_gb,
            gpu_memory_used_gb=gpu_memory_used_gb,
            gpu_memory_percent=gpu_memory_percent,
            gpu_power_usage_watts=metrics.get("gpu", {}).get("power_usage"),
            gpu_power_limit_watts=metrics.get("gpu", {}).get("power_limit"),
            # CPU 메트릭
            cpu_utilization=metrics.get("cpu", {}).get("utilization"),
            cpu_memory_total_gb=cpu_memory_total_gb,
            cpu_memory_used_gb=cpu_memory_used_gb,
            cpu_memory_percent=cpu_memory_percent,
            
            raw_data=json.dumps(metrics, default=str),
        )
        
        logger.debug("Created TritonMetric object, adding to session...")
        db.add(metric)
        logger.debug("Committing to database...")
        db.commit()
        logger.info(
            f"Triton metric saved - GPU: {metrics.get('gpu', {}).get('utilization')}%, "
            f"CPU: {metrics.get('cpu', {}).get('utilization')}%"
        )
        
    except Exception as e:
        logger.error(f"Failed to save triton metric: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

async def save_inference_metric(data: dict):
    db = SessionLocal()
    try:
        ts = data.get("timestamp")

        if isinstance(ts, str):
            try:
                from dateutil import parser
                ts = parser.parse(ts)
            except:
                ts = datetime.now(KST)

        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)

        metric = InferenceMetric(
            timestamp=ts,
            client_id=data.get("client_id"),
            mae_px=data.get("mae_px"),
            rmse_px=data.get("rmse_px"),
            pck=data.get("pck"),
            pck_thresh_px=data.get("pck_thresh_px"),
            frames_total=data.get("frames_total"),
            frames_visible=data.get("frames_visible"),
            frames_pred=data.get("frames_pred"),
            elapsed_sec=data.get("elapsed_sec"),
            pred_format=data.get("pred_format"),
            gt_format=data.get("gt_format"),
            raw_data=json.dumps(data, default=str)
        )
        
        db.add(metric)
        db.commit()
        logger.debug(f"Inference metric saved for client: {data.get('client_id')}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save inference metric: {e}")
    finally:
        db.close()

def get_latest_metric():
    db = SessionLocal()
    try:
        latest = db.query(Metric).order_by(Metric.id.desc()).first()
        
        if not latest:
            return None
        
        return {
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "client_id": latest.client_id,
            "cpu_percent": latest.cpu_percent,
            "memory_total_gb": latest.memory_total_gb,
            "memory_used_gb": latest.memory_used_gb,
            "memory_percent": latest.memory_percent,
            "disk_percent": latest.disk_percent,
            "gpu_percent": latest.gpu_percent,
            "temperature": latest.temperature,
            "bandwidth_mbps": latest.bandwidth_mbps,
            "rtt": latest.rtt,
            "jitter": latest.jitter,
            "packet_loss_percent": latest.packet_loss_percent,
            "errors": latest.errors,
            "drops": latest.drops,
            "docker_top": latest.docker_top,
            "proc_top": latest.proc_top
        }
    except Exception as e:
        logger.error(f"Failed to get latest metric: {e}")
        return None
    finally:
        db.close()


def get_latest_triton_metric():
    db = SessionLocal()
    try:
        latest = db.query(TritonMetric).order_by(TritonMetric.id.desc()).first()
        
        if not latest:
            return None
        
        return {
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "gpu_utilization": latest.gpu_utilization,
            "gpu_memory_total_gb": latest.gpu_memory_total_gb,
            "gpu_memory_used_gb": latest.gpu_memory_used_gb,
            "gpu_memory_percent": latest.gpu_memory_percent,
            "gpu_power_usage_watts": latest.gpu_power_usage_watts,
            "gpu_power_limit_watts": latest.gpu_power_limit_watts,
            "cpu_utilization": latest.cpu_utilization,
            "cpu_memory_total_gb": latest.cpu_memory_total_gb,
            "cpu_memory_used_gb": latest.cpu_memory_used_gb,
            "cpu_memory_percent": latest.cpu_memory_percent,
        }
    except Exception as e:
        logger.error(f"Failed to get latest triton metric: {e}")
        return None
    finally:
        db.close()

def get_latest_inference_metric():
    db = SessionLocal()
    try:
        latest = db.query(InferenceMetric).order_by(InferenceMetric.id.desc()).first()
        
        if not latest:
            return None
        
        return {
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "client_id": latest.client_id,
            "mae_px": latest.mae_px,
            "rmse_px": latest.rmse_px,
            "pck": latest.pck,
            "pck_thresh_px": latest.pck_thresh_px,
            "elapsed_sec": latest.elapsed_sec,
            "frames_total": latest.frames_total,
            "frames_pred": latest.frames_pred,
            "gt_format": latest.gt_format,
            "pred_format": latest.pred_format,
        }
    except Exception as e:
        logger.error(f"Failed to get latest inference metric: {e}")
        return None
    finally:
        db.close()
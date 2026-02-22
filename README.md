# ShotAi Monitoring System

이 프로젝트는 **국립공주대학교 소프트웨어중심대학사업**의 일환으로 진행된 **샷에이아이(ShotAi)** 인턴십 프로젝트 결과물입니다.
ShotAi의 SBC와 Triton Inference Server의 시스템 리소스(CPU, GPU, Memory, Network) 및 추론 결과를 실시간으로 수집하고 시각화하여 서비스 운영을 지원하기 위해 개발되었습니다.

**Details**
* **회사명**: 샷에이아이(ShotAi)
* **기간**: 2025.12.17 ~ 2026.01.31 (약 6주)
* **소속**: 국립공주대학교 인턴십 (참여학생: 곽민정)
* **근무 형태**: 재택근무 (대구)

**Overview**
<img width="1902" height="813" alt="image" src="https://github.com/user-attachments/assets/4f3c96d0-277f-48f5-9ecc-625eab03c703" />
<img width="1965" height="845" alt="image" src="https://github.com/user-attachments/assets/0a773d99-9007-4e59-b037-bf81ac2bd840" />


**Quick Start**
```bash
/$ git clone https://github.com/kwakminjung/ShotAi-Dashboard.git
```

## 1. 환경 설정 (Configuration)

프로젝트 루트에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 환경에 맞게 내용을 수정합니다.

```bash
/$ cd ShotAi-Dashboard
/ShotAi-Dashboard$ cp .env.example .env
/ShotAi-Dashboard$ vi .env
```

`.env` 설정 예시 (.txt 파일 전달)
```bash
# Triton Server 설정
TRITON_SERVER=https://tritonserver

# NATS Server 설정
NATS_SERVER=wss://username:password@nats.shotai.us/ws:443

# FastAPI 서버 설정
API_HOST=localhost
API_PORT=8000

# MySQL 설정
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=shotai_monitor
# 주의: DB_NAME은 아래 데이터베이스 생성 단계에서 만든 이름과 일치해야 합니다.
# 주의: DB_USER, DB_PASSWORD는 아래 사용자 생성 단계에서 만든 이름과 일치해야 합니다.

# 로깅 레벨
LOG_LEVEL=INFO
```

## 2. 데이터베이스 설정 (MySQL)

MySQL이 설치되어 있지 않다면 설치를 진행하고, 데이터베이스 및 사용자를 생성합니다.

### 2-1. MySQL 설치 및 서비스 시작
```bash
/ShotAi-Dashboard$ sudo apt install mysql-server
/ShotAi-Dashboard$ sudo ufw allow mysql
/ShotAi-Dashboard$ sudo systemctl start mysql
```

### 2-2. 데이터베이스 및 사용자 생성

MySQL 쉘에 접속하여 다음 명령어들을 순차적으로 실행합니다.

```bash
/ShotAi-Dashboard$ sudo mysql -u root

-- 데이터베이스 생성
mysql> CREATE DATABASE shotai-monitor;

-- 사용자 생성 (<username>과 <password>를 실제 사용할 값으로 변경하세요)
mysql> CREATE USER '<username>'@'localhost' IDENTIFIED BY '<password>';

-- 권한 부여
mysql> GRANT ALL PRIVILEGES ON shotai_monitor.* TO '<username>'@'localhost';

-- 권한 적용 및 종료
mysql> FLUSH PRIVILEGES;
mysql> EXIT;
```

## 4. Docker 실행

Docker ver: 29.0.0

```bash

/ShotAi-Dashboard$ ./run.sh
```

서버가 실행되면 브라우저에서 아래 주소로 접속하여 정상 작동을 확인합니다.
- 접속 주소: http://localhost:8000/

## 5. SBC / Triton 추론 모니터링 실행 (SBC 에서 실행, 2개의 실행창 필요)

### SBC Status Monitor docker 실행

```bash
/$ sudo ./nats-sample/run.sh
```

### Triton AI Inference docker 실행
```bash
/$ sudo ./triton_test/run_ffmpeg_triton_eval.sh
```

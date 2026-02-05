# ShotAI Monitoring System

이 프로젝트는 ShotAI 시스템의 상태를 모니터링하기 위한 대시보드 입니다.

**Quick Start**
```bash
git clone https://github.com/kwakminjung/ShotAi-Dashboard.git
```

## 1. 환경 설정 (Configuration)

프로젝트 루트에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 환경에 맞게 내용을 수정합니다.

```bash
cp .env.example .env
vi .env
```

`.env` 설정 예시
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

# 로깅 레벨
LOG_LEVEL=INFO
```

## 2. 데이터베이스 설정 (MySQL)

MySQL이 설치되어 있지 않다면 설치를 진행하고, 데이터베이스 및 사용자를 생성합니다.

### 2-1. MySQL 설치 및 서비스 시작
```bash
sudo apt install mysql-server
sudo ufw allow mysql
sudo systemctl start mysql
```

### 2-2. 데이터베이스 및 사용자 생성

MySQL 쉘에 접속하여 다음 명령어들을 순차적으로 실행합니다.

```bash
$ sudo mysql -u root

-- 데이터베이스 생성
CREATE DATABASE shotai_monitor;

-- 사용자 생성 (<username>과 <password>를 실제 사용할 값으로 변경하세요)
CREATE USER '<username>'@'localhost' IDENTIFIED BY '<password>';

-- 권한 부여
GRANT ALL PRIVILEGES ON shotai_monitor.* TO '<username>'@'localhost';

-- 권한 적용 및 종료
FLUSH PRIVILEGES;
EXIT;
```

## 3. 가상환경 설정 (Virtual Environment)

Python 가상환경을 생성 및 활성화하고 필요한 라이브러리를 설치합니다.

```bash
# 가상환경 활성화 (Linux/Mac)
source .venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt

# (선택 사항) 작업 완료 후 가상환경 비활성화 시
# deactivate
```

## 4. FastAPI 서버 실행

가상환경이 활성화된 상태(`.venv`)에서 API 서버를 실행합니다.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 브라우저에서 아래 주소로 접속하여 정상 작동을 확인합니다.
- 접속 주소: http://localhost:8000/

## 5. SBC / Triton 추론 모니터링 실행 (SBC 에서 실행)

### SBC Status Monitor docker 실행

**SBC Status Monitor 실행**
```bash
sudo ./nats-sample/run.sh
```

**실행 취소 및 프로세스 종료** 백그라운드에서 실행 중인 run.sh 프로세스를 종료하려면 다음 명령어를 사용합니다.
```bash
sudo pkill -f "run.sh"
```

### Triton AI Inference docker 실행
```bash
sudo ./triton_test/run_ffmpeg_triton_eval.sh
```

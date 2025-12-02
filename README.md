# FFXIV Big Fish Guider

**FFXIV Big Fish Guider**는 파이널 판타지 14의 터주(Big Fish) 정보를 수집하고, 디스코드 봇을 통해 사용자들에게 편리한 조회 및 관리 기능을 제공하는 프로젝트입니다.

## 프로젝트 개요

이 프로젝트는 두 가지 주요 컴포넌트로 구성되어 있습니다:
1. **Data Pipeline (Airflow)**: 외부 웹사이트(Carbuncle Plushy, Teamcraft 등)에서 터주 관련 데이터(획득 정보, 입질 시간 등)를 주기적으로 수집하여 데이터베이스에 저장합니다.
2. **Discord Bot**: 사용자가 디스코드 명령어를 통해 저장된 터주 정보를 조회하거나, 서버 설정을 관리하고, 데이터를 제보할 수 있는 인터페이스를 제공합니다.

## 주요 기능

### Discord Bot
- **/fish [이름]**: 특정 터주의 정보를 조회합니다. (획득 조건, 날씨, 시간 등)
- **/setup**: 디스코드 서버에서 봇이 활동할 채널을 설정하고 초기 구성을 진행합니다.
- **/update**: 사용자가 새로운 정보를 제보하거나 데이터를 업데이트할 수 있는 스레드를 생성합니다.
- **인터랙티브 UI**: 버튼 및 선택 메뉴를 활용한 직관적인 사용자 경험을 제공합니다.

### Data Collection (Airflow)
- **자동화된 데이터 수집**: 주기적으로 실행되는 DAG를 통해 최신 정보를 유지합니다.
- **Selenium 크롤링**: 동적인 웹 페이지(예: Teamcraft)에서도 정확한 데이터를 수집합니다.
- **데이터베이스 동기화**: 수집된 데이터를 PostgreSQL 데이터베이스에 효율적으로 저장 및 갱신합니다.

## 기술 스택

### Backend & Bot
- **Language**: Python
- **Framework**: `discord.py` (Py-cord)
- **Database**: PostgreSQL (DB Interaction layer via `asyncpg` or `psycopg2`)

### Data Engineering
- **Orchestrator**: Apache Airflow
- **Scraping**: Selenium, WebDriver Manager
- **Containerization**: Docker

### Infrastructure
- **Orchestration**: Kubernetes (K8s)
- **Deployment**: Docker containers for Airflow components (Scheduler, Webserver, Worker) and the Discord Bot.

## 프로젝트 구조

```
ffxiv-big-fish-guider/
├── airflow/                # Airflow 관련 설정 및 DAG
│   ├── docker/             # Airflow Docker 이미지 빌드 설정
│   ├── k8s/                # Kubernetes 배포 매니페스트 (Deployments, Services, PVCs)
│   └── pv/dags/            # 데이터 수집 파이프라인 (Python Scripts)
├── discord/                # 디스코드 봇 소스 코드
│   ├── bot/                # 봇 메인 로직 및 커맨드 핸들러
│   ├── config/             # 환경 변수 및 상수 설정
│   ├── core/               # 핵심 유틸리티
│   └── db/                 # 데이터베이스 연동 모듈
└── ...
```

## 설치 및 실행 (Deployment)

이 프로젝트는 Kubernetes 환경에서의 실행을 가정하고 구성되어 있습니다.

### 사전 요구 사항
- Docker
- Kubernetes Cluster (e.g., Minikube, K3s, EKS, GKE)

### 실행 방법

1. **Airflow 배포**:
   `airflow/k8s/` 디렉토리의 매니페스트 파일들을 사용하여 Airflow 컴포넌트를 배포합니다.
   ```bash
   kubectl apply -f airflow/k8s/
   ```

2. **환경 변수 설정**:
   `secret_example.yaml`을 참고하여 필요한 Secret(DB 접속 정보, Discord Token 등)을 생성해야 합니다.

3. **Discord Bot 실행**:
   ```bash
   python discord/bot/main.py
   ```
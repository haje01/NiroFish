<div align="center">


간결하고 범용적인 군집 지능 엔진, 만물을 예측하다
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

</div>

**NiroFish** 는 [MiroFish](https://github.com/666ghj/MiroFish) 를 포크하여 수정하였습니다. 다음과 같은 주요한 수정 사항이 있습니다. 

- 중국어 UI 를 한국어로 번역 
- 시뮬레이션 후 투표 시스템 추가 
- Zep 의존성을 제거하고 Neo4j + Graphiti 로 대체

## ⚡ 프로젝트 개요

**NiroFish**는 다중 에이전트 기술 기반의 차세대 AI 예측 엔진입니다. 현실 세계의 시드 정보(속보 뉴스, 정책 초안, 금융 신호 등)를 추출하여 고충실도의 평행 디지털 세계를 자동으로 구축합니다. 이 공간 안에서 독립적인 개성, 장기 기억, 행동 논리를 갖춘 수천 개의 에이전트가 자유롭게 상호작용하고 사회적으로 진화합니다. "신의 시점"에서 변수를 동적으로 주입하여 미래 방향을 정밀하게 추론할 수 있습니다 — **미래를 디지털 샌드박스에서 미리 연습하고, 수백 번의 시뮬레이션 끝에 의사결정에서 승리하세요**.

> 당신은 다음만 하면 됩니다: 시드 자료(데이터 분석 보고서 또는 흥미로운 소설 이야기)를 업로드하고, 자연어로 예측 요구 사항을 설명하세요</br>
> NiroFish가 반환하는 것: 상세한 예측 보고서와 심층 상호작용이 가능한 고충실도 디지털 세계

### 비전

NiroFish는 현실을 매핑하는 군집 지능 미러를 구축하는 데 전념합니다. 개인 상호작용으로 촉발된 집단 창발을 포착함으로써 전통적 예측의 한계를 돌파합니다:

- **거시적 관점**: 우리는 의사결정자를 위한 리허설 실험실로, 정책과 홍보를 제로 리스크로 테스트할 수 있습니다
- **미시적 관점**: 우리는 개인 사용자를 위한 창의적 샌드박스로, 소설 결말을 추론하거나 상상력을 탐구하는 것 모두 재미있고, 즐겁고, 쉽게 접근 가능합니다

진지한 예측부터 재미있는 시뮬레이션까지, 우리는 모든 "만약에"가 결과를 볼 수 있게 하여 만물을 예측하는 것을 가능하게 합니다.

## 🔄 워크플로우

1. **그래프 구축**: 현실 시드 추출 & 개인 및 집단 기억 주입 & GraphRAG 구축 (Neo4j + Graphiti에 저장)
2. **환경 설정**: 엔티티 관계 추출 & 페르소나 생성 & 환경 설정 에이전트 주입 시뮬레이션 파라미터
3. **시뮬레이션 시작**: 이중 플랫폼 병렬 시뮬레이션 & 예측 요구 사항 자동 파싱 & 동적 시계열 기억 업데이트
4. **보고서 생성**: ReportAgent가 풍부한 도구 세트를 갖추고 시뮬레이션 후 환경과 심층 상호작용
5. **심층 상호작용**: 시뮬레이션 세계의 임의 에이전트와 대화 & ReportAgent와 대화

## 🚀 빠른 시작

### 1. 소스 코드 배포 (권장)

#### 사전 요구 사항

| 도구 | 버전 요구 사항 | 설명 | 설치 확인 |
|------|---------|------|---------|
| **Node.js** | 18+ | 프론트엔드 실행 환경, npm 포함 | `node -v` |
| **Python** | ≥3.11, ≤3.12 | 백엔드 실행 환경 | `python --version` |
| **uv** | 최신 버전 | Python 패키지 관리자 | `uv --version` |

#### 1. 환경 변수 설정

```bash
# 예시 설정 파일 복사
cp .env.example .env

# .env 파일을 편집하여 필요한 API 키 입력
```

**필수 환경 변수:**

```env
# LLM API 설정 (OpenAI SDK 형식을 지원하는 모든 LLM API)
# 알리바바 Bailian 플랫폼의 qwen-plus 모델 권장: https://bailian.console.aliyun.com/
# 소비량이 크므로 먼저 40라운드 미만으로 시뮬레이션을 시도해보세요
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Neo4j 그래프 데이터베이스 설정 (로컬 자체 호스팅)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=nirofish_password
```

> **참고**
> OpenAI 이용 시
> ```
> LLM_BASE_URL=https://api.openai.com/v1
> LLM_MODEL_NAME=gpt-4o-mini
> ```

#### 2. Neo4j 실행

지식 그래프 저장소로 Neo4j를 사용합니다. Docker로 간단히 실행할 수 있습니다:

```bash
# Neo4j만 단독 실행 (소스 코드 배포 시)
docker compose up -d neo4j
```

Neo4j Browser(`http://localhost:7474`)에서 연결을 확인할 수 있습니다.
(초기 로그인: ID `neo4j`, 비밀번호는 `.env`의 `NEO4J_PASSWORD`)

#### 3. 의존성 설치

```bash
# 모든 의존성 원클릭 설치 (루트 디렉터리 + 프론트엔드 + 백엔드)
npm run setup:all
```

또는 단계별 설치:

```bash
# Node 의존성 설치 (루트 디렉터리 + 프론트엔드)
npm run setup

# Python 의존성 설치 (백엔드, 가상 환경 자동 생성)
npm run setup:backend
```

> **주의**
> 설치 시 `pillow` 관련 에러가 나면 `backend/` 디렉토리에서 `uv python pin 3.12` 을 실행하여 파이썬 버전을 3.12 로 지정한 후 다시 `npm run setup:backend` 를 실행한다.

#### 4. 서비스 시작

```bash
# 프론트엔드와 백엔드 동시 시작 (프로젝트 루트 디렉터리에서 실행)
npm run dev
```

**서비스 주소:**
- 프론트엔드: `http://localhost:3000`
- 백엔드 API: `http://localhost:5001`

**개별 시작:**

```bash
npm run backend   # 백엔드만 시작
npm run frontend  # 프론트엔드만 시작
```

### 2. Docker 배포

```bash
# 1. 환경 변수 설정 (소스 코드 배포와 동일)
cp .env.example .env

# 2. Neo4j + NiroFish 전체 스택 시작
docker compose up -d
```

기본적으로 루트 디렉터리의 `.env`를 읽고 포트 `3000(프론트엔드)/5001(백엔드)/7474·7687(Neo4j)`를 매핑합니다.

> `docker-compose.yml`에 주석으로 가속 이미지 주소가 제공되어 있으며 필요에 따라 교체할 수 있습니다


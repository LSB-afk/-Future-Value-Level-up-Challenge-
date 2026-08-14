# MoveValue - 국토교통 서비스 발굴 경연 작업공간

`MoveValue`는 주거비, 이동시간, 대중교통 접근성, 생활 SOC, 안전·환경 지표를 함께 계산해 국민이 체감할 수 있는 생활권 선택을 돕는 국토교통 데이터 기반 서비스 모델입니다.

**라이브 데모**: <https://lsb-afk.github.io/-Future-Value-Level-up-Challenge-/> — 설치 없이 브라우저에서 바로 실행됩니다(Pyodide로 Python API를 브라우저 안에서 구동). 첫 접속 시 엔진 로딩에 10초 정도 걸립니다.

라이브 데모 재배포는 `python3 scripts/build_pages.py`로 `site/`를 빌드한 뒤 `gh-pages` 브랜치에 푸시합니다(자세한 명령은 `scripts/build_pages.py` 도입부 주석 참고).

## 웹 서비스 구성

웹 화면은 단일 지도 워크스페이스입니다. 왼쪽 사이드바에서 예산·목적지·가구 유형·가중치를 입력하고, 오른쪽 Leaflet + OpenStreetMap 지도에서 추천 단지와 주변 아파트 단지를 확인합니다. 추천 카드나 지도 마커를 선택하면 가운데 상세 패널이 열리고 `매칭 결과`, `아파트 정보`, `출퇴근 경로`, `주변 인프라` 탭으로 상세 근거를 확인합니다.

- **조건 입력**: 월 주거 예산, 회사/목적지 주소, 가구 유형, 통근·주거비·생활 SOC·안전 가중치를 조정합니다.
- **추천 랭킹**: 아파트 단지 단위로 통근시간, 월세, 생활 SOC, 안전 신호를 계산해 TOP 후보를 표시합니다.
- **지도 탐색**: Leaflet + OSM 지도에 아파트 가격 라벨, 추천 후보, 클러스터, 선택 단지 생활 SOC 반경을 표시합니다.
- **아파트 상세 대시보드**: 단지 기본정보, 매매가·전세가·월세·공시가격, 거래 추이, 전세 위험 신호, 계약 전 체크리스트, 데이터 연계 상태를 보여줍니다.
- **후보 비교**: 즐겨찾기한 단지의 매칭 점수, 통근시간, 추정 매매가, 전세가율, 위험도, 생활 SOC를 비교합니다.
- **AI Agent**: "이 아파트 전세 들어가도 괜찮아?" 같은 질문에 가격 근거, 통근 근거, 위험 근거, 주변 입지 근거, 확인 필요 서류를 나눠 답변합니다.
- **출퇴근 경로**: 선택 단지와 목적지 사이의 ODsay/TMAP live 경로를 우선 사용하고, 키가 없으면 거리 기반 폴백으로 시간·환승·도보·요금을 표시합니다.
- **제출자료**: `deliverables/`와 `docs/`에 참가신청서 보강본, 스크린샷, Mermaid 다이어그램, 시스템 분석 문서를 저장합니다.

## 현재 산출물

- `api/`: 추천 계산과 정적 웹앱 제공을 담당하는 Python API 서버
- `api/route_adapters.py`: Kakao 주소 검색, ODsay/TMAP 대중교통 경로, 거리 기반 폴백 어댑터
- `api/apartment_adapters.py`: 서울시 공동주택 아파트 정보 API/스냅샷 기반 지도 레이어 어댑터
- `api/real_estate_price_adapters.py`: 국토교통부 매매·전월세 실거래가 live 보정 어댑터. 키 없으면 추정값 유지
- `api/property_model.py`, `api/property_adapters.py`: 부동산 상세 대시보드, 전세 위험 신호, AI Agent 응답 모델
- `app/`: API를 호출하는 브라우저 실행 프로토타입 (Leaflet 지도 포함)
- `data/areas.actual.json`: 서울시 2025 전월세 스냅샷 기반 생활권 데이터
- `data/apartments.seoul.snapshot.json`: 서울시 공동주택 아파트 정보 sample 키 기반 단지 레이어 미리보기 스냅샷
- `scripts/build_real_dataset.py`: 실제 공공데이터 다운로드·정규화 파이프라인
- `scripts/build_apartment_snapshot.py`: 서울 열린데이터광장 `OpenAptInfo` 단지 데이터 스냅샷 생성기
- `scripts/verify_live_integrations.py`: Kakao/ODsay/TMAP/서울 OpenAptInfo/국토부 실거래가 키 기반 live 여부 검증 스크립트
- `scripts/movevalue_adapters.py`: 대중교통 경로 API 폴백 어댑터, 생활 SOC 좌표 집계 어댑터, 안전·환경 스냅샷 점수 어댑터
- `docs/competition-brief.md`: 공모전 공고·양식 확인 요약
- `docs/data-sources.md`: 실제 연계 가능한 공공데이터 근거
- `docs/api-development.md`: API 구조, 실행 방법, 지도 제공자 교체 가이드
- `docs/real-estate-dashboard.md`: 부동산 지도 대시보드 설계, 레퍼런스 조사, 데이터 진실성 구분
- `docs/service-model.md`: 사업모델, 밸류체인, 구현계획
- `docs/product-roadmap.md`: 선정 후 구체화 단계 개발 순서
- `docs/worklog.md`: 작업 일지, 다음 작업 우선순위, 이어서 작업용 프롬프트
- `docs/verification.md`: 실행·브라우저·데이터 검증 로그
- `docs/application-draft.md`: 참가신청서 및 기획서 작성 초안
- `docs/github-latest-analysis.md`: 최신 GitHub 커밋 기준 구현 현황과 미완성 항목 분석
- `docs/system-flow-summary.md`: 사용자 입력, 지도 추천, 상세 대시보드, 위험 점검, AI Agent 흐름 요약
- `docs/mermaid-diagrams.md`: 참가신청서 삽입용 Mermaid 다이어그램 9종
- `docs/submission-screenshots.md`: 제출용 스크린샷 10종 설명 문구
- `docs/submission-checklist.md`: 제출 전 수정 필요 체크리스트
- `architecture/`: 시스템 아키텍처, 데이터 흐름, 사용자 플로우, API 시퀀스, 배포·보안 다이어그램
- `deliverables/`: 제출용 문서 산출물 저장 위치

## API 웹 서비스 실행

별도 패키지 설치 없이 Python 표준 라이브러리만 사용합니다.

```bash
python3 api/movevalue_api.py --port 5173
```

그 다음 브라우저에서 `http://127.0.0.1:5173/`를 엽니다.

## AI Agent (Claude API / 로컬 Ollama 연동)

AI Agent는 세 가지 엔진으로 동작하며, 실행 환경에 따라 자동으로 선택됩니다.
우선순위는 Claude → Ollama → 규칙 기반이고, 설정 스위치는 없습니다.

| 엔진 | 동작 조건 | 특징 |
|---|---|---|
| **Claude API** (`claude-haiku-4-5`) | `anthropic` 설치 + `ANTHROPIC_API_KEY` 설정 | 자유로운 질문에 답변. 공공 도메인 한정 웹 검색으로 제도·법령까지 확인합니다. 토큰 과금이 있습니다. |
| **로컬 Ollama** (`gemma4:latest`) | 키가 없고 `ollama serve`가 떠 있을 때 | 과금 없음. 같은 도구 6개를 쓰지만 웹 검색이 없고, 응답에 20~40초 걸립니다. |
| **규칙 기반** (기본) | 위 둘 다 안 될 때 | 정해진 6개 질문 갈래에만 답변. 아무 설정 없이도 데모가 동작합니다. |

Claude로 쓰려면:

```bash
pip install anthropic
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
python3 api/movevalue_api.py --port 5173
```

Ollama로 쓰려면 (키 불필요, 무료):

```bash
ollama pull gemma4                       # 또는 OLLAMA_MODEL로 다른 모델 지정
python3 api/movevalue_api.py --port 5173
```

`GET /api/agent-status`로 현재 엔진을 확인할 수 있고, 대화 패널 상단에도 표시됩니다.
어느 엔진이 죽어도 다음 순위로 자동 전환되어 대화가 끊기지 않습니다.

열어준 도구는 6개입니다 — 단지 조회, 가격·위험 신호, 전세사기 안전장치,
계약 체크리스트, 더 안전한 대안, 통근 경로. 모두 이 저장소의 데이터를 읽으며,
등기부 권리관계처럼 데이터에 없는 항목은 모른다고 답하도록 시스템 프롬프트에 명시했습니다.

### 로컬 모델 검증 (`api/eval_agent_ollama.py`)

8B급 모델은 도구가 돌려준 숫자를 옮겨 적다가 틀립니다. 루프가 완벽해도 그렇습니다.
그래서 "모델이 사실을 지어내지 않는가"를 재는 평가 하네스를 따로 뒀습니다.
답변 속 모든 수치를 도구 출력·시스템 프롬프트와 대조하고, 판정 반전 표현과
도구 미호출을 함께 잡습니다.

```bash
python3 api/eval_agent_ollama.py                              # 기본 모델
OLLAMA_MODEL=llama3.1:8b python3 api/eval_agent_ollama.py     # 바꾸기 전 비교
```

실측 결과 — **모델을 바꾸려면 반드시 먼저 돌려보세요.**

| 모델 | 결과 | 잡힌 결함 |
|---|---|---|
| `gemma4:latest` | **6/6** | 없음 (기본값) |
| `qwen2.5:7b-instruct` | 4/6 | 전세가율 62.7%를 59.0%로 지어냄, 도구 미호출 |
| `llama3.1:8b` | 4/6 | "62.7%로 80%를 넘으므로 깡통주택"으로 판정 반전, 제도 답변 조작 |

`llama3.1:8b`가 제일 빠르지만(5~11초) 위험 판정을 뒤집습니다. 속도로 상쇄되지 않습니다.

> 정적 배포(GitHub Pages)는 서버가 없어 API 키도 Ollama도 쓸 수 없으므로 항상 규칙 기반으로 동작합니다.
> 라이브 데모에서 LLM 연동을 보려면 위 명령으로 로컬 실행하세요.

## 지도

지도는 API 키가 필요 없는 Leaflet + OpenStreetMap 타일을 사용합니다. 서울 아파트 단지 레이어는 `GET /api/apartments`가 반환하는 좌표와 가격 미리보기를 지도 위에 표시하며, `SEOUL_OPEN_API_KEY`가 있으면 서울 열린데이터광장 `OpenAptInfo` 전체 단지를 런타임으로 불러옵니다. 키가 없으면 저장소의 제한 스냅샷으로 폴백합니다. 지도 사이드바에서 단지 라벨 기준을 매매가·전세가율·위험도·통근시간으로 바꿀 수 있고, 선택 단지는 생활 SOC 반경 1.6km 원으로 표시합니다. 단지 클릭 상세 대시보드는 `GET /api/property-detail`과 `GET /api/property-agent`를 사용합니다. VWorld·카카오·네이버 지도로 교체하는 방법은 `docs/api-development.md`의 "지도 제공자 교체" 절을 참고하세요. 타일 로딩에 실패하면 좌표 기반 분포도 폴백이 유지됩니다.

## 실제 데이터 갱신

서울시 열린데이터광장 전월세 파일을 내려받아 생활권별 월세·보증금·전세 중앙값을 다시 계산합니다. 원천 ZIP은 `data/raw/`에 저장되며 Git에는 포함하지 않습니다.

```bash
python3 scripts/build_real_dataset.py
```

통근시간은 `ODSAY_API_KEY` 또는 `MOVEVALUE_ODSAY_API_KEY`가 있으면 대중교통 경로 API를 호출하고, 키가 없거나 실패하면 기존 검증 테이블로 폴백합니다. 생활 SOC는 병의원·학교·공원 좌표 스냅샷을 생활권 대표역 기준 반경 1.6km로 집계하고, 안전·환경은 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성을 결합합니다. 각 생활권에는 개인정보성 상세주소를 제외한 전월세 실거래 예시 4건도 포함됩니다.

실제 주소 검색과 통근 루트 검증은 서버 환경변수로 API 키를 주입합니다. 기본 생활권·목적지 대표 주소는 API 키 없이 로컬 좌표로 변환되며, 사용자가 입력한 상세 주소는 Kakao 키가 있을 때 검색합니다. 키를 코드에 직접 쓰지 않습니다.

```bash
export KAKAO_REST_API_KEY="카카오 REST API 키"
export ODSAY_API_KEY="ODsay API 키"
export TMAP_APP_KEY="TMAP 대중교통 appKey"
export TMAP_GENERAL_APP_KEY="TMAP 일반 appKey"
export SEOUL_OPEN_API_KEY="서울 열린데이터광장 인증키"
export MOLIT_SERVICE_KEY="공공데이터포털 일반 인증키"
python3 api/movevalue_api.py --port 5173
```

필요한 키 목록은 `.env.example`에 정리되어 있습니다. 실제 키는 `.env`에만 넣고 Git에 커밋하지 않습니다.

키 주입 후 live 연동 상태만 먼저 확인하려면 아래 스크립트를 사용합니다. 출력에는 키 값이 나오지 않고, `mode=live_api` 또는 폴백 상태만 표시됩니다.

```bash
KAKAO_REST_API_KEY=... ODSAY_API_KEY=... TMAP_APP_KEY=... TMAP_GENERAL_APP_KEY=... SEOUL_OPEN_API_KEY=... MOLIT_SERVICE_KEY=... \
  python3 scripts/verify_live_integrations.py
```

## 주요 API

- `GET /api/health`: 데이터 로딩 상태 확인
- `GET /api/areas`: 실제 기반 생활권 데이터 전체 조회
- `GET /api/recommendations`: 예산, 목적지, 가구 유형, 가중치 기반 추천 랭킹 조회
- `GET /api/geocode`: 주소·후보지명·좌표 입력을 좌표 객체로 변환
- `GET /api/commute-route`: 집 주소와 회사 주소를 받아 ODsay/TMAP 경로 또는 폴백 통근 루트 반환
- `GET /api/apartments`: 서울시 공동주택 아파트 정보 기반 단지·클러스터 지도 레이어 반환
- `GET /api/property-detail`: 선택 단지의 기본 정보, 가격, 거래 추이, 전세 위험 신호, 생활권 정보, AI 요약 반환
- `GET /api/property-agent`: 선택 단지에 대한 전세 안전성·추천 이유·대안 탐색 질문에 데이터 근거 기반 답변 반환

## 데이터 기반과 한계

주거비(월세·보증금·전세 중앙값)는 서울시 2025 전월세 실데이터에서 집계한 값입니다. 생활 SOC는 병의원·학교·공원 좌표 스냅샷 반경 집계 기반이고, 안전·환경은 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성 스냅샷 기반입니다. 통근시간은 경로 API 어댑터가 있으나 키 미설정 환경에서는 테이블 폴백으로 생성됩니다. 아파트 지도 레이어는 서울시 공동주택 단지 좌표 기반이며, 현재 커밋된 스냅샷은 sample 키 제한 때문에 5건 미리보기만 포함합니다. `SEOUL_OPEN_API_KEY`를 설정하면 공식 API의 전체 단지 데이터를 같은 엔드포인트로 불러옵니다. 단지 상세 대시보드의 매매·전월세 가격은 `MOLIT_SERVICE_KEY` 등 공공데이터포털 키가 있으면 국토교통부 실거래가 live 보정을 시도하고, 키가 없거나 단지명 매칭이 없으면 생활권 전월세 집계 기반 추정값으로 표시합니다. 공시가격은 PNU/공시가격 식별자 매핑 전 단계이므로 아직 추정값입니다. 화면의 `가격 API 연계 상태`와 `데이터 연계 상태`에서 실데이터/live/추정/연계 예정 여부를 구분합니다. 선정 후 구체화 단계에서는 ODsay/TMAP live 운영 검증, 공시가격·건축물대장 매핑, 원천 API 자동 갱신, 전체 행정동 커버리지로 고도화합니다(`docs/product-roadmap.md` 참고).

## 제출 전 확인 필요

신청서에는 개인정보, 전화번호, 서명, 개인정보 수집·이용 동의가 포함됩니다. 이 항목은 사용자가 직접 확인하고 서명해야 하므로 초안에서는 `제출 전 기재`로 표시했습니다.

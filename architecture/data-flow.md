# Data Flow

MoveValue의 데이터 흐름은 `오프라인 데이터 구축`과 `런타임 API 조회`로 나뉜다. 대용량 원천 파일과 API 키는 저장소에 남기지 않고, 정규화된 프로토타입 데이터만 커밋한다.

## Data Source Map

```mermaid
flowchart LR
    SeoulRent["서울시 부동산 전월세가 정보<br/>2025 실거래"]
    SeoulApt["서울시 공동주택 아파트 정보<br/>OpenAptInfo"]
    Soc["병의원·학교·공원 좌표<br/>서울 열린데이터광장"]
    Safety["치안시설·CCTV·대기측정망<br/>공공데이터 스냅샷"]
    RouteApi["ODsay / TMAP<br/>대중교통 경로"]
    Kakao["Kakao Local<br/>주소 검색"]
    Molit["국토교통부 실거래가<br/>매매·전월세 live 보정"]
    PublicPrice["공동주택 공시가격<br/>PNU 매핑 후 연계"]
    FutureVworld["VWorld / 건축물대장<br/>연계 예정"]

    SeoulRent --> Areas["data/areas.actual.json"]
    Soc --> Areas
    Safety --> Areas
    SeoulApt --> AptSnapshot["data/apartments.seoul.snapshot.json"]
    RouteApi -. "키 있을 때 live" .-> RuntimeRoute["/api/commute-route"]
    Kakao -. "키 있을 때 live" .-> RuntimeRoute
    Molit -. "키 있을 때 live" .-> PriceAdapter["real_estate_price_adapters.py"]
    PriceAdapter --> PropertyDetail["/api/property-detail"]
    PublicPrice -. "식별자 매핑 후" .-> PropertyDetail
    FutureVworld -. "후속 단계" .-> PropertyDetail
```

## Offline Build Flow

```mermaid
flowchart TB
    Start["python3 scripts/build_real_dataset.py"]
    Download["서울시 전월세 ZIP 다운로드<br/>data/raw/ 저장"]
    Normalize["면적 15~85㎡ 필터링<br/>법정동·생활권 매핑"]
    Aggregate["월세·보증금·전세 중앙값<br/>매칭 거래 수 집계"]
    RentExamples["개인정보성 위치 제외<br/>전월세 예시 4건 추출"]
    Commute["ODsay 키 있으면 경로 API<br/>없으면 테이블 폴백"]
    SocCount["병원·학교·공원<br/>반경 1.6km 집계"]
    SafetyCount["치안시설·CCTV·대기·공원<br/>반경 1.8km 집계"]
    Output["data/areas.actual.json"]

    Start --> Download --> Normalize --> Aggregate --> RentExamples
    RentExamples --> Commute --> SocCount --> SafetyCount --> Output
```

## Apartment Layer Flow

```mermaid
sequenceDiagram
    participant Builder as build_apartment_snapshot.py
    participant Seoul as Seoul OpenAptInfo API
    participant Snapshot as apartments.seoul.snapshot.json
    participant API as /api/apartments
    participant Map as Leaflet Map

    Builder->>Seoul: SEOUL_OPEN_API_KEY로 단지 목록 요청
    alt 실제 키 있음
        Seoul-->>Builder: 전체 단지 데이터
        Builder->>Snapshot: 좌표 있는 단지 정규화 저장
    else sample 또는 키 없음
        Seoul-->>Builder: 제한 미리보기 또는 실패
        Builder->>Snapshot: 제한 스냅샷 저장
    end
    Map->>API: bounds, zoom, cluster 쿼리
    API->>Snapshot: 키 없으면 스냅샷 읽기
    API-->>Map: apartment 또는 cluster feature 반환
```

## Runtime Recommendation Flow

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Web as app/app.js
    participant API as movevalue_api.py
    participant Areas as areas.actual.json

    User->>Web: 예산, 목적지, 가구 유형, 가중치 입력
    Web->>API: GET /api/recommendations
    API->>Areas: 생활권 9개 로드
    API->>API: 통근·비용·SOC·안전환경 점수 계산
    API-->>Web: ranking + reasonText + evidence 반환
    Web-->>User: 추천 카드, 지도 마커, 상세 근거 표시
```

## Runtime Property Detail Flow

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Map as 지도 화면
    participant AptApi as /api/apartments
    participant DetailApi as /api/property-detail
    participant Price as real_estate_price_adapters.py
    participant AgentApi as /api/property-agent
    participant Model as property_model.py
    participant MOLIT as MOLIT Transaction APIs

    User->>Map: 단지 마커 또는 단지 리스트 클릭
    Map->>DetailApi: id 기반 상세 요청
    DetailApi->>Model: 단지 기본정보 + 생활권 집계 결합
    Model->>Price: 국토부 실거래가 live 보정 시도
    alt 키와 단지명 매칭 있음
        Price->>MOLIT: 법정동 코드 + 계약년월 조회
        MOLIT-->>Price: 매매/전월세 실거래가 XML
        Price-->>Model: live 가격 + liveStatus
    else 키 없음 또는 매칭 없음
        Price-->>Model: 추정값 유지 + 폴백 사유
    end
    Model-->>DetailApi: 가격, 추이, 위험 신호, AI 요약
    DetailApi-->>Map: 상세 대시보드 JSON
    User->>Map: "전세 들어가도 괜찮아?" 질문
    Map->>AgentApi: id + question
    AgentApi->>Model: 규칙 기반 근거 응답 생성
    AgentApi-->>Map: answer + basis + suggestedComparisons
```

## Data Truth Matrix

| 데이터 | 현재 상태 | 화면 표기 |
| --- | --- | --- |
| 생활권 월세·보증금·전세 중앙값 | 서울시 2025 전월세 실데이터 집계 | 실데이터 |
| 전월세 예시 | 서울시 2025 전월세 공개파일에서 상세 위치 제거 후 추출 | 실거래 예시 |
| 생활 SOC | 병의원·학교·공원 좌표 스냅샷 반경 집계 | 공공데이터 기반 |
| 안전·환경 | 치안시설·CCTV·대기측정망·공원 접근성 스냅샷 | 공공데이터 기반 |
| 통근시간 추천 점수 | ODsay 어댑터 우선, 키 없으면 테이블 폴백 | live 또는 폴백 |
| 사용자 통근 루트 | Kakao/ODsay/TMAP 키 있으면 live, 없으면 거리 추정 | live 또는 추정 |
| 아파트 단지 기본정보 | OpenAptInfo live 또는 스냅샷 | 실데이터/제한 스냅샷 |
| 매매·전월세 단지 가격 | 국토교통부 키 있으면 live 보정, 없거나 단지명 매칭 실패 시 생활권 기반 추정 | live 또는 추정 |
| 공시가격·거래 추이 | 공시가격 PNU 매핑 전 생활권 집계 기반 추정 | 추정/연계 예정 |
| 등기부 권리관계 | 자동 수집하지 않음 | 사용자 확인 필요 |

## Live Verification Flow

```mermaid
flowchart LR
    Env["환경변수<br/>Kakao·ODsay·TMAP·Seoul·MOLIT"]
    Script["scripts/verify_live_integrations.py"]
    Route["통근 루트 live/폴백 확인"]
    Apt["OpenAptInfo 전체/스냅샷 확인"]
    Price["매매·전월세 live/추정 확인"]
    Report["키 값 없는 JSON 리포트"]

    Env --> Script
    Script --> Route
    Script --> Apt
    Script --> Price
    Route --> Report
    Apt --> Report
    Price --> Report
```

## Privacy and Storage Boundary

```mermaid
flowchart LR
    Raw["data/raw/<br/>원천 ZIP·대용량 파일"] -->|"Git 제외"| LocalOnly["로컬 보관"]
    Raw --> Builder["정규화 스크립트"]
    Builder --> PublicJson["data/*.json<br/>집계·비식별 데이터"]
    PublicJson --> Git["GitHub 커밋 가능"]
    Secrets["API Keys<br/>환경변수"] -. "코드 저장 금지" .-> Runtime["런타임 어댑터"]
```

`data/raw/`는 `.gitignore`에 등록된 원천 데이터 영역이다. 사용자·신청자 개인정보, API 키, 상세 지번·건물명 등 민감하거나 재배포 위험이 있는 값은 커밋 대상이 아니다.

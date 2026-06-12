# System Architecture

MoveValue는 현재 외부 패키지 없는 Python 표준 라이브러리 API 서버와 브라우저 SPA로 구성된 프로토타입이다. 핵심 계산은 서버에 두고, 웹은 지도·대시보드·입력 UX를 담당한다.

## System Context

```mermaid
flowchart TB
    User["사용자<br/>청년·신혼부부·직장인·정책 담당자"]
    Service["MoveValue<br/>주거-이동 통합 생활권 추천 서비스"]
    OpenData["공공데이터<br/>서울시 전월세·공동주택·SOC·안전환경"]
    RouteApis["외부 경로/주소 API<br/>Kakao Local · ODsay · TMAP"]
    GovBiz["B2G/B2B 활용처<br/>정책 리포트 · 데이터 API · 주거 상담"]

    User -->|"조건 입력, 지도 선택, 질문"| Service
    Service -->|"추천 생활권, 통근 루트, 단지 위험 신호"| User
    OpenData -->|"정규화·집계"| Service
    Service -. "키 있을 때 live 호출" .-> RouteApis
    Service -->|"API/리포트 확장"| GovBiz
```

## Container Diagram

```mermaid
flowchart LR
    subgraph Client["Client"]
        Web["Web SPA<br/>app/index.html<br/>app/app.js<br/>app/styles.css"]
        Leaflet["Leaflet + OSM Tile<br/>지도 렌더링"]
    end

    subgraph Server["Local API Server"]
        Router["movevalue_api.py<br/>HTTP Router"]
        Recommend["Recommendation Engine<br/>예산·통근·SOC·안전환경 점수"]
        Route["Route Adapters<br/>Kakao / ODsay / TMAP / Fallback"]
        Apt["Apartment Layer Adapter<br/>OpenAptInfo / Snapshot"]
        Price["Real Estate Price Adapter<br/>MOLIT live / Fallback"]
        Property["Property Model<br/>가격·위험 신호·AI Agent"]
    end

    subgraph Data["Local Data"]
        Areas["areas.actual.json<br/>생활권 9개 + 전월세 집계"]
        AptSnapshot["apartments.seoul.snapshot.json<br/>단지 레이어 폴백"]
    end

    subgraph Build["Offline Build Scripts"]
        RentBuilder["build_real_dataset.py"]
        AdapterBuilder["movevalue_adapters.py"]
        AptBuilder["build_apartment_snapshot.py"]
    end

    Web --> Router
    Web --> Leaflet
    Router --> Recommend
    Router --> Route
    Router --> Apt
    Router --> Price
    Router --> Property
    Recommend --> Areas
    Apt --> AptSnapshot
    Property --> Areas
    Property --> AptSnapshot
    Property --> Price
    RentBuilder --> Areas
    AdapterBuilder --> Areas
    AptBuilder --> AptSnapshot
```

## Component Diagram

```mermaid
flowchart TB
    Router["api/movevalue_api.py"]

    Router --> Health["/api/health<br/>데이터·키 상태"]
    Router --> AreasApi["/api/areas<br/>생활권 원천 조회"]
    Router --> RecApi["/api/recommendations<br/>랭킹 계산"]
    Router --> GeoApi["/api/geocode<br/>주소·좌표 변환"]
    Router --> CommuteApi["/api/commute-route<br/>통근 경로 검증"]
    Router --> AptApi["/api/apartments<br/>단지·클러스터 레이어"]
    Router --> DetailApi["/api/property-detail<br/>부동산 상세 대시보드"]
    Router --> AgentApi["/api/property-agent<br/>데이터 기반 질의응답"]

    RecApi --> Score["score_neighborhood()<br/>통근·비용·SOC·안전 가중합"]
    GeoApi --> RouteAdapters["route_adapters.py<br/>known location + Kakao"]
    CommuteApi --> RouteAdapters
    AptApi --> ApartmentAdapters["apartment_adapters.py<br/>bounds filtering + clustering"]
    DetailApi --> PropertyAdapters["property_adapters.py"]
    AgentApi --> PropertyAdapters
    PropertyAdapters --> PropertyModel["property_model.py<br/>price/risk/trend/AI rules"]
    PropertyModel --> PriceAdapters["real_estate_price_adapters.py<br/>MOLIT trade/rent live status"]
```

## 화면 구조

```mermaid
flowchart LR
    Nav["상단 메뉴"]
    RecommendView["추천<br/>생활권 랭킹"]
    RouteView["통근검증<br/>집-회사 루트"]
    MapView["지도<br/>풀스크린 부동산 대시보드"]
    DataView["데이터 근거"]
    ApiView["API"]
    BizView["사업모델"]
    SubmitView["제출자료"]

    Nav --> RecommendView
    Nav --> RouteView
    Nav --> MapView
    Nav --> DataView
    Nav --> ApiView
    Nav --> BizView
    Nav --> SubmitView
```

`#map` 화면은 `body.is-map-view` 상태에서 전역 헤더·내비게이션·푸터를 숨기고, 왼쪽 사이드바와 오른쪽 전체 지도 캔버스를 보여준다. 이는 부동산 지도 서비스처럼 지도 탐색을 첫 화면 경험으로 만들기 위한 구조다.

## 책임 분리

| 계층 | 책임 | 주요 파일 |
| --- | --- | --- |
| Web UI | 입력 상태, 탭 전환, 지도 마커, 상세 패널, 반응형 렌더링 | `app/app.js`, `app/styles.css` |
| API Router | 정적 파일 서빙, 엔드포인트 라우팅, JSON 응답 | `api/movevalue_api.py` |
| Recommendation | 생활권 점수, 추천 사유 문장, 가중치 계산 | `api/movevalue_api.py` |
| Route/Geocode | 주소 좌표화, 대중교통 live API, 거리 기반 폴백 | `api/route_adapters.py` |
| Apartment Layer | 단지 API 호출, 스냅샷 폴백, 클러스터링, 가격 미리보기 | `api/apartment_adapters.py` |
| Price Live Adapter | 국토교통부 매매·전월세 실거래가 조회, 단지명 매칭, live/폴백 상태 | `api/real_estate_price_adapters.py` |
| Property Detail | 가격 추정/live 보정, 거래 추이, 전세 위험 신호, 계약 체크리스트, AI Agent 규칙 | `api/property_model.py`, `api/property_adapters.py` |
| Data Build | 전월세 집계, SOC·안전환경 집계, 단지 스냅샷 생성 | `scripts/` |
| Verification | 키 기반 live API와 폴백 상태 검증 | `scripts/verify_live_integrations.py` |

## 확장 목표 구조

```mermaid
flowchart TB
    Web["Web Dashboard"] --> Gateway["API Gateway"]
    IOS["SwiftUI iOS App"] --> Gateway
    Gateway --> AppApi["MoveValue Application API"]
    AppApi --> Postgis["PostgreSQL / PostGIS"]
    AppApi --> Cache["Route / Tile / Query Cache"]
    AppApi --> Queue["Batch Job Queue"]
    Queue --> DataLake["Public Data Staging"]
    DataLake --> Postgis
    AppApi --> LLM["AI Summary Layer<br/>근거 기반 응답"]
    AppApi --> External["Kakao / ODsay / TMAP / VWorld / MOLIT"]
```

현재 저장소는 위 확장 구조로 옮기기 전에 API 계약과 화면 UX를 검증하는 실작동 프로토타입이다.

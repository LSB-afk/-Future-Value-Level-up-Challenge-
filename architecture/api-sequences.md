# API Sequences

이 문서는 프론트엔드와 API 서버가 어떤 순서로 통신하는지 정리한다. 모든 API는 현재 `python3 api/movevalue_api.py --port 5173` 서버에서 제공된다.

## Initial Page Load

```mermaid
sequenceDiagram
    participant Browser as Browser
    participant Server as movevalue_api.py
    participant Areas as areas.actual.json

    Browser->>Server: GET /
    Server-->>Browser: app/index.html
    Browser->>Server: GET /app.js, /styles.css
    Server-->>Browser: no-store 정적 파일
    Browser->>Server: GET /api/areas
    Server->>Areas: 생활권 데이터 로드
    Server-->>Browser: areas + meta + integrations
    Browser->>Server: GET /api/recommendations?limit=9
    Server-->>Browser: 추천 랭킹
```

## Recommendation Request

```mermaid
sequenceDiagram
    participant UI as Recommendation UI
    participant API as /api/recommendations
    participant Engine as Score Engine
    participant Data as areas.actual.json

    UI->>API: budget, destination, persona, weights
    API->>Data: 생활권 후보 전체 로드
    API->>Engine: 후보별 점수 계산
    Engine->>Engine: 통근 점수 + 비용 점수 + SOC 점수 + 안전환경 점수
    Engine->>Engine: reasonText 생성
    API-->>UI: results, meta, reasonText, evidence
```

## Commute Route With Fallback

```mermaid
sequenceDiagram
    participant UI as Commute UI
    participant API as /api/commute-route
    participant Geo as resolve_location()
    participant ODsay as ODsay API
    participant TMAP as TMAP API
    participant Fallback as fallback_route()

    UI->>API: origin, destinationQuery, provider=auto
    API->>Geo: 출발지·도착지 좌표화
    alt Kakao 키 있음
        Geo->>Geo: Kakao Local 주소 검색
    else 키 없음 또는 대표 주소
        Geo->>Geo: 로컬 후보지/목적지/좌표 매칭
    end
    API->>ODsay: ODSAY_API_KEY 있으면 경로 요청
    alt ODsay 성공
        ODsay-->>API: live route
    else ODsay 실패 또는 키 없음
        API->>TMAP: TMAP_APP_KEY 있으면 경로 요청
        alt TMAP 성공
            TMAP-->>API: live route
        else TMAP 실패 또는 키 없음
            API->>Fallback: 거리 기반 추정 경로
            Fallback-->>API: estimated route + notice
        end
    end
    API-->>UI: provider, mode, summary, steps, coordinates, errors
```

## Apartment Map Layer

```mermaid
sequenceDiagram
    participant Map as Leaflet Map
    participant API as /api/apartments
    participant Adapter as apartment_adapters.py
    participant Seoul as Seoul OpenAptInfo API
    participant Snapshot as apartments.seoul.snapshot.json

    Map->>API: bounds, zoom, cluster
    API->>Adapter: apartments_response()
    alt SEOUL_OPEN_API_KEY 있음
        Adapter->>Seoul: live API 호출
        Seoul-->>Adapter: 전체 단지 데이터
    else 키 없음 또는 호출 실패
        Adapter->>Snapshot: 제한 스냅샷 로드
        Snapshot-->>Adapter: 단지 5건 미리보기
    end
    Adapter->>Adapter: bounds 필터링
    Adapter->>Adapter: zoom 기준 클러스터링
    Adapter->>Adapter: pricePreview 생성
    API-->>Map: features + meta
```

## Property Detail Dashboard

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Map as Map UI
    participant API as /api/property-detail
    participant Adapter as property_adapters.py
    participant Model as property_model.py
    participant Areas as areas.actual.json
    participant Apt as apartment dataset

    User->>Map: 단지 클릭
    Map->>API: GET /api/property-detail?id=...
    API->>Adapter: property_detail_response()
    Adapter->>Apt: 단지 id 검색
    Adapter->>Model: build_property_detail(apartment)
    Model->>Areas: 생활권 전월세·SOC·안전환경 참조
    Model->>Model: 가격, 거래 추이, 전세 위험 신호, AI 요약 생성
    API-->>Map: detail + dataStatus + source meta
    Map-->>User: 오른쪽 상세 드로어 렌더링
```

## Property Agent

```mermaid
sequenceDiagram
    participant User as 사용자
    participant UI as Property Drawer
    participant API as /api/property-agent
    participant Adapter as property_adapters.py
    participant Model as property_model.py

    User->>UI: 질문 입력
    UI->>API: id + question
    API->>Adapter: property_agent_response()
    Adapter->>Model: build_property_detail()
    Adapter->>Model: comparison_candidates()
    Model->>Model: property_agent_answer()
    Model-->>Adapter: answer, basis, suggestedComparisons, disclaimer
    Adapter-->>API: agent payload
    API-->>UI: 근거 기반 답변
```

## Endpoint Contract Summary

| Endpoint | 입력 | 출력 | 폴백 |
| --- | --- | --- | --- |
| `/api/health` | 없음 | 데이터 로딩 상태, API 키 감지 여부 | 없음 |
| `/api/areas` | 없음 | 생활권 원천 데이터 | `areas.actual.json` 필수 |
| `/api/recommendations` | 예산, 목적지, 가구 유형, 가중치 | 생활권 랭킹과 근거 | 데이터셋 기반 |
| `/api/geocode` | 주소/후보지/좌표 | 좌표 객체 | 로컬 대표 주소, 좌표 파싱 |
| `/api/commute-route` | 집, 회사, provider | 통근 루트 요약과 단계 | 거리 기반 추정 |
| `/api/apartments` | bounds, zoom, cluster | 단지/클러스터 feature | 스냅샷 |
| `/api/property-detail` | id 또는 q | 상세 대시보드 | 단지 스냅샷 + 추정값 |
| `/api/property-agent` | id, question | 답변, 근거, 비교 후보 | 내부 규칙 기반 |

## Error Handling Policy

```mermaid
flowchart TD
    A["API 요청"] --> B{"입력 검증 성공?"}
    B -->|"아니오"| C["400 JSON<br/>ok=false, error"]
    B -->|"예"| D{"외부 API 필요?"}
    D -->|"아니오"| E["로컬 데이터 응답"]
    D -->|"예"| F{"키 있음 + 호출 성공?"}
    F -->|"예"| G["live_api 응답"]
    F -->|"아니오"| H["fallback 응답<br/>notice/errors 포함"]
    E --> I["200 JSON"]
    G --> I
    H --> I
```

외부 API 실패는 사용자 경험을 끊지 않고 `provider`, `mode`, `notice`, `errors`, `dataStatus` 필드로 한계를 공개한다.

# 참가신청서 삽입용 Mermaid 다이어그램

각 다이어그램은 신청서 본문 또는 발표자료에 붙여넣기 쉽도록 핵심 흐름 중심으로 작성했다.

## 1. 전체 시스템 아키텍처 다이어그램

MoveValue가 사용자, 웹 UI, API 서버, 로컬 데이터, 외부 공공 API를 어떻게 연결하는지 보여준다.

```mermaid
flowchart TB
    User["사용자"] --> Web["MoveValue Web UI"]
    Web --> API["Python API Server"]
    API --> Rec["추천 점수 엔진"]
    API --> Property["부동산 상세/위험 모델"]
    API --> Agent["AI Agent 응답 모델"]
    API --> LocalData["로컬 정규화 데이터"]
    API -. "키 있을 때 live" .-> External["Kakao / ODsay / TMAP / MOLIT / Seoul / VWorld"]
    LocalData --> Areas["생활권 전월세/SOC/안전 데이터"]
    LocalData --> Apt["아파트 단지 스냅샷"]
    Web --> Map["Leaflet + OSM 지도"]
```

## 2. 사용자 플로우 다이어그램

사용자가 조건 입력부터 단지 비교와 계약 전 확인까지 이동하는 흐름이다.

```mermaid
flowchart TD
    A["서비스 접속"] --> B["예산·목적지·가구유형 입력"]
    B --> C["가중치 조정"]
    C --> D["매칭하기"]
    D --> E["추천 아파트 랭킹 확인"]
    E --> F["지도에서 단지 선택"]
    F --> G["상세 대시보드 확인"]
    G --> H["전세 위험 신호 점검"]
    G --> I["즐겨찾기 비교"]
    G --> J["AI Agent 질문"]
    H --> K["계약 전 확인 항목 정리"]
```

## 3. 서비스 시퀀스 다이어그램

추천과 상세 대시보드가 어떤 API 호출 순서로 구성되는지 보여준다.

```mermaid
sequenceDiagram
    participant U as 사용자
    participant W as Web UI
    participant A as API Server
    participant D as Local Data
    participant X as External APIs

    U->>W: 조건 입력 후 매칭
    W->>A: GET /api/apartment-recommendations
    A->>D: 생활권/아파트 데이터 조회
    A-->>W: 추천 결과와 근거
    U->>W: 단지 선택
    W->>A: GET /api/property-detail
    A->>D: 단지/생활권 데이터 조회
    A-->>X: 키 있을 때 실거래/경로 조회
    A-->>W: 상세 대시보드 데이터
    U->>W: AI 질문
    W->>A: GET /api/property-agent
    A-->>W: 근거 그룹 답변
```

## 4. 데이터 파이프라인 다이어그램

공공데이터를 수집하고 점수화하는 흐름이다.

```mermaid
flowchart LR
    SeoulRent["서울 전월세 데이터"] --> Clean["정제·비식별"]
    SOC["병원·학교·공원 좌표"] --> Aggregate["반경 집계"]
    Safety["치안·CCTV·대기·공원"] --> Aggregate
    AptInfo["서울 OpenAptInfo"] --> AptLayer["단지 지도 레이어"]
    Clean --> Areas["areas.actual.json"]
    Aggregate --> Areas
    Areas --> Score["생활권/단지 점수화"]
    AptLayer --> Score
    Score --> API["추천·상세 API"]
```

## 5. AI Agent 의사결정 흐름도

AI Agent가 질문을 근거 기반 답변으로 바꾸는 방식이다.

```mermaid
flowchart TD
    Q["사용자 질문"] --> Intent{"질문 의도"}
    Intent -->|"전세 안전성"| Risk["위험 신호와 체크리스트"]
    Intent -->|"추천 이유"| Reason["가격·통근·SOC 근거"]
    Intent -->|"더 안전한 대안"| Compare["비교 후보 탐색"]
    Risk --> Answer["설명형 답변"]
    Reason --> Answer
    Compare --> Answer
    Answer --> Basis["가격 / 통근 / 위험 / 입지 / 확인 서류"]
    Basis --> Disclaimer["법적 판정 아님 고지"]
```

## 6. 지도 기반 부동산 대시보드 기능 흐름도

지도 마커 클릭부터 상세 패널이 열리는 흐름이다.

```mermaid
flowchart TD
    Map["지도 표시"] --> Layer["단지/클러스터 레이어"]
    Layer --> Label["가격·전세가율·위험도·통근 라벨"]
    Label --> Select["단지 선택"]
    Select --> Detail["/api/property-detail"]
    Detail --> Dashboard["상세 대시보드"]
    Dashboard --> Price["가격/거래추이"]
    Dashboard --> Risk["전세 위험 신호"]
    Dashboard --> SOC["생활 SOC 반경"]
    Dashboard --> Agent["AI Agent"]
```

## 7. 전세 위험 신호 점검 프로세스

법적 판정이 아닌 계약 전 주의 요소 안내 프로세스다.

```mermaid
flowchart TD
    P["가격 데이터"] --> R1["전세가율"]
    P --> R2["공시가격 대비 보증금"]
    P --> R3["주변 시세 대비 차이"]
    T["거래 추이"] --> R4["최근 가격 변동성"]
    B["건축연도"] --> R5["건축물 노후도"]
    U["사용자/서류 입력"] --> R6["등기부 권리관계"]
    R1 --> Score["위험 신호 점수"]
    R2 --> Score
    R3 --> Score
    R4 --> Score
    R5 --> Score
    R6 --> Score
    Score --> Guide["계약 전 확인 필요 항목"]
```

## 8. 생활권 점수 산정 구조도

추천 점수가 어떤 항목으로 산정되는지 보여준다.

```mermaid
flowchart LR
    Input["사용자 조건"] --> Weights["가중치"]
    Commute["통근 시간"] --> Weighted["가중합"]
    Cost["예산 대비 주거비"] --> Weighted
    SOC["생활 SOC 접근성"] --> Weighted
    Safety["안전·환경"] --> Weighted
    Weights --> Weighted
    Weighted --> Rank["추천 랭킹"]
    Rank --> Reason["근거 문장"]
```

## 9. 공공데이터/API 연계 구조도

현재 구현된 API와 확장 예정 API를 한 번에 보여준다.

```mermaid
flowchart TB
    subgraph Current["현재 구현/폴백 포함"]
        Rent["서울 전월세 2025"]
        Apt["서울 OpenAptInfo"]
        Route["Kakao / ODsay / TMAP"]
        MOLIT["국토부 매매·전월세 실거래"]
    end
    subgraph Next["확장 예정"]
        PublicPrice["공동주택 공시가격"]
        Building["건축HUB 건축물대장"]
        VWorld["VWorld 지오코딩/용도지역"]
        Transport["전국 도시철도/교통 오픈마켓"]
    end
    Current --> MoveValue["MoveValue API"]
    Next --> MoveValue
    MoveValue --> Web["웹 대시보드"]
    MoveValue --> Report["정책/B2B 리포트"]
```

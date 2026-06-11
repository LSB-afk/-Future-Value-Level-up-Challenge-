# MoveValue API 개발 메모

## 현재 구현

MoveValue는 웹 화면과 추천 계산 API를 같은 Python 서버에서 제공한다. 외부 패키지 없이 실행되므로 공모전 심사·데모 환경에서 재현성이 높다.

```bash
python3 api/movevalue_api.py --port 5173
```

접속 URL은 `http://127.0.0.1:5173/`이다.

## 데이터 파이프라인

`scripts/build_real_dataset.py`는 서울시 열린데이터광장의 `서울시 부동산 전월세가 정보` 2025년 파일을 내려받고, 15~85㎡ 거래를 생활권 법정동 기준으로 집계한다.

```bash
python3 scripts/build_real_dataset.py
```

산출물은 `data/areas.actual.json`이며, 원천 ZIP은 `data/raw/`에 보관한다. `data/raw/`는 용량과 원천 데이터 재배포 이슈를 줄이기 위해 Git에서 제외한다.

## 엔드포인트

### `GET /api/health`

데이터 파일 로딩 상태와 후보 생활권 수를 확인한다.

### `GET /api/areas`

정규화된 생활권 후보 전체를 반환한다. 웹앱은 초기 지도 범위와 데이터 출처 표시를 위해 이 엔드포인트를 먼저 호출한다.

### `GET /api/recommendations`

사용자 조건을 기반으로 생활권 추천 랭킹을 반환한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `budget` | `70` | 월 주거 예산, 만원 단위 |
| `destination` | `gangnam` | 주요 목적지. `gangnam`, `yeouido`, `seoulStation`, `digital`, `pangyo` 지원 |
| `persona` | `single` | 가구 유형. `single`, `commuter`, `newlywed`, `senior` 지원 |
| `commuteWeight` | `35` | 통근 점수 가중치 |
| `costWeight` | `30` | 주거비 점수 가중치 |
| `serviceWeight` | `20` | 생활 SOC 점수 가중치 |
| `safetyWeight` | `15` | 안전·환경 점수 가중치 |
| `limit` | `9` | 반환 개수 (기본 8, 웹앱은 지도 마커 9개를 위해 9 요청) |

예시:

```bash
curl 'http://127.0.0.1:5173/api/recommendations?budget=70&destination=gangnam&persona=single&commuteWeight=35&costWeight=30&serviceWeight=20&safetyWeight=15&limit=9'
```

## 지도 구현과 제공자 교체

웹앱 지도는 API 키가 필요 없는 **Leaflet 1.9.4 + OpenStreetMap 타일**을 사용한다. 구현 위치는 `app/app.js`의 `initializeLeafletMap()`이며, 타일 레이어 한 줄만 바꾸면 다른 제공자로 교체할 수 있다.

- **VWorld**: `L.tileLayer("https://api.vworld.kr/req/wmts/1.0.0/{API_KEY}/Base/{z}/{y}/{x}.png")` — 국토교통부 제공, 발급 키 필요. 공공 서비스 신뢰도 측면에서 1순위 교체 후보.
- **카카오/네이버 지도**: 자체 JS SDK를 사용하므로 Leaflet 마커 로직을 SDK 마커 API로 옮겨야 한다. `renderLeafletMap()`의 마커 데이터(좌표·점수·선택 상태)는 그대로 재사용 가능하다.
- 타일 로딩이 실패하거나 Leaflet 스크립트가 차단된 환경에서는 좌표 비례 분포도 폴백(`renderFallbackMap()`)이 자동으로 동작한다.

API 키가 필요한 제공자는 키를 코드에 하드코딩하지 않고 환경 변수 또는 서버 측 프록시로 주입한다.

## 확장 방향

- 교통: 현재는 주요 업무지구별 실증용 통근시간 테이블을 사용한다. 배포 단계에서는 대중교통 경로 API나 GTFS 기반 라우팅으로 분리한다.
- 주거: 현재는 서울시 2025 전월세 파일 기반이다. 다음 단계에서는 월별 증분 갱신과 국토교통부 실거래가 API를 병행한다.
- 클라이언트: iOS Swift 앱은 `/api/areas`와 `/api/recommendations`를 그대로 소비하는 구조로 확장한다.
- 수익화: 부동산·교통 플랫폼에는 추천 점수 API, 지자체에는 생활권 취약지 리포트 API로 제공한다.

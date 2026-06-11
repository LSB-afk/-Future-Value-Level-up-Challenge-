# Verification Log

확인일: 2026-06-11

## 완료한 확인

- `data/neighborhoods.json` JSON 문법 검사 통과
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 생성 성공
- DOCX 렌더링 성공: `qa/docx-render/page-1.png` ~ `page-4.png`
- 렌더 이미지 육안 확인: 빈 페이지, 표 경계 잔상, 큰 텍스트 겹침 없음
- 로컬 서버 실행: `python3 -m http.server 5173`
- 브라우저 검증 URL: `http://localhost:5173/app/`
- 앱 기본 로딩 확인: 랭킹 카드 8개, 지도 마커 12개 표시
- 기본 조건 상위 추천: 건대입구, 신림, 청량리
- 목적지 변경 테스트: 판교 선택 시 상위 추천이 광교로 재계산됨
- 브라우저 콘솔 오류: 없음

## 확인된 제한

- GitHub CLI(`gh`)가 설치되어 있지 않음
- GitHub SSH 인증 실패: `Permission denied (publickey)`
- 브라우저 GitHub 세션도 로그인되어 있지 않아 원격 저장소 생성은 미완료
- 공공데이터 API는 실제 키 없이 연결하지 않았고, 프로토타입은 샘플 데이터로 동작함
- 전화번호, 서명, 개인정보 동의 체크는 신청자가 제출 전 직접 기재해야 함


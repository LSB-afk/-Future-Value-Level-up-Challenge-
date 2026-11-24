# 리포트 신청자 본인인증

안심 판정 리포트의 **서류 확인 → 신청자 본인확인**에서 사용자가 인증을 준비하고 기관 인증창을 엽니다. 휴대폰에서 인증창으로 이동한 경우 같은 탭의 원래 매물로 돌아옵니다. 핏홈 서버가 포트원에서 해당 인증 건을 조회해 완료 여부를 표시합니다. 이 결과의 대상은 현재 인증을 진행한 신청자입니다. 임대인 소유권, 세금, 증명서 발급은 각 서류의 확인 절차를 따릅니다. [포트원 본인인증 연동](https://developers.portone.io/opi/ko/extra/identity-verification/readme-v2?v=v2)

| 서버 환경변수 | 설정 값 |
| --- | --- |
| `FITHOME_PORTONE_STORE_ID` | 해당 상점의 ID |
| `FITHOME_PORTONE_CHANNEL_KEY` | 본인인증 계약이 연결된 운영 채널 키 |
| `FITHOME_PORTONE_API_SECRET` | 같은 상점에 접근 가능한 V2 API Secret |
| `FITHOME_IDENTITY_GATEWAY_TOKEN` | 외부 공개 시 로그인과 요청 권한을 확인하는 프록시와 공유하는 서버 비밀 |

공개 배포 시 프록시는 사용자가 보낸 `X-FitHome-Identity-Gateway` 헤더를 제거하고, 인증과 권한 확인을 통과한 요청에만 서버 비밀을 헤더로 주입합니다. 직접 루프백 접속은 로컬 점검에 사용할 수 있습니다. 이용 채널에서 HTTPS 서비스 도메인과 본인인증 계약을 등록합니다. KCP 채널은 파트너 관리자에서 V2 연동과 인증 결과 URL 설정도 필요합니다. [KCP 채널 설정](https://developers.portone.io/opi/ko/integration/pg/v2/kcp-v2-identity-verification?v=v2)

인증 건 번호는 핏홈이 생성하며, 별도 임의 토큰을 이 매물과 주소에 연결합니다. 요청은 10분 동안, 인증 완료 결과는 1시간 동안 서버 메모리에서 유효합니다. 서버 재시작 또는 탭 종료 후에는 다시 인증합니다. 완료 여부는 단건 조회의 운영 채널·인증 건 번호·완료 상태·시각을 대조해 결정합니다. 핏홈은 이름·생년월일·전화번호·CI·DI를 저장하지 않습니다. 인증 SDK는 사용자가 동의하고 인증을 준비할 때 불러옵니다. [포트원 V2 API](https://developers.portone.io/api/rest-v2/identityVerification?v=v2) · [브라우저 SDK](https://developers.portone.io/sdk/ko/v2-sdk/readme?v=v2)

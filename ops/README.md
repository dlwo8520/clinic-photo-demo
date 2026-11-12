# 공개 무료 데모 검증

`python ops/verify_public.py --base-url <실제 HTTPS 원점> --upload`는 가상 PNG 3장과 1장을 3주차에 추가합니다. 직원 버튼 접속을 자동 인식하며 비밀번호를 요구하지 않습니다.

- 같은 인스턴스에서 새로고침 후 보존 확인: `--check-restart artifacts/public-verification.json`
- Free 서버가 교체된 뒤 샘플 복원 확인: `--check-reset`
- 증거 JSON은 `artifacts/`에 저장하며 Git에 포함하지 않습니다.
- QR 토큰·비밀번호는 증거 파일에 저장하지 않습니다.
- 실제 PC 자동 갱신과 아이폰 Safari 업로드는 별도 수동 검증이 필요합니다.

Free 서비스는 임시 저장소를 사용하므로 서버 재시작·재배포·절전 후 업로드 사진이 사라집니다. `--check-restart`는 같은 실행 인스턴스의 사진 재조회 용도로만 사용합니다.
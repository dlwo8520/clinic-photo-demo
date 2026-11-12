# HTTPS 배포 수락 확인

`verify_public.py`는 Django에 직접 접근하지 않고 실제 서버의 HTTP 경로를 확인합니다. Python 표준 라이브러리만 사용하며 HTTPS 인증서 검증을 끄지 않습니다. 가상 환자가 있는 데모 서버에서 실행하세요.

기본 로그인 아이디는 `dlwo8520`입니다. 비밀번호는 실행 시 숨김 입력합니다. 자동화 환경에서는 `CLINIC_DEMO_PASSWORD` 환경변수를 사용할 수 있습니다. 비밀번호나 QR의 비밀 토큰은 출력 또는 결과 JSON에 저장하지 않습니다.

```powershell
# 기본 조회·접근 제한 확인 (서버 데이터 변경 없음)
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com

# 명시적으로 대표 환자 DEMO-1001의 3주차에 가상 PNG 3장 + 1장 저장
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com --upload
```

첫 실행은 로그인, 차트번호·이름 일부 검색, 동명이인 구분, 1주차 4장 이상·2주차 5장 이상, 인증된 사진·썸네일 조회, 비로그인 사진·썸네일 차단을 확인합니다. `--upload`를 붙이면 QR 서버 주소와 QR 이미지, 모바일 업로드 폼, 실제 다중 저장, 기존 사진 유지, 추가 1장, 마지막 사진 순서, 같은 요청 재전송의 중복 방지를 확인합니다.

`--upload`는 기존 3주차 사진을 삭제하지 않습니다. 예를 들어 현재 4장이면 4→7→8장이 됩니다. 정확한 0→3→4 시연은 처음 생성한 가상 데이터에서 진행하세요. 동시에 다른 사람이 같은 방문에 올리면 정확한 개수 검증이 실패할 수 있으므로 시연 중인 방문에서 단독으로 실행하세요.

결과는 기본적으로 `artifacts/public-verification.json`에 저장됩니다. 환자·방문·사진 ID, 가상 차트번호, 이미지와 썸네일의 SHA-256, 업로드 전후 개수를 담습니다. 다른 결과 파일은 `--output 경로`로 지정합니다.

서버를 **실제로 재시작하거나 재배포한 뒤** 다음을 실행하세요.

```powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com --check-restart artifacts\public-verification.json --output artifacts\after-restart-verification.json
```

이 명령은 이전 사진 ID가 모두 남아 있고 화면용 이미지와 썸네일의 바이트 해시가 그대로인지 확인합니다. 스크립트 자체가 재시작을 수행하거나 재시작 사실을 증명하지는 않습니다. 재시작 여부는 호스팅 작업 기록과 함께 확인하세요.

로컬 QA만 HTTP 루프백을 허용할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url http://127.0.0.1:8000 --allow-local --upload --output artifacts\local-http-verification.json
```

이 확인은 실제 브라우저의 JavaScript나 아이폰 Safari를 실행하지 않습니다. PC에서 오른쪽 3주차를 열어 둔 상태로 다른 세션에서 업로드하고, 새로고침 없이 사진 수·썸네일·마지막 큰 사진이 바뀌는지 별도로 확인하세요. 아이폰 Safari에서는 QR 스캔, 로그인 후 돌아오기, 카메라 촬영, 보관함 다중 선택, 미리보기·삭제, 일부 실패 재시도를 확인해야 합니다.

# 굿모나 의원 · 공개 HTTPS 확인

verify_public.py는 Python 표준 라이브러리로 실제 HTTP 경로를 확인합니다. TLS 인증서 검증을 유지하며 비밀번호와 QR 토큰은 결과에 저장하지 않습니다. 기본 아이디는 dlwo8520, 비밀번호는 숨김 입력합니다.

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com --upload
~~~

로그인, 이름 일부·차트번호·동명이인 검색, 1주차 4장·2주차 5장, 인증된 사진·썸네일 조회와 익명 접근 차단을 검사합니다. 업로드 옵션은 QR과 모바일 폼, 3장+1장 저장, 기존 사진 유지, UUID 재전송의 중복 방지를 확인합니다.

기존 업로드는 삭제하지 않습니다. 3주차가 0장이면 0→3→4, 이미 4장이면 4→7→8장이 됩니다. 동시에 다른 사람이 같은 방문을 변경하지 않는 상태에서 실행하세요.

## 같은 실행 중 새로고침·재로그인 후 조회

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com --check-refresh artifacts\public-verification.json --output artifacts\after-refresh.json
~~~

앞서 기록한 사진 ID와 이미지·썸네일 SHA-256이 그대로 조회되는지 확인합니다.

## Free 서비스 재시작 후 새 샘플 확인

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url https://실제-서비스.onrender.com --check-reseed --output artifacts\after-restart.json
~~~

운영자가 서비스를 실제로 재시작·재배포한 뒤 실행합니다. 새 계정 로그인과 대표 환자 방문의 정확한 샘플 개수 4장·5장·0장을 확인합니다. Free 임시 저장소의 이전 업로드가 유지된다고 검사하지 않습니다.

## 로컬 QA

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url http://127.0.0.1:8000 --allow-local --upload --output artifacts\local-http.json
~~~

결과는 artifacts의 JSON에 기록됩니다. 이 스크립트는 실제 브라우저를 실행하지 않습니다. PC 화면에서 페이지 새로고침 없이 오른쪽 사진 수·썸네일·마지막 큰 사진이 갱신되는지, 아이폰 Safari에서 QR 스캔·로그인 복귀·카메라·보관함 다중 선택·미리보기·삭제·부분 재시도가 동작하는지는 별도로 확인하세요.

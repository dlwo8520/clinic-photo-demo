# 굿모나 의원 · 진료 사진 면접 데모

Django + SQLite로 환자 검색, 방문별 사진 비교, QR 다중 업로드, PC 자동 갱신을 제공하는 프로토타입입니다. 가상 환자 8명과 코드로 생성한 샘플 이미지만 사용합니다. 녹음·음성 전사·CRM 연동은 포함하지 않습니다.

## 이번 배포 기준

Render Free Web Service 한 개로 실행하며 유료 서비스·영구 디스크·별도 DB 서비스는 만들지 않습니다.

- SQLite, 사진 원본, 화면용 JPEG와 썸네일은 서버의 비공개 임시 폴더에 저장합니다.
- 같은 서버 실행 중에는 업로드가 누적됩니다. 페이지 새로고침과 재로그인 후에도 같은 방문의 사진을 다시 조회합니다.
- 서비스 시작 명령은 매번 새로운 임시 폴더를 선택하고 마이그레이션·데모 생성을 실행합니다. 재시작·재배포 뒤에는 기본 샘플 4장·5장·0장으로 새 시연을 시작합니다.
- 초기화 명령만 다시 실행하면 현재 방문·사진·계정을 유지합니다. 기존 업로드를 지우거나 덮어쓰지 않습니다.
- Gunicorn 작업자 재생성은 현재 임시 경로를 이어 쓰며, 서비스 시작 명령을 다시 실행할 때 새 데모가 준비됩니다.

Render Free는 유휴 상태에서 중지될 수 있으며, 중지·재시작·재배포 때 로컬 파일은 사라집니다. 다시 접속하면 준비 시간이 필요합니다. 면접 전에 공개 주소를 열고 로그인 화면이 나타난 뒤 시연하세요. [Render Free 공식 안내](https://render.com/docs/free)

실제 환자 자료는 사용하지 않습니다. 실제 진료 데이터는 운영 보안·권한·감사 기록·백업·보관 정책을 준비한 환경에서만 사용해야 합니다.

## Windows PowerShell에서 로컬 실행

Python 3.12를 권장합니다. 현재 폴더의 가상환경이 준비돼 있으면 설치 단계는 건너뛸 수 있습니다.

~~~powershell
cd C:\Users\Administrator\Desktop\home_work
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
~~~

새 데모 계정의 비밀번호는 seed_demo 실행 시 숨김 입력합니다. 이미 생성된 계정은 비밀번호를 유지합니다. 아이디는 dlwo8520입니다. 실제 비밀번호와 키는 소스에 넣지 않습니다.

접속 주소: http://127.0.0.1:8000/login/

로컬 실행은 작업 폴더의 SQLite와 private_media를 사용하므로 일반 로컬 서버 재실행으로 자료가 초기화되지 않습니다. 아래의 Free 서비스 시작 방식만 새 임시 폴더를 선택합니다.

## Render Free 배포

소스 저장소: https://github.com/dlwo8520/clinic-photo-demo

[이 저장소로 Render Blueprint 열기](https://dashboard.render.com/blueprint/new?repo=https://github.com/dlwo8520/clinic-photo-demo)

1. Render에 로그인하고 요청하면 GitHub 저장소를 연결합니다.
2. main 브랜치, 루트 render.yaml을 사용합니다.
3. Web Service의 Plan이 Free이고 Disk 항목이 없는지 확인합니다.
4. 로그인 비밀번호 환경변수를 입력합니다. Django 서명 키는 Blueprint가 무작위로 생성합니다.

| 항목 | 값 |
| --- | --- |
| DJANGO_SECRET_KEY | Blueprint에서 자동 생성. 기존 서비스의 키는 유지 |
| CLINIC_DEMO_PASSWORD | 데모 로그인에 사용할 비밀번호 |

서명 키 생성 명령입니다. 출력값은 Render 입력란에만 복사하고 저장소나 대화에 붙이지 마세요.

~~~powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
~~~

5. Deploy Blueprint / Apply를 누릅니다.
6. 상태가 Live가 된 뒤 Render가 표시하는 실제 HTTPS 주소로 접속합니다. 아이디는 dlwo8520, 비밀번호는 환경변수에 지정한 값입니다.

아직 실제 공개 URL과 Render 서비스 상태는 이 작업에서 확인되지 않았습니다. 주소를 추측해서 접속 완료로 간주하지 않습니다.

### 실행 설정

| 설정 | 값 또는 동작 |
| --- | --- |
| 서비스 수 / Plan | Web Service 1개 / free |
| 영구 디스크 / 추가 데이터 서비스 | 없음 |
| Build Command | bash scripts/render-build.sh |
| Start Command | bash scripts/render-start.sh |
| Health Check | /healthz/ |
| DJANGO_DEBUG | 0 |
| CLINIC_EPHEMERAL_DEMO | 1 |
| CLINIC_DATA_DIR | 빌드용 기본 /tmp/goodmona-demo; 서비스 시작 시 /tmp/goodmona-demo.XXXXXX로 새로 지정 |
| CLINIC_MAX_IMAGE_PIXELS | 16000000 (Free 메모리 한도에 맞춘 16MP) |
| CLINIC_STORAGE_MODE / CLINIC_DEMO_LOGIN | ephemeral / 0 (계정 로그인 사용) |
| QR_BASE_URL | Render의 실제 RENDER_EXTERNAL_URL을 빌드·시작 때 환경변수로 지정 |
| DJANGO_ALLOWED_HOSTS | 실제 RENDER_EXTERNAL_HOSTNAME 사용 |
| HTTPS | 보안 쿠키, HTTPS 리다이렉트, 프록시 헤더, HSTS 적용 |

사용자 지정 도메인을 쓰면 QR_BASE_URL과 DJANGO_ALLOWED_HOSTS를 Render 환경변수에서 직접 지정할 수 있습니다. 공개 배포에서는 localhost·사설 IP·HTTP QR 주소를 거부합니다. .env 파일은 자동으로 읽지 않습니다.

빌드는 의존성 설치와 collectstatic만 실행합니다. 시작은 새 임시 폴더 지정 → 저장 경로 준비 → migrate → 배포 보안 검사 → seed_demo → HEIC 변환 검사 → Gunicorn 순서입니다. Free에서 사용할 수 없는 pre-deploy command나 별도 one-off job에 초기화를 맡기지 않습니다.

## 면접 시연 순서

대표 환자는 김하나 · DEMO-1001, 동명이인은 김하나 · DEMO-1002입니다.

1. PC에서 실제 공개 HTTPS 주소에 로그인합니다.
2. 김하를 검색하고 차트번호로 두 환자를 구분합니다.
3. DEMO-1001을 열고 왼쪽 1주차(2026-10-05, 4장), 오른쪽 2주차(2026-10-12, 5장)를 선택합니다.
4. 썸네일을 눌러 정수리·헤어라인·측면 사진을 양쪽에서 바꿉니다.
5. 오른쪽을 3주차(2026-10-19, 0장)로 바꾸고 대상을 확인한 뒤 아이폰으로 사진 추가를 누릅니다.
6. 아이폰 Wi-Fi를 끄고 모바일 데이터의 Safari로 QR을 엽니다. 같은 계정으로 로그인하면 해당 방문 업로드 화면으로 돌아옵니다.
7. 사진 보관함에서 가상 사진 3장을 선택하고 미리보기·제거·촬영 부위를 확인한 뒤 업로드합니다.
8. PC에서 새로고침 없이 사진 수·썸네일이 3장으로 바뀌고 마지막 사진이 크게 표시되는지 확인합니다.
9. 같은 QR로 1장을 더 올려 총 4장을 확인합니다. 기존 사진과 왼쪽 사진도 계속 볼 수 있어야 합니다.
10. PC 페이지를 새로고침하고 오른쪽을 다시 3주차로 골라 4장을 확인합니다.
11. 서비스를 재시작·재배포한 뒤에는 새 데모 계정과 1주차 4장·2주차 5장·3주차 0장을 확인합니다.

비교 화면 기본값은 직전 2주차와 최근 3주차입니다. 아이폰이 없으면 이 브라우저에서 업로드 열기로 같은 화면을 사용할 수 있습니다. 새 방문은 주차와 실제 방문일을 직접 입력해 만들며 사진 0장이어도 선택할 수 있습니다.

## 공개 HTTPS 검증 명령

비밀번호는 실행 시 숨김 입력합니다. 자동화 환경에서는 CLINIC_DEMO_PASSWORD를 사용할 수 있습니다.

~~~powershell
$clinicPublicUrl = Read-Host "실제 Render HTTPS 주소"
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl --upload --output artifacts\public-verification.json
~~~

같은 서비스 실행 중에 PC 페이지를 새로고침한 뒤 재조회합니다.

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl --check-refresh artifacts\public-verification.json --output artifacts\after-refresh.json
~~~

Render에서 서비스를 재시작·재배포한 뒤 기본 샘플 복구를 확인합니다.

~~~powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl --check-reseed --output artifacts\after-restart.json
~~~

업로드 검증은 기존 3주차 사진을 지우지 않습니다. 현재 4장이면 4→7→8장이 됩니다. 처음부터 0→3→4를 시연하려면 새 서비스 실행 후 진행하세요. 자세한 범위는 [ops/README.md](ops/README.md)에 있습니다.

HTTP 검증은 실제 브라우저 JavaScript나 아이폰 Safari 조작을 대신하지 않습니다. 공개 주소에서 PC 자동 갱신, Safari 카메라·보관함 다중 선택·실제 HEIC 방향·실패 사진 재시도는 실기기로 최종 확인해야 합니다.

## 사진 처리와 접근 제한

- Patient → Visit → Photo 관계와 UploadSession → Visit 관계를 사용합니다.
- 사진은 서버가 생성한 파일명으로 비공개 폴더에 저장합니다. SQLite에는 메타데이터만 저장합니다.
- 원본은 비공개 originals 폴더에 보관하고 원본 URL은 제공하지 않습니다. 화면 JPEG·썸네일은 직원 인증 경로로 제공합니다.
- JPEG·PNG·HEIC/HEIF의 실제 형식, 파일 크기, 해상도를 검사합니다. 표시용 이미지는 방향을 적용하고 EXIF·GPS 등을 제거합니다.
- Free는 사진당 20MB·16MP, 한 번에 20장·100MB까지 받습니다. 아이폰 12MP 사진을 사용하세요. 표시용 이미지는 비율을 유지해 긴 변 2400px 이하로 만들고 원본은 그대로 보관합니다.
- 사진 처리는 한 번에 한 장씩 수행하며 다른 스레드에서 조회·폴링을 처리합니다.
- QR은 10분간 한 방문에 고정됩니다. 사진별 요청 ID로 재전송 중복을 막고 부분 실패만 재시도합니다.
- 일반 로그인 폼은 same-origin Referrer-Policy를 사용하며 CSRF 검증을 유지합니다.

## 테스트와 소스 묶음

~~~powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check_heif
.\.venv\Scripts\python.exe scripts\package_source.py
~~~

소스 ZIP은 artifacts/clinic-photo-demo-source.zip입니다. DB·사진·가상환경·키·환경변수 파일은 포함하지 않습니다.

자동 테스트 56개가 통과했으며, Free 전용 Blueprint의 공식 스키마 검사도 통과했습니다. 초기화 재실행 시 현재 업로드 유지, 서비스 시작마다 새 임시 경로 선택, 로그인 CSRF, 이미지 크기 제한과 비율 유지도 검증했습니다. 현재 검증 기록은 공개 Render 배포 성공 기록은 아닙니다. 최종 공개 HTTPS 주소와 실기기 결과를 확인한 뒤 배포 완료로 판단합니다.

## 같은 Wi-Fi에서 로컬 아이폰 시연

~~~powershell
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost,192.168.0.25"
$env:QR_BASE_URL = "http://192.168.0.25:8000"
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
~~~

192.168.0.25는 ipconfig로 확인한 노트북의 실제 IPv4로 바꾸세요. 노트북의 localhost는 아이폰에서 노트북을 가리키지 않습니다. 이 방식은 같은 신뢰할 수 있는 Wi-Fi에서만 시연하며, 면접장에서는 공개 HTTPS 주소를 사용합니다.

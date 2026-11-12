# 진료 사진 조회·비교 프로토타입

Django + SQLite로 실행하는 의원 면접 과제 1의 첫 번째 프로토타입입니다. 환자 검색, 방문별 사진 비교, QR을 통한 아이폰 다중 사진 업로드, PC 화면 자동 갱신을 제공합니다. 녹음, 음성 전사, CRM 연동은 포함하지 않습니다.

모든 데모 환자와 샘플 이미지는 **가상 자료**입니다. 샘플 이미지는 프로젝트 코드가 직접 생성하므로 외부 네트워크 없이 표시됩니다. 모바일 업로드 시연은 가상 데이터와 신뢰할 수 있는 네트워크에서 진행하세요. 실제 환자 데이터는 HTTPS, 운영 인증·권한 관리, 감사 기록, 백업, 보관 정책 등 운영 보안이 준비된 환경에서만 사용해야 합니다.

## Windows PowerShell에서 실행

Python 3.12를 권장합니다. Django 5.2는 Python 3.10 이상을 지원하며, 이 프로젝트는 Python 3.12에서 검증했습니다. `py`가 없으면 설치한 Python의 `python` 명령을 사용하세요.

```powershell
cd C:\Users\Administrator\Desktop\home_work
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

브라우저에서 <http://127.0.0.1:8000/>를 열고 로그인합니다.

| 항목 | 값 |
| --- | --- |
| 데모 직원 아이디 | `dlwo8520` |
| 비밀번호 | 최초 데모 생성 시 숨김 입력한 값 |
| 대표 가상 환자 | 김하나 · `DEMO-1001` |
| 동명이인 | 김하나 · `DEMO-1002` |

`seed_demo`는 같은 환자·방문·사진을 중복 생성하지 않습니다. 기존 계정의 비밀번호와 이미 업로드한 사진을 유지합니다. 대표 환자는 처음 생성할 때 1주차(2026-10-05) 4장, 2주차(2026-10-12) 5장, 3주차(2026-10-19) 0장을 갖습니다. 1·2주차에 정수리, 헤어라인, 측면 사진이 있으며 같은 촬영 부위의 사진도 여러 장 있습니다. 동명이인 환자는 같은 1주차에 방문일이 다른 방문 두 건을 갖습니다.

새 로컬 계정의 비밀번호는 최초 `seed_demo` 실행 시 숨김 입력합니다. 소스에 비밀번호를 포함하지 않습니다. 공개 서버에서는 `DJANGO_DEBUG=0`으로 실행하고 배포 환경변수 `CLINIC_DEMO_PASSWORD`에 비밀번호를 지정합니다. 실제 배포 비밀번호나 서명 키를 저장소·README·배포 로그에 넣지 않습니다. 계정이 이미 있으면 `seed_demo`는 환경변수의 새 비밀번호로 변경하지 않습니다.

## Render 공개 HTTPS 배포

같은 Wi-Fi 밖에서도 아이폰 셀룰러 데이터로 QR을 열려면 실제 공개 HTTPS 서버가 필요합니다. 이 프로젝트의 `render.yaml`, `scripts/render-build.sh`, `scripts/render-start.sh`는 **Render Python 웹 서비스와 유료 영구 디스크**를 구성합니다. 현재 문서에 실제 발급된 공개 URL은 없으며, 아래 절차를 완료한 뒤 Render가 표시하는 주소를 사용해야 합니다. 배포 설정 준비와 실제 공개 서비스 접속 검증은 별도입니다.

소스 저장소는 https://github.com/dlwo8520/clinic-photo-demo 입니다. Render 플러그인 설치와 Render 계정 연결은 별개이며, 배포는 해당 계정의 Dashboard에서 진행할 수도 있습니다. 아래 Git 명령은 새 작업 폴더에서 저장소를 연결할 때 참고하는 예시입니다.

```powershell
# 현재 소스 폴더에서 실행. 새 GitHub 저장소는 README를 자동 생성하지 않은 빈 저장소로 만듭니다.
git init
git add .
git commit -m "Add clinic photo comparison prototype"
git branch -M main
$clinicRepoUrl = Read-Host "방금 만든 비공개 GitHub 저장소의 HTTPS URL"
git remote add origin $clinicRepoUrl
git push -u origin main
```

Git을 쓰기 어려우면 GitHub의 **Add file → Upload files**에서 소스만 올릴 수 있습니다. 소스 묶음은 다음 명령으로 다시 만들 수 있고, 생성 위치는 `artifacts/clinic-photo-demo-source.zip`입니다. 압축을 푼 뒤 `manage.py`와 `render.yaml`이 저장소 루트에 오도록 업로드하세요. 압축은 소스 폴더·파일 허용 목록으로 만들며 DB·사진·환경변수·런타임·실제 키를 포함하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts\package_source.py
```

Render의 기본 파일시스템은 재시작·재배포 시 유지되지 않습니다. 이 앱은 SQLite와 사진을 같은 영구 디스크 아래 저장하며, 디스크 없는 무료 서비스로는 업로드 보존 조건을 충족하지 않습니다. 영구 디스크는 실행 중에만 접근할 수 있으므로 빌드 단계에서 마이그레이션이나 데모 생성을 하지 않습니다. 자세한 제약은 [Render 영구 디스크 문서](https://render.com/docs/disks)를 참고하세요.

1. 위에서 만든 저장소에 소스가 올라왔는지 확인합니다. `.venv`, `.runtime`, `db.sqlite3`, `private_media`, `.local_secret_key`, `.env`는 `.gitignore`로 제외합니다. 기존 로컬 DB·사진·키를 저장소에 포함하지 마세요.
2. Render 계정에서 **New → Blueprint**를 열고 해당 저장소를 연결합니다. 루트의 `render.yaml`을 사용합니다. 유료 서비스·디스크 비용을 확인하고 생성합니다. [Render Django 배포 안내](https://render.com/docs/deploy-django)와 [Blueprint 명세](https://render.com/docs/blueprint-spec)를 참고하세요.
3. Blueprint는 Python `3.12.16`, 컴퓨트 플랜 `1c-2g`(2GB), 영구 디스크 **1GB**, 마운트 경로 `/var/data`로 구성돼 있습니다. 디스크가 연결됐는지 확인하고 웹 서비스는 한 인스턴스로 운영합니다. 디스크를 분리하거나 삭제하면 저장 보존 조건이 사라집니다.
4. Render Dashboard의 **Environment**에서 아래 값을 지정합니다. `sync: false` 항목은 실제 값이 저장소에 들어가지 않도록 대시보드에서 입력하는 항목입니다. 필수 입력은 `DJANGO_SECRET_KEY`와 `CLINIC_DEMO_PASSWORD` 두 항목입니다. 공개 주소와 허용 호스트는 서비스 생성 시 발급되는 Render 환경변수에서 자동 지정하므로 최초 배포 전에 주소를 추측할 필요가 없습니다.

| 환경변수 | Render 값 |
| --- | --- |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | 직접 생성한 50자 이상의 무작위 키를 대시보드에 입력. Blueprint가 자동 생성하지 않음 |
| `DJANGO_ALLOWED_HOSTS` | 빌드·시작 스크립트가 Render의 실제 공개 호스트명을 자동 지정. 사용자 지정 도메인은 Dashboard에서 덮어쓸 수 있음 |
| `QR_BASE_URL` | 빌드·시작 스크립트가 Render가 발급한 실제 공개 HTTPS 주소를 자동 지정. 사용자 지정 도메인은 Dashboard에서 덮어쓸 수 있음 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 필요할 때 실제 HTTPS 원점. 생략하면 QR 원점 사용 |
| `CLINIC_DATA_DIR` | `/var/data/clinic` |
| `CLINIC_SEED_DEMO` | 가상 자료 생성 시 `1`. 재시작마다 중복 없이 실행 |
| `CLINIC_DEMO_PASSWORD` | 공개 서버용으로 별도 생성한 비밀번호. 대시보드에서만 지정 |

환경변수 입력·배포 방식은 [Render 환경변수 문서](https://render.com/docs/configure-environment-variables)를 참고하세요. 이 앱은 배포 모드에서 비밀 키와 공개 HTTPS QR 주소를 명시적으로 요구하며 `localhost`로 대신하지 않습니다. 새 공개 데모 계정 생성 시 비밀번호 환경변수가 없으면 시드를 중단합니다. 기존 계정은 비밀번호를 유지하므로 비밀번호 변경은 Render Shell에서 `python manage.py changepassword dlwo8520`로 별도 수행합니다.

서명 키는 로컬에서 다음 명령으로 생성해 결과를 Render Dashboard의 `DJANGO_SECRET_KEY`에 복사할 수 있습니다. 생성한 실제 값은 소스 파일에 저장하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

5. Build Command는 `bash scripts/render-build.sh`, Start Command는 `bash scripts/render-start.sh`입니다. 빌드는 의존성 설치와 `collectstatic`만 수행합니다. 시작 스크립트는 실제 영구 디스크 마운트를 확인하고, 마이그레이션 → `check --deploy --fail-level WARNING` → 선택한 경우 데모 생성 → HEIF 확인 → Gunicorn 실행 순서로 동작합니다. Gunicorn은 작업자 1개·스레드 2개, 요청 제한시간 180초로 실행합니다. 정적 CSS·JavaScript는 WhiteNoise가 제공하고 사진은 계속 직원 인증이 필요한 Django 경로로 제공합니다.
6. 배포 로그와 상태를 확인한 뒤 실제 HTTPS 주소를 PC에서 엽니다. 아이디 `dlwo8520`과 대시보드에서 설정한 배포 비밀번호로 로그인합니다. 아이폰 Wi-Fi를 끄고 셀룰러 데이터에서 같은 주소와 새 QR이 열리는지 확인합니다. 공개 배포에서는 노트북의 `0.0.0.0` 바인딩·사설 IP·포트 포워딩이 필요하지 않습니다.

시작 스크립트가 초기화를 자동으로 수행하지만 수동 확인이 필요하면 **해당 실행 중인 웹 서비스의 Render Shell**에서 다음 명령을 실행합니다. 영구 디스크가 없는 별도 one-off job이나 빌드 단계에서 실행하지 않습니다. 첫 계정 생성 시에는 대시보드의 `CLINIC_DEMO_PASSWORD`가 설정돼 있어야 합니다.

```bash
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py check_heif
```

디스크의 실제 데이터 경로는 `/var/data/clinic/db.sqlite3`와 `/var/data/clinic/private_media`입니다. 같은 디스크를 연결한 서비스 재시작·재배포 후에도 이 경로를 유지해야 합니다. 단일 인스턴스 SQLite 프로토타입이며 실제 환자 운영용으로 공개 배포 보안이 완성됐다는 의미는 아닙니다.

### 공개 서비스 인수 확인 기록

실제 Render 계정 연결·배포·공개 URL 발급과 아이폰 실기기 확인은 아직 완료되지 않았습니다. 아래 표는 배포 후 수행할 기준이며, 성공했다고 기록한 결과가 아닙니다.

| 확인 항목 | 확인 방법과 기대 결과 | 현재 상태 |
| --- | --- | --- |
| 공개 HTTPS와 로그인 | 실제 Render URL에서 `dlwo8520` 로그인 | 미확인 |
| 검색·비교 | `김하` 검색, 동명이인 차트 구분, 1주차 4장·2주차 5장 비교 | 공개 서버 미확인 |
| Wi-Fi 밖 QR | 아이폰 Wi-Fi를 끄고 셀룰러 Safari에서 QR 열기·로그인 복귀 | 실기기 미확인 |
| 3주차 3장 + 1장 | 최초 0장인 3주차 QR로 3장 저장 후 1장 추가, 총 4장 | 공개 서버·실기기 미확인 |
| PC 자동 갱신 | 새로고침 없이 약 2초 후 개수·썸네일·마지막 사진 갱신 | 브라우저 미확인 |
| 서비스 재시작 보존 | Render에서 같은 서비스 Restart 후 3주차 4장과 1·2주차 재조회 | 공개 서버 미확인 |
| 재배포 보존 | 같은 영구 디스크로 Manual Deploy 후 같은 사진·방문·계정 재조회 | 공개 서버 미확인 |

데모 시드는 3주차에 이미 올린 사진을 삭제하거나 0장으로 초기화하지 않습니다. 인수 시연을 반복할 때는 기존 누적 개수를 기록하거나 새 방문을 만들어 확인하세요. 사진 보존 검증을 위해 DB·영구 디스크를 지우거나 시드로 초기화하지 않습니다.

### 실제 공개 서버의 HTTP 확인

배포 후에는 다음 명령에서 실제 Render 주소를 입력합니다. 비밀번호는 실행 시 숨김 입력하므로 명령에 넣거나 파일에 저장할 필요가 없습니다. 조회 검증 후 `--upload`로 3주차에 가상 PNG 3장과 1장을 추가할 수 있습니다.

```powershell
$clinicPublicUrl = Read-Host "실제 Render HTTPS 주소"
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl --upload --output artifacts\public-verification.json
```

Render에서 서비스를 실제로 Restart한 후 다음을 실행합니다. 이후 Manual Deploy 후에도 같은 방식으로 확인하세요.

```powershell
.\.venv\Scripts\python.exe ops\verify_public.py --base-url $clinicPublicUrl --check-restart artifacts\public-verification.json --output artifacts\after-restart-verification.json
```

검증 스크립트는 이전 사진 ID와 화면용 이미지·썸네일의 SHA-256을 비교합니다. 스크립트가 재시작 자체를 수행하거나 증명하지는 않으므로 Render의 작업 기록도 확인해야 합니다. HTTP 확인은 PC JavaScript와 아이폰 Safari의 실제 조작 검증을 대신하지 않습니다. 자세한 옵션과 범위는 [ops/README.md](ops/README.md)에 있습니다.

## 같은 Wi-Fi의 아이폰에서 열기

노트북의 `localhost` 또는 `127.0.0.1`은 아이폰에서 노트북을 가리키지 않습니다. 아이폰에서 접근할 수 있는 노트북의 실제 사설 IPv4 주소를 QR 주소에 사용해야 합니다.

1. 노트북과 아이폰을 같은 신뢰할 수 있는 Wi-Fi에 연결합니다.
2. PowerShell에서 `ipconfig`를 실행하고 사용 중인 Wi-Fi 어댑터의 IPv4 주소를 확인합니다. 아래의 `192.168.0.25`를 그 주소로 바꿉니다.
3. 서버를 실행하는 **같은 PowerShell 창**에서 환경변수를 지정하고 서버를 실행합니다.

```powershell
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost,192.168.0.25"
$env:QR_BASE_URL = "http://192.168.0.25:8000"
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

`0.0.0.0:8000`은 서버가 네트워크 접속을 수신하는 바인딩 주소입니다. QR이나 브라우저에 입력할 주소는 `http://192.168.0.25:8000`입니다. `ALLOWED_HOSTS`에는 스킴·포트 없이 호스트만 쉼표로 나열합니다. `QR_BASE_URL`에는 스킴과 포트를 포함합니다. 주소를 변경한 뒤에는 서버를 재시작하고 QR을 새로 생성하세요. `.env` 파일은 자동으로 읽지 않습니다.

Windows 방화벽이 요청하면 신뢰하는 **개인 네트워크**에서 Python의 수신을 허용하세요. 접속이 안 되면 아이폰 Safari에서 위 주소를 직접 열어 확인하고, Wi-Fi의 기기 간 통신 차단 또는 게스트 네트워크 분리 여부를 확인하세요. 이 개발 서버를 인터넷에 공개하거나 공유기의 포트 포워딩을 설정하지 마세요.

아이폰 Safari에서 QR을 처음 열면 같은 `dlwo8520` 계정으로 로그인합니다. 로그인 후 QR의 업로드 화면으로 돌아오며 환자 이름·차트번호·주차·방문일을 확인할 수 있습니다. PC의 로그인과 아이폰 로그인은 각각 필요합니다.

## 시연 순서

1. 로그인 후 `김하` 또는 `DEMO-1001`로 검색합니다. 동명이인 두 명의 차트번호, 최근 방문일, 방문 수를 확인합니다.
2. 김하나 `DEMO-1001`의 비교 화면을 엽니다. 왼쪽에 1주차, 오른쪽에 2주차를 선택합니다. 각각 4장·5장의 썸네일을 눌러 큰 사진과 촬영 부위를 확인합니다. 기본 선택은 직전 방문인 2주차와 최근 방문인 3주차입니다.
3. 오른쪽을 사진 없는 3주차로 바꿉니다. 표시된 대상 환자·방문을 확인하고 **아이폰으로 사진 추가**를 누릅니다. 10분간 유효한 QR과 만료 시각이 표시됩니다.
4. 아이폰 Safari에서 QR을 열고 로그인합니다. **카메라로 촬영** 또는 **사진 보관함에서 여러 장 선택**으로 가상 사진 3장을 선택합니다. 미리보기·개수를 확인하고 필요하면 개별 사진을 제거하거나 촬영 부위를 입력한 뒤 한 번에 업로드합니다.
5. 사진별 **저장 완료**를 확인합니다. PC는 약 2초마다 현재 오른쪽 방문을 확인하므로 새로고침 없이 3장과 마지막 사진이 나타납니다. 업로드 중 PC에서 다른 방문으로 이동해도 저장 대상은 QR 생성 당시의 3주차로 유지됩니다.
6. 같은 유효한 QR로 1장을 더 올립니다. 3주차가 총 4장이 되고 기존 사진이 유지됩니다. 새로고침 후, 서버를 종료했다가 같은 명령으로 재시작한 뒤에도 4장을 확인하고 1·2주차 사진을 다시 조회합니다.
7. 아이폰 없이 시연할 때는 QR 아래 **이 브라우저에서 업로드 열기**를 눌러 같은 업로드 화면을 새 탭으로 엽니다.

새 방문은 환자 비교 화면에서 주차와 실제 방문일을 입력해 만듭니다. 주차는 날짜로 계산하지 않으며 같은 주차의 방문을 여러 건 만들 수 있습니다. 사진 0장인 방문도 오른쪽에 선택할 수 있습니다. 새 방문을 만들지 않고 기존 방문을 선택해 사진을 추가할 수도 있습니다.

## 파일 처리와 접근 제한

- SQLite는 환자·방문·사진 메타데이터를 저장합니다. 원본 바이너리를 DB에 넣지 않습니다. 이미지 파일은 `private_media`의 비공개 경로에 저장하고 서버가 파일명을 생성합니다. 원본은 비공개 `originals/*.bin`에 보관하며 원본을 여는 URL은 제공하지 않습니다. 화면용 JPEG와 썸네일은 별도로 생성합니다.
- 사진과 썸네일은 로그인한 직원의 권한을 검사하는 Django 경로로만 제공됩니다. 비공개 폴더를 정적 파일이나 웹 서버의 공개 경로로 연결하지 마세요.
- JPEG·PNG와 서버에서 디코딩할 수 있는 HEIC·HEIF를 지원합니다. 확장자 대신 실제 이미지 형식·크기·해상도를 검사합니다. 화면용 파일에는 촬영 방향을 적용하고 EXIF·GPS 등 불필요한 메타데이터를 제거합니다.
- 한 번에 최대 20장, 사진당 최대 20MB, 요청 전체 최대 100MB입니다. 사진은 가로·세로 각각 64px 이상, 각 변 12,000px 이하, 총 4천만 화소 이하만 허용합니다.
- QR에는 환자 이름이나 차트번호가 들어가지 않습니다. 예측하기 어려운 토큰은 한 방문에만 연결되며 10분 뒤 만료됩니다. 유효 시간 안에서는 여러 번 업로드할 수 있습니다. 서버는 로그인·토큰·대상 방문 일치를 검사합니다.
- 사진별 요청 ID로 재시도를 구분하므로 같은 요청의 재전송은 사진을 중복 등록하지 않습니다. 일부 사진만 실패하면 실패한 사진만 다시 시도합니다. 처리 실패로 생긴 임시 파일은 정리하고 정상 처리한 사진만 목록에 등록합니다.

`Patient → Visit → Photo` 관계와 `UploadSession → Visit` 관계를 사용합니다. PC·모바일 화면은 같은 Django 템플릿 서버를 사용하고, PC JavaScript는 현재 오른쪽 방문의 사진 목록을 약 2초마다 조회합니다. 업로드 대상은 PC의 현재 선택값이 아닌 서버에 저장한 QR 세션의 방문입니다. 데모에서는 로그인한 활성 직원 계정에 전체 가상 환자 접근을 허용합니다.

구현 시 [Django 파일 업로드 문서](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/)의 multipart 처리 방식, [Django 사용자 업로드 보안 안내](https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content), [pillow-heif 플러그인 문서](https://pillow-heif.readthedocs.io/en/latest/pillow-plugin.html)의 디코더 등록 방법을 참고했습니다. 업로드 파일은 검사 후 새 이미지로 다시 인코딩하며, 공개 정적 파일 경로로 제공하지 않습니다.

## 테스트와 HEIF 지원 확인

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check_heif
```

`pillow-heif` 설치 또는 디코더 준비가 실패한 환경에서는 HEIC/HEIF 업로드가 지원되지 않으며 모바일 화면에서 이유를 표시합니다. 이 경우 JPEG·PNG로 시연할 수 있습니다. 이미지가 손상되었거나 서버에서 변환할 수 없으면 해당 사진만 실패 상태와 이유를 반환합니다.

자동 테스트는 환자 검색, 다중 사진 DB 저장, 토큰·방문 일치, 만료 토큰, 익명 사진 접근 차단, 잘못된 이미지와 동일 요청 재전송을 검증합니다. 이 작업 환경에서는 **Django 테스트 46개가 모두 통과**했고, 일반 로그인 폼의 CSRF 검증도 포함했습니다. `check_heif`로 실제 HEIC를 생성해 화면용 JPEG·썸네일로 변환하고 메타데이터가 제거되는 경로를 확인했습니다. JavaScript 구문 검사도 통과했습니다. 배포 설정으로 `collectstatic`과 `manage.py check --deploy --fail-level WARNING`도 경고 없이 통과했습니다.

별도 로컬 테스트 데이터 경로 `.runtime/smoke-data`에서 실제 HTTP 서버에 로그인·검색·QR·업로드 요청을 보내 **3주차 0 → 3 → 4장**, 동일 요청 재전송의 중복 방지를 확인했습니다. 서버 프로세스를 종료하고 재시작한 후 마이그레이션과 시드를 다시 실행해도 새 샘플은 생성되지 않았고, 사진 13장과 각각의 썸네일의 ID·SHA-256이 유지됐습니다. 결과는 [재시작 전 기록](artifacts/local-http-before-restart.json)과 [재시작 후 기록](artifacts/local-http-after-restart.json)에 있습니다. 이 검증은 HTTP 루프백 기준이며 공개 HTTPS 배포 검증이 아닙니다. 기본 로컬 데모 DB는 1주차 4장·2주차 5장·3주차 0장으로 유지했습니다.

Windows 환경이므로 Linux용 Gunicorn 프로세스와 Render의 실제 빌드·디스크 마운트는 실행 확인하지 못했습니다. Render 계정 연결·원격 저장소 생성·공개 URL 발급도 남아 있습니다.

브라우저 환경의 접근 제한으로 PC 브라우저의 실제 화면 조작과 실제 아이폰 Safari 검증은 완료하지 못했습니다. 자동 테스트의 HTTP 응답·DB·파일 처리 검증과 브라우저의 화면·동작 검증은 구분해야 합니다. 다음 항목은 실제 기기에서 확인하세요.

- 노트북의 사설 IPv4 주소로 만든 QR을 같은 Wi-Fi의 아이폰 Safari에서 열고, 로그인 후 해당 업로드 화면으로 돌아오는지 확인합니다.
- 카메라 권한·촬영과 사진 보관함의 일반 파일 입력에서 여러 장 선택이 동작하는지 확인합니다.
- 실제 아이폰 HEIC와 세로로 촬영한 사진의 변환·방향·미리보기를 확인합니다.
- 정상 이미지와 잘못된 파일을 함께 전송해 사진별 결과가 표시되고, 실패한 사진만 재시도되는지 확인합니다.
- 업로드 도중 PC 방문을 변경해도 QR에 연결된 방문에 저장되고, PC에서 그 방문을 선택하면 새 사진·개수·마지막 사진이 갱신되는지 확인합니다.
- 같은 QR로 3장과 1장을 차례로 업로드한 뒤 총 4장 유지, 새로고침·서버 재시작 후 재조회, QR 만료 상태를 확인합니다.

## 설정

| 환경변수 | 용도 |
| --- | --- |
| `DJANGO_ALLOWED_HOSTS` | 허용할 호스트 목록, 쉼표로 구분 |
| `QR_BASE_URL` | 아이폰에서 접근할 수 있는 서버 주소. 기본 `http://127.0.0.1:8000` |
| `DJANGO_SECRET_KEY` | Django 서명 키. 별도 환경에서는 충분히 긴 무작위 값을 지정 |
| `DJANGO_DEBUG` | 로컬 프로토타입용 디버그 설정 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 신뢰할 HTTPS 원점 목록. 배포에서 QR 원점이 기본 |
| `CLINIC_DATA_DIR` | SQLite·비공개 사진 저장 루트. 로컬 기본은 작업 폴더, Render는 `/var/data/clinic` |
| `CLINIC_SEED_DEMO` | Render 시작 시 데모 생성 여부. `1`이면 중복 없이 실행 |
| `CLINIC_DEMO_PASSWORD` | 새 공개 데모 계정의 비밀번호. 기존 계정 비밀번호는 변경하지 않음 |

환경변수는 해당 PowerShell 세션과 그 세션에서 실행하는 서버에 적용됩니다. 로컬에서는 `db.sqlite3`와 `private_media`, Render에서는 지정한 영구 디스크의 두 경로를 함께 보관하세요. 데모 명령을 다시 실행해도 이미 올린 사진은 제거하지 않습니다.

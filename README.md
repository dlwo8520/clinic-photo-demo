# 진료 사진 조회·비교 · 무료 면접 데모

Django와 SQLite로 만든 가상 진료 사진 앱입니다. 직원 인트라넷 과제 2와 프로젝트·DB·배포 서비스를 분리합니다. 모든 환자와 샘플 사진은 가상입니다.

**공개 HTTPS 주소: https://clinic-photo-demo.onrender.com/**

Render Free Web Service 배포와 실제 HTTPS 직원 접속·검색·QR·사진 3장+1장 업로드를 확인했습니다. 유료 서비스와 영구 디스크는 사용하지 않습니다. 접속 후 **직원으로 접속**을 누르세요. PC 자동 갱신과 아이폰 Safari 실기기 확인은 아래 자동 검증 결과와 구분합니다.

## 무료 배포 조건

- Render **Free Web Service** 한 개만 사용합니다. 유료 서비스·영구 디스크·외부 DB를 만들지 않습니다.
- SQLite와 사진은 `/tmp/clinic-photo-demo` 아래 임시 저장소를 사용합니다.
- 서버 시작 단계에서 디렉터리 준비 → 마이그레이션 → 운영 설정 점검 → `seed_demo` → HEIF 확인 → Gunicorn을 실행합니다.
- 초기화 명령을 다시 실행해도 기존 환자·방문·계정·사진을 중복 생성하거나 사진 파일을 덮어쓰지 않습니다.
- 브라우저 새로고침과 재접속은 같은 실행 인스턴스의 사진을 다시 조회합니다.
- Render 서버 재시작·재배포·절전 후 새 인스턴스가 만들어지면 임시 DB와 업로드 사진이 사라집니다. 새 서버는 기본 샘플을 자동 생성합니다. 장기 보존을 보장하지 않는 면접 데모입니다.
- 무료 서비스는 15분간 요청이 없으면 절전 상태가 되며, 다음 접속에서 기동에 약 1분이 걸릴 수 있습니다. 면접 직전에 접속해 준비하세요. [Render 무료 서비스 문서](https://render.com/docs/free)

## 접속과 시연

배포된 HTTPS 주소에서 **직원으로 접속** 버튼을 누릅니다. 무료 데모는 아이디·비밀번호 입력 없이 고정된 가상 직원 `dlwo8520`의 Django 세션으로 접속합니다. 사진·업로드 API는 계속 직원 세션을 검사합니다. `CLINIC_DEMO_LOGIN=0`이면 기존 직원 비밀번호 인증을 사용합니다.

1. PC에서 `김하` 또는 `DEMO-1001`로 검색합니다. 동명이인 김하나 두 명의 차트번호를 구분합니다.
2. 대표 환자 `DEMO-1001`의 **1주차 4장 / 2주차 5장**을 비교합니다.
3. 오른쪽에 **3주차(초기 0장)**를 선택하고 **아이폰으로 사진 추가**를 누릅니다.
4. 아이폰 Safari에서 QR을 열고 **직원으로 접속**합니다. 같은 환자·방문의 업로드 화면으로 돌아갑니다.
5. 가상 사진 3장을 선택해 업로드하고 각 사진의 저장 완료를 확인합니다. PC 오른쪽 사진 수·썸네일·큰 사진이 약 2초 후 자동으로 갱신되는지 확인합니다.
6. 같은 QR로 1장을 더 올리면 기존 사진을 유지한 채 총 4장이 됩니다. PC 새로고침 후에도 같은 3주차 사진을 조회합니다.
7. 서버 재배포 후에는 다시 1주차 4장 / 2주차 5장 / 3주차 0장의 기본 샘플로 시연할 수 있습니다. 기존 QR과 로그인 세션은 새로 준비하세요.

아이폰이 없으면 QR 아래 **이 브라우저에서 업로드 열기**로 업로드 흐름을 확인할 수 있습니다. 이 확인은 실제 아이폰 Safari 검증을 대신하지 않습니다. 실제 환자 이름·연락처·진료 사진은 입력하지 마세요.

## 샘플 데이터와 반복 초기화

`python manage.py seed_demo`가 가상 환자 8명, 직원 계정, 대표 환자의 1·2·3주차 방문과 기본 사진 9장을 준비합니다. 실제 사진을 내려받지 않고 코드로 명시적인 가상 일러스트를 만듭니다.

환자 차트번호, 방문 `demo_key`, 사진 `demo_key`와 고정 요청 UUID로 중복을 막습니다. 초기화 중 기존 사진을 삭제하거나 3주차를 비우지 않습니다. 현재 인스턴스에서 올린 사진과 원본·화면용 파일·썸네일을 유지합니다. 기존 계정의 비밀번호·권한도 재설정하지 않습니다. 새 무료 인스턴스의 빈 임시 저장소에서만 기본 데이터가 처음 생성됩니다.

## Render 설정

저장소: https://github.com/dlwo8520/clinic-photo-demo

| 항목 | 값 |
| --- | --- |
| Type / Runtime / Plan | Web Service / Python / **Free** |
| Region / Instances | Singapore / 1 |
| Branch | `main` |
| Build | `bash scripts/render-build.sh` |
| Start | `bash scripts/render-start.sh` |
| 상태 확인 URL | `/healthz/` · MCP 생성 서비스는 기본 TCP 상태 검사 사용 |
| Persistent disk | **없음** |
| SQLite | `/tmp/clinic-photo-demo/db.sqlite3` |
| Photos | `/tmp/clinic-photo-demo/private_media` |

`render.yaml`은 Free 설정만 선언합니다. 기존 유료 Blueprint와 디스크를 적용하지 마세요. Build 단계에서는 의존성 설치와 `collectstatic`만 수행하고 데이터는 서버 시작 때 만듭니다. Free 서비스는 Render Shell/one-off job을 제공하지 않으므로 시작 명령이 초기화를 자동 수행합니다.

| 환경 변수 | 값·설명 |
| --- | --- |
| `PYTHON_VERSION` | `3.12.16` |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | 서버 환경 변수의 무작위 키. Blueprint는 `generateValue: true`. 32자 이상이며 짧은 Render 생성값은 안정적으로 SHA-512 변환 |
| `CLINIC_STORAGE_MODE` | `ephemeral` |
| `CLINIC_DATA_DIR` | `/tmp/clinic-photo-demo` |
| `CLINIC_SEED_DEMO` | `1` |
| `CLINIC_DEMO_LOGIN` | `1` · 가상 직원 버튼 접속 |
| `QR_BASE_URL` | Render의 실제 `RENDER_EXTERNAL_URL`로 시작·빌드 스크립트가 자동 설정 |
| `DJANGO_ALLOWED_HOSTS` | Render의 실제 `RENDER_EXTERNAL_HOSTNAME`으로 자동 설정 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | 생략하면 실제 QR HTTPS 원점 사용 |
| `CLINIC_DEMO_PASSWORD` | 버튼 접속에서는 불필요. 비밀번호 인증 모드의 새 계정 생성에만 필요 |

비밀 키·비밀번호·DB·업로드 파일은 저장소에 포함하지 않습니다. `/tmp` 데이터는 공개 정적 폴더로 제공하지 않으며 직원 권한을 확인하는 Django 경로로만 사진을 읽습니다. HTTPS 보안 쿠키, CSRF, 명시적 호스트와 QR 원점을 유지합니다. Gunicorn은 worker 1개·thread 2개이고 QR 토큰이 포함된 접근 로그는 쓰지 않습니다.

## Windows 로컬 실행

Python 3.12를 권장합니다. 새 환경에서:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CLINIC_DEMO_LOGIN = '1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8003
```

로컬 QR을 같은 PC에서 시험하려면 `QR_BASE_URL=http://127.0.0.1:8003`를 설정합니다. 아이폰에서 노트북의 `127.0.0.1`은 열리지 않으므로 면접 시연은 공개 HTTPS 주소로 진행합니다. 로컬 개발 서버를 인터넷에 직접 노출하지 마세요.

## 업로드와 자동 갱신

JPEG·PNG·HEIC/HEIF를 실제 디코딩하고 확장자·크기·해상도를 검증합니다. 한 장 20MB, 요청 전체 100MB, 최대 20장을 허용합니다. 촬영 방향을 적용하고 화면용 JPEG·썸네일에서 EXIF/GPS를 제거합니다. 원본은 비공개 경로에 유지합니다. 무료 서버의 메모리 사용을 줄이기 위해 화면용 사진은 긴 변 2400px 이하로 만듭니다.

PC는 현재 오른쪽 방문의 사진 목록을 약 2초마다 조회합니다. 새 사진이 오면 개수·썸네일을 갱신하고 마지막 사진을 큰 화면에 선택합니다. QR은 생성 당시 한 방문에 고정되며 10분 뒤 만료됩니다. 같은 유효 QR로 추가 업로드할 수 있고 요청 UUID 재전송은 중복 사진을 만들지 않습니다.

## 검증 명령과 범위

```powershell
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check_heif
.\.venv\Scripts\python.exe ops/verify_public.py --base-url https://실제호스트.onrender.com --upload
```

`verify_public.py`는 공개 HTTPS 인증서, 직원 접속, 검색, 방문별 원문·썸네일 조회, 익명 접근 차단, QR 원점, 3장+1장 업로드, 중복 재전송 방지, 다른 주차 보존을 검사합니다. 버튼 접속을 자동 인식합니다. 증거 JSON에는 비밀번호나 QR 토큰을 기록하지 않습니다.

같은 실행 인스턴스에서 사진 ID·파일 해시를 다시 확인하려면 `--check-restart artifacts/public-verification.json`을 사용합니다. 옵션 이름은 기존 호환용이며 Free 서버가 실제로 재시작되어도 업로드가 남는다는 뜻이 아닙니다. Free 서버 재배포 후에는 **`--check-reset`**으로 기본 4장·5장·0장 복원을 검사합니다. 검증 스크립트가 재시작을 수행하지는 않습니다.

HTTP 검증은 PC JavaScript 실행과 실제 아이폰 Safari의 QR 스캔·사진 보관함·카메라 조작을 대신하지 않습니다. 자동 검증과 실기기 검증 결과를 구분해서 기록합니다.

## 실제 확인 결과 · 2026-11-12

| 항목 | 결과 |
| --- | --- |
| Render 서비스 | `clinic-photo-demo` · Singapore · **Free** · 영구 디스크 없음 |
| HTTPS 실제 접속 | 직원 버튼 접속·CSRF·환자 검색·동명이인 차트 구분 통과 |
| 사진 업로드 | 공개 HTTPS에서 3주차 **0 → 3 → 4장**, 요청 재전송 중복 차단 통과 |
| QR | 공개 HTTPS 원점과 방문 연결, QR 이미지·업로드 경로 통과 |
| 사진 재조회 | 같은 서버에서 사진 ID, 화면용 이미지·썸네일 SHA-256 유지 확인 |
| 기존 샘플 보존 | 3주차 업로드 후 1주차 4장·2주차 5장 변경 없음 |
| 자동 테스트 | **52개 통과** |
| Linux HEIC | 실제 Render 시작 로그에서 HEIC → JPEG·썸네일 변환 확인 |
| Free 재배포 샘플 복원 | 같은 커밋을 재배포한 새 인스턴스에서 **4장·5장·0장** 자동 복원 통과 |
| PC 자동 갱신·실제 아이폰 Safari | 브라우저 제어 연결과 실기기 접근이 없어 사용자 확인 대기 |

실제 HTTP 증거 JSON은 로컬 `artifacts/public-verification.json`과 `artifacts/refetch-verification.json`에 저장했습니다. 이 파일은 저장소에 올리지 않으며 비밀번호와 QR 토큰을 포함하지 않습니다.

재배포 후 기본 샘플 복원 증거는 `artifacts/reset-verification.json`에 저장했습니다. 공개 요약은 [검증 요약](ops/public-verification-summary.json)에 있습니다. 재배포 검증은 실제로 수행했으며 단순 브라우저 새로고침 결과와 구분합니다.

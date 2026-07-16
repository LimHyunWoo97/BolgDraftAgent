# Blog Draft Agent

사진, 사실 메모, 기존 블로그 글을 바탕으로 네이버 블로그에 옮겨 쓸 **설계안과 완성 본문**을 만드는 Windows 데스크톱 앱입니다. 자동 발행은 하지 않으며, 작성자가 최종 검토한 뒤 네이버 에디터에 붙여 넣는 방식입니다.

## 주요 기능

- JPG/PNG/GIF/WEBP 사진 선택 및 사진별 메모 입력
- 선택한 사진의 가로 미리보기와 사진별 캡션 위치 확인
- 다크/라이트 모드 전환 및 카드형 작성 화면
- NVIDIA Build/NIM의 OpenAI 호환 API로 사진 분석, 글 설계, 완성 본문 생성
- **맛집 후기·카페·여행·제품 리뷰·일상·정보**별 구성 가이드
- 테마마다 내 기존 글 예시를 이 PC에 저장하고 다시 불러오기
- 예시 글의 문장 길이·어미·문단 호흡만 반영하고 원문 문장을 복사하지 않음
- **1단계 초안 설계 → 사용자 검토·수정 → 2단계 완성 본문** 작성
- 제목 후보, 소제목, `[사진 N 삽입]`, 해시태그, 확인 필요 목록 생성
- API 키가 없어도 로컬 템플릿 초안 생성
- Markdown/TXT 저장과 클립보드 복사
- 네이버 로그인 OAuth 연결(프로필 확인용, 게시물 발행 없음)

## 맛집 후기 말투를 반영하는 방법

1. 앱에서 테마를 **맛집 후기**로 선택한다.
2. `내 기존 글 예시` 칸에 본인의 맛집 후기 3개 이상을 붙여 넣는다.
3. **현재 테마 샘플 저장**을 누른다. 샘플은 `.style_profiles.json`에 로컬로만 저장되며 Git에 올라가지 않는다.
4. 새 글에서 장소, 메뉴, 가격, 운영시간, 방문 계기, 사진 메모처럼 사실을 입력한다.
5. **1. 초안 설계**에서 제목·소제목·사진 배치·확인 필요 정보를 검토하고, 수정한 뒤 **2. 본문 완성**을 누른다.

맛집 테마는 방문 계기 → 접근성/공간 → 메뉴·가격 → 기본찬/주문 메뉴 → 맛의 포인트 → 편의 정보 → 마무리 순서를 우선합니다. 제공한 예시처럼 짧은 문단, 친근한 존댓말, `인데요`·`같아요` 같은 종결 습관을 참고하되 주소·가격·영업시간 등 사진이나 메모에 없는 사실은 만들지 않습니다.

## NVIDIA API 키 발급과 연결

1. [NVIDIA Build API key 설정](https://build.nvidia.com/settings/api-key)에 로그인한다.
2. **Get API Key** 또는 **Generate**로 키를 만든다.
3. 앱의 **설정 → NVIDIA API 키 발급 페이지 열기**를 누른 뒤, 발급한 키를 `NVIDIA API Key` 칸에 붙여 넣고 저장한다.
4. 사용 가능한 모델은 NVIDIA Build에서 확인하고, 필요하면 사진 분석/글 작성 모델 이름을 설정 화면에서 변경한다.

### “이 동작에 대한 권한이 없습니다”가 보일 때

이 메시지는 이메일 인증 자체와 별개로, NVIDIA 개인 조직에 API 키 생성 권한이 아직 붙지 않았을 때 발생할 수 있습니다.

1. 로그아웃 후 [NVIDIA Build API Key](https://build.nvidia.com/settings/api-key)를 다시 열고 Developer Program/이용약관 동의를 완료한다.
2. API 키 생성 화면에서 가능하면 `Public API Endpoints` 권한이 포함된 개인 키를 만든다.
3. 계속 막히면 NVIDIA Developer Forums의 **NIM Access/Accounts** 카테고리에 계정 이메일, Personal organization, 오류 화면을 적고 `Public API Endpoints` 권한 확인을 요청한다. 키나 비밀번호는 절대 올리지 않는다.

키는 프로젝트 루트의 로컬 `.env`에만 저장됩니다. API 키, 네이버 Client Secret, `.style_profiles.json`은 절대 GitHub에 커밋하지 마세요.

기본 NVIDIA 엔드포인트는 아래와 같습니다. 직접 NVIDIA NIM을 운영할 경우에는 해당 서버의 `/v1` 주소로 바꾸면 됩니다.

```text
https://integrate.api.nvidia.com/v1
```

## 네이버 로그인

네이버 로그인은 현재 앱 사용자의 프로필을 확인하는 OAuth 연결입니다. 네이버 블로그 글 발행 권한은 사용하지 않습니다.

1. NAVER Developers에서 애플리케이션을 등록한다.
2. 네이버 로그인 사용을 설정한다.
3. Callback URL에 아래 주소를 등록한다.

```text
http://127.0.0.1:8765/callback
```

4. 발급한 Client ID와 Client Secret을 앱 설정 또는 로컬 `.env`에 입력한다.

## 실행

Windows에 Python 3.11 이상(Tcl/Tk 포함)을 설치한 뒤 실행합니다.

```powershell
cd C:\Users\twowinscom\Desktop\BlogAgent
py app.py
```

`.env.example`을 복사해 `.env`로 바꾸면 설정 항목을 미리 확인할 수 있습니다. API 키가 없어도 앱 창과 로컬 초안 기능은 실행됩니다.

## 테스트와 Windows 빌드

```powershell
cd C:\Users\twowinscom\Desktop\BlogAgent
python -m unittest discover -s tests
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1 -Clean
```

실행 파일은 `dist\BlogDraftAgent\BlogDraftAgent.exe`에 생성됩니다. 빌드 스크립트는 실제 Tcl/Tk 창을 열어 확인한 Python만 사용하므로, `No module named 'tkinter'` 또는 Tcl/Tk 누락 패키징을 사전에 막습니다.

## CI/CD 파이프라인

GitHub Actions가 다음 순서로 동작합니다.

```text
main 브랜치 push
  → 단위 테스트
  → Tkinter 런타임 확인
  → PyInstaller Windows EXE 빌드
  → ZIP 아티팩트 업로드

v* 태그 push
  → 위 검증 전체 통과
  → GitHub Release 생성 및 Windows ZIP 자동 첨부
```

새 버전을 배포할 때는 `v0.1.2`처럼 태그를 만들면 됩니다. 릴리스 워크플로우는 테스트 실패 시 실행 파일을 배포하지 않습니다.

## 프로젝트 운영 규칙

개발·테스트·보안·배포 규칙은 [AGENTS.md](AGENTS.md)에 정리되어 있습니다.

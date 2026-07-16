# Blog Draft Agent

사진, 간단한 메모, 사용자의 기존 글 예시를 바탕으로 **네이버 블로그용 초안**을 만들어 주는 Windows 데스크톱 MVP입니다.

자동 발행 기능은 포함하지 않습니다. 네이버 블로그 글쓰기 Open API가 종료된 상태이므로, 이 프로그램은 사용자가 사진 위치와 내용을 최종 검토한 뒤 네이버 에디터에 복사·붙여넣기 하는 방식으로 동작합니다.

## 현재 기능

- JPG/PNG/GIF/WEBP 사진 여러 장 선택
- 사진별 메모와 글 주제·사실 메모 입력
- 기존 글 예시에서 말투 프로필 생성
- NVIDIA Build 또는 자체 NIM의 OpenAI 호환 API 호출
  - 사진 분석
  - 제목 후보, 소제목, 사진별 캡션, 본문, 태그, 확인 필요 목록 생성
- 모델 키가 없을 때도 로컬 템플릿 초안 생성
- Markdown/TXT 저장 및 클립보드 복사
- 네이버 로그인 OAuth 연결(작성자 프로필 식별용, 글 발행 없음)
- PyInstaller용 Windows 빌드 스크립트

## 빠른 실행

1. Windows에 Python 3.11 이상을 설치한다. 설치할 때 **Add Python to PATH**를 선택한다.
2. `blog-agent` 폴더에서 `.env.example`을 복사해 `.env`로 이름을 바꾼다.
3. NVIDIA Build에서 받은 API 키를 `.env`의 `NVIDIA_API_KEY`에 넣거나, 프로그램의 **설정** 화면에서 입력한다.
4. PowerShell에서 실행한다.

```powershell
cd blog-agent
py app.py
```

API 키가 없어도 창과 로컬 초안 생성은 확인할 수 있다. 사진 내용을 실제로 분석하고 글의 품질을 높이려면 NVIDIA API 키가 필요하다.

## NVIDIA Build 설정

기본 주소는 다음과 같다.

```text
https://integrate.api.nvidia.com/v1
```

NVIDIA Build 계정에서 실제로 사용할 수 있는 모델 이름을 확인하고 설정 화면에서 바꿀 수 있다. 기본값은 사진 분석용 `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, 글 작성용 `nvidia/llama-3.3-nemotron-super-49b-v1.5`이다.

나중에 GPU 서버에 NVIDIA NIM을 직접 띄우는 경우에는 `NVIDIA_BASE_URL`만 해당 NIM의 `/v1` 주소로 바꾸면 된다. 이 앱은 OpenAI 호환 `chat/completions` 형식을 사용한다.

## 네이버 로그인 설정

네이버 로그인은 프로그램 사용자의 별명 등 프로필을 확인하기 위한 OAuth 연결이다. **네이버 블로그 글을 등록하거나 자동 발행하지 않는다.**

1. NAVER Developers에서 애플리케이션을 등록한다.
2. 네이버 로그인 사용을 설정한다.
3. Callback URL에 아래 주소를 정확히 등록한다.

```text
http://127.0.0.1:8765/callback
```

4. 발급받은 Client ID와 Client Secret을 설정 화면 또는 `.env`에 입력한다.
5. 프로그램에서 **네이버 로그인**을 누른다.

Client Secret과 NVIDIA API 키는 `.env`에만 저장한다. `.env`는 `.gitignore`에 포함되어 있으므로 Git에 올리지 않는다. 여러 사용자가 쓰는 서비스로 확장할 때는 데스크톱 앱에 공용 API 키를 넣지 말고, 별도 백엔드의 Secret 관리 기능을 사용해야 한다.

## 내 말투 반영 방식

처음에는 파인튜닝 대신 다음 방식을 사용한다.

1. 사용자가 본인의 과거 글 일부를 붙여 넣는다.
2. 프로그램이 문장 길이, 말투, 끝맺음, 이모지 사용을 분석해 말투 프로필을 만든다.
3. 새 주제와 겹치는 단어가 많은 예시 문단 최대 3개를 골라 모델에 제공한다.
4. 모델은 예시 문장을 복사하지 않고 말투와 구조만 반영해 새 초안을 만든다.

개인용 MVP에는 이 방식이 파인튜닝보다 비용이 적고 수정하기 쉽다.

## 출력과 발행 흐름

```text
사진 + 메모 + 기존 글 예시
  → 사진 분석
  → 말투 프로필
  → 제목/소제목/사진 설명/본문 초안
  → 사용자가 사실 확인
  → Markdown 또는 TXT 저장
  → 네이버 에디터에 복사·붙여넣기
  → [사진 N 삽입] 위치에 사진 배치 후 발행
```

모델은 사진으로 확인할 수 없는 가격, 주소, 영업시간, 인물 관계 등을 지어내지 않도록 지시되어 있다. 그래도 최종 발행 전에 반드시 `확인 필요` 항목과 문장을 검토해야 한다.

## 테스트

```powershell
cd blog-agent
py -m unittest discover -s tests
```

## Windows 실행 파일 만들기

PyInstaller를 사용해 실행 파일을 만든다. 이 명령은 첫 실행 때 PyInstaller를 설치하므로 인터넷 연결이 필요하다.

```powershell
cd blog-agent
Set-ExecutionPolicy -Scope Process Bypass
.\build.ps1
```

생성 위치:

```text
blog-agent\dist\BlogDraftAgent\BlogDraftAgent.exe
```

배포 시에는 `.env`를 실행 파일과 같은 폴더 또는 프로그램 루트에 안전하게 두고, 실제 키가 포함된 `.env`를 공개 저장소나 메신저에 공유하지 않는다.

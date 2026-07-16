# Blog Draft Agent 운영 가이드

## 목적과 범위

- 이 앱은 사용자가 최종 검토하는 블로그 **초안 도구**다.
- 네이버 자동 발행, 비밀번호 수집, 게시물 임의 등록은 구현하지 않는다.
- 사진·메모·사용자 말투 예시에서 확인할 수 있는 사실만 본문에 쓴다.

## 로컬 데이터와 보안

- `.env`, `.style_profiles.json`, API 키, OAuth Client Secret은 절대 커밋하지 않는다.
- 키는 채팅·로그·테스트 출력에도 노출하지 않는다.
- 테마별 말투 샘플은 로컬 파일에만 저장하며, 원문 문장을 생성 결과에 그대로 복사하지 않는다.

## 개발 규칙

- Python 표준 라이브러리를 우선 사용하고, 새 의존성은 필요성과 라이선스를 README에 기록한다.
- 테마를 추가할 때는 `blog_agent/style.py`의 가이드와 테스트를 함께 추가한다.
- API 키가 없어도 로컬 초안 모드가 동작해야 한다.
- UI 작업은 Windows의 `Malgun Gothic` 표시와 Tkinter 런타임을 고려한다.
- 사진 미리보기 의존성(Pillow)을 변경하면 `requirements.txt`, 빌드 스크립트, GitHub Actions 설치 단계를 함께 갱신한다.
- 글 생성 흐름은 `초안 설계 → 사용자 검토 → 완성 본문`을 유지하며, 완성 본문 단계도 설계안 밖의 사실을 새로 만들지 않는다.

## 검증

변경 후 아래 명령을 실행한다.

```powershell
python -m unittest discover -s tests
.\build.ps1 -Clean
```

실행 파일은 실제로 시작되는지 확인한다. PyInstaller는 Tcl/Tk 리소스를 포함해야 하므로 `tkinter` import만 확인하지 않는다.

## CI/CD와 릴리스

- `main` push: 테스트 → Tkinter 확인 → Windows EXE 빌드 → ZIP 아티팩트 업로드
- `v*` 태그 push: 위 단계를 통과한 뒤 GitHub Release와 ZIP을 생성
- 릴리스는 실패한 테스트를 우회하거나 기존 태그를 덮어쓰지 않는다.

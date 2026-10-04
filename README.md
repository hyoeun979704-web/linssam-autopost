# 린쌤 자동 편집·업로드

"비너스 셔플&라인 DANCE 린" 채널용. 휴대폰으로 찍은 영상을 구글 드라이브 폴더에 넣으면 자동으로 편집해서 정해진 요일·시간에 유튜브에 올린다. 유튜브 운영용 Claude 스킬도 같이 들어 있다.

## 선생님이 하실 일

1. **찍기.** 휴대폰을 세로로 세우고, 혼자, 머리부터 발끝까지 나오게 찍는다.
2. **폴더에 넣기.** 구글 드라이브 `린쌤자동업로드` 안의 폴더에 넣는다.
   - `쇼츠_입문` : 파일 이름을 `03 T스텝` 처럼 **번호 + 동작 이름**으로
   - `롱폼_라인댄스` : 파일 이름을 **곡명**으로 (예: `Lucky Lips`)

나머지(자르기, 세로 맞춤, 제목 띠, 박자 카운트, 수업 안내, 썸네일, 제목·설명, 업로드)는 자동이다. 문제가 있는 영상은 올리지 않고 `확인필요` 폴더로 옮긴다.

## 자동으로 하는 일

| 단계 | 내용 |
|---|---|
| 감지 | 30분마다 폴더 확인. 드라이브가 아직 복사 중인 파일은 건너뜀 |
| 편집 | 앞뒤 0.5초 자르기 → 선생님을 따라가며 세로(9:16)로 자르기 → 위쪽 제목 띠 → 음악 박자에 맞춘 1~8 카운트 → 마지막 2초 수업 안내 |
| 검사 | 사람이 잘 안 보이거나, 발끝이 잘렸거나, 쇼츠가 60초를 넘으면 `확인필요` 로 |
| 제목·설명 | 쇼츠: `셔플 입문 3/12 · T스텝 · 완전초보 따라하기 \| 천안셔플댄스`. 롱폼: 곡명 + 난이도 + 스텝시트 |
| 썸네일 | 롱폼은 선생님이 정면을 보는 장면을 골라 곡명·난이도를 빈 쪽에 넣음 |
| 업로드 | 쇼츠 화·금 19:00, 롱폼 매달 첫째 토 10:00. Aside 브라우저(선생님 계정)로 스튜디오에 올림. 화면의 채널명이 설정과 다르면 멈춤 |

### 왜 유튜브 API 가 아니라 브라우저로 올리나

유튜브 공식 업로드 API 는 구글 감사(audit)를 받지 않은 프로젝트로 올린 영상을 **비공개로 묶는다**(videos.insert 공식 문서). 감사가 끝나기 전까지는 Aside 브라우저로 스튜디오에 올린다.

## 설치

필요한 것: 컴퓨터(맥 또는 윈도우), 구글 드라이브 데스크톱 앱, Aside(선생님 계정으로 유튜브 로그인), 인터넷.

```bash
# 맥
git clone https://github.com/hyoeun979704-web/linssam-autopost.git
cd linssam-autopost
bash scripts/install_mac.sh
```

```powershell
# 윈도우 (PowerShell)
git clone https://github.com/hyoeun979704-web/linssam-autopost.git
cd linssam-autopost
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
```

설치 후 `config.yaml` 을 연다.
- `channel_name`: 스튜디오에 보이는 채널 이름 그대로
- `base_dir`: 구글 드라이브 폴더 경로
- `class_line`, `contact_line`: 수업 안내와 문의
- `aside_account`: Aside 계정이 여러 개면 선생님 계정 id

로그인은 선생님이 Aside 에서 직접 한다. 이 프로그램은 로그인·계정 전환을 하지 않는다.

## 확인 명령

```bash
.venv/bin/python -m autopost edit "영상.mp4"   # 편집 결과만 만들어 보기 (업로드 안 함)
.venv/bin/python -m autopost status            # 대기열과 업로드 결과
.venv/bin/python -m autopost tick              # 지금 한 번 실행
```

기록: `~/.linssam-autopost/log.txt`

## Claude 스킬

`.claude/skills/` 에 들어 있고 설치 스크립트가 `~/.claude/skills/` 에 연결한다.

| 스킬 | 용도 |
|---|---|
| `linssam-channel` | 이 채널 운영: 업로드 확인, 실패 재시도, 확인필요 처리, 제목 수정, 월간 점검 |
| `yt-script` `yt-shorts` `yt-package` `yt-seo` `yt-chapters` | 대본·쇼츠 구간·제목/썸네일·설명/태그·챕터 |
| `yt-edit` `yt-retention` | 편집점·시청 지속률 분석 |
| `yt-comment` `yt-plan` `yt-viral` `yt-audit` | 댓글·주간 계획·잘 된 영상 분석·채널 점검 |
| `youtube-tracking` | 채널 데이터 수집과 해석 |

`yt-*` 스킬은 [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill)(MIT)을 그대로 쓰고, `yt-script`·`yt-edit`·`yt-package` 에 한국어 사용 메모를 덧붙였다.

## 아직 확인하지 못한 것

- 스튜디오 업로드 단계(파일 선택 → 제목·설명 → 아동용 아님 → 공개 → 완료)는 선생님 계정으로 첫 실행 때 확인해야 한다. 채널명 확인에서 멈추는 동작은 다른 계정으로 확인했다.
- 롱폼 썸네일 업로드는 채널이 맞춤 썸네일 권한(전화 인증)을 가진 경우에만 된다.

## 라이선스

글꼴 Do Hyeon: SIL Open Font License (`assets/fonts/OFL.txt`).

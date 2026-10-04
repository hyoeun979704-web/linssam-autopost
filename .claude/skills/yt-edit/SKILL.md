---
name: yt-edit
description: >-
  Turn a raw recording's transcript into an edit decision list - dead air,
  filler cues and retakes, with timecodes. Use for "edit this", "cut the
  dead space", "tighten this video", "I rambled", or any request to shorten
  footage from a transcript.
---

# yt-edit

An edit decision list from a timestamped transcript. It prints the cuts. You apply them.

```bash
python3 deadair.py transcript.srt              # srt, vtt or whisper json
python3 deadair.py transcript.srt --floor 0.35 --json
```

No transcript yet? Ask for one, or produce one first - `whisper`, `faster-whisper`, or the caption
track YouTube generates on an unlisted upload all work. Do not guess at timings.

## What it finds

- **DEAD** - gaps longer than the floor, trimmed from the MIDDLE so both sides keep a breath.
  Cutting flush against speech is what makes a tightened take sound gasping.
- **FILLER** - cues that are nothing but "um", "so yeah", "basically".
- **REPEAT** - a sentence restarted. Compared against the last cue that was actually speech, not
  the literal previous cue, because most retakes have an "um" between the two attempts.

## What it will not do

It does not touch media. It has no opinion about your B-roll. A 40% cut on the report is a 40% cut
of SPEECH, and if the video has a long silent demo in it that number is wrong - check the report
against the footage before you trust the runtime at the bottom.

## 편집을 AI 에이전트에 넘길 때 (이 스크립트 범위 밖, 외부 주장 — local patch 2026-10-04)

- 러닝타임을 단어 수로 추정하지 않는다. 테이크를 실제 타임라인에 올려 잰 값만 쓴다. [higgsfield NuvA32_dmtg 2026-09-05, 미검증]
- 대본·원본 폴더·과거 프로젝트·폰트·효과음 팩을 함께 준다. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 컴퓨터 사용으로 편집 앱을 조작시키기 전에 프로젝트를 백업하고 민감한 앱을 닫는다. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 수정은 정확한 타임코드 목록으로 묶어 한 번에. 마이크로 포즈 같은 마지막 페이싱은 사람이 다듬는다. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 생성 내레이션·아바타는 문장 경계에서 끝나는 짧은 테이크로 나눠 틀린 문장만 다시 만든다. 테이크마다 대본 대조. [higgsfield NuvA32_dmtg 2026-09-05, 미검증]
- 화면 작업지시는 "무엇 → 어디·어느 캠 → 어느 단어에 등장·변경 → 언제 퇴장" 한 줄. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 인서트 사이 검사는 모든 레이어를 합친 실제 화면 기준(진행자가 몇 프레임 튀는 "깜박임"). [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 스크린캐스트는 속도 변경+양쪽 여유분, 프리즈·루프 금지, 입력 중 문장 끝까지. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- 납품 보고에 검수 수준 구분: 구조 비교 / 프레임 샘플 / 애니메이션 재생 / 오디오 포함 전체 재생 / 파일 디코딩. [higgsfield kOoC3yhUyDQ 2026-10-02, 미검증]
- Resolve 3캠 편집 스킬 원문(러시아어): `prompt-craft/references/외부자료/higgsfield_원본_2026-08_10/skills/kOoC3yhUyDQ__YT_video_editor_skill_2026-09-22/`.
## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?**

# 도구 목록

확인 시점 2026-09-09. 저장소 상태는 바뀐다. 도입 전에 최근 커밋일과 열린 이슈를 다시 본다.

## 1. 합법 코어 — 기본 경로

| 도구 | 최근 커밋 | 스타 | 라이선스 | 역할 |
|---|---|---|---|---|
| `google-api-python-client` | 2026-09-08 | 8.9k | Apache-2.0 | Data API v3 전체. **유일하게 약관 위반 없는 기반** |
| `python-youtube` (sns-sdks) | 2026-04-17 | 353 | MIT | Data API 얇은 래퍼. 편의용, 필수 아님 |

구글이 매주 릴리스한다. 스크립트의 기반은 여기다.

## 2. 분석 스택 (한국어)

### 감성 분류

| 모델 | 라이선스 | 30일 다운로드 | 비고 |
|---|---|---|---|
| `daekeun-ml/koelectra-small-v3-nsmc` | MIT | 250만 | 1차 선택. 영화리뷰 파인튜닝 |
| `nlp04/korean_sentiment_analysis_kcelectra` | MIT | 5.3k | 댓글체가 심하면 2차. 댓글 코퍼스 학습 백본 |
| `beomi/KcELECTRA-base` | MIT | 5.4k | 직접 파인튜닝할 때의 백본 |

**쓰지 않는다**: `tabularisai/multilingual-sentiment-analysis`는 상업 사용 금지 라이선스다. `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`, `lxyuan/distilbert-...-sentiments-student`, `nlptown/bert-base-multilingual-uncased-sentiment` 셋은 다운로드 수가 높지만 **학습 언어에 한국어가 없다**. 한국어 댓글에 쓰면 성능 보장이 없다.

라이선스가 명시되지 않은 모델이 여럿 있다. `circulus/koelectra-sentiment-v1`, `circulus/koelectra-emotion-v1`, `smilegate-ai/kor_unsmile`, `matthewburke/korean_sentiment`, `jhgan/ko-sroberta-multitask`, `snunlp/KR-SBERT-V40K-klueNLI-augSTS`, `Leo97/KoELECTRA-small-v3-modu-ner`가 그렇다. 내부 분석에는 쓸 수 있으나 **상업 배포 전에 확인이 필요하다.**

### 임베딩·키워드

| 도구 | 라이선스 | 비고 |
|---|---|---|
| KeyBERT | MIT | 키워드 추출 프레임 |
| `jhgan/ko-sroberta-multitask` | 미표기 | KeyBERT 백본으로 쓸 한국어 임베딩 |
| `intfloat/multilingual-e5-large` | MIT | 다국어 임베딩. 라이선스가 깨끗한 대안 |
| KR-WordRank | **LGPL** | 비지도 한국어 키워드 |
| soynlp | **LGPL** | 미등록어 추출 |

**한국어 키페이즈 추출 전용 모델은 사실상 없다.** 허깅페이스의 키페이즈 모델은 영어 전용이다. 라이브러리 조합으로 푼다.

LGPL 세 개는 배포 형태에 따라 검토가 필요하다. 사내 분석 스크립트면 문제없지만 제품에 정적 링크하면 다르다.

### 형태소 분석기

**konlpy를 쓰지 않는다.** 2022년 1월 이후 릴리스가 없고, 번들된 Okt가 업스트림보다 낮은 버전이며, MeCab 설치 스크립트가 고장 나 있고 관련 이슈가 열린 채다. 윈도우에서 MeCab이 지원되지 않는다.

**`kiwipiepy`가 유일하게 유지된다.** 2026-08 커밋. LGPL. 오타 교정과 미등록어 추출 API를 내장한다. 유튜브 댓글처럼 표기가 흔들리는 텍스트에 그 기능이 필요하다.

### 데이터셋 (파인튜닝용)

| 데이터셋 | 라이선스 | 비고 |
|---|---|---|
| `LLM-SocialMedia/Korean-YouTube-Comment-Sentiment-Dataset` | other | 용도가 가장 정확히 맞는다. 조건 확인 필요 |
| `e9t/nsmc` | CC-BY-2.0 | 한국어 감성 표준 벤치 |
| `jeanlee/kmhas_korean_hate_speech` | CC-BY-SA-4.0 | 혐오 8종 다중라벨 |

## 3. 비공식 경로 — 사용자 승인 필요

아래는 전부 유튜브 서비스 약관에 저촉된다. 약관은 로봇·봇넷·스크래퍼 등 자동화 수단으로 서비스에 접근하는 것을 금지하고, 별도로 사용자 이름이나 얼굴 같은 개인 식별 가능 정보 수집을 금지한다.

**기본값은 사용 안 함이다.** 사용자가 리스크를 알고 명시적으로 켜야 동작한다.

| 도구 | 최근 커밋 | 라이선스 | 무엇을 얻나 | 상태 |
|---|---|---|---|---|
| `yt-dlp` | 2026-08-30 | Unlicense | 메타 전체, 댓글(하트·슈퍼챗 금액 포함), 자막 | 열린 이슈 2,644개. SABR과 PO Token 강제로 봇 확인 요구와 403이 빈발. **데이터센터 IP는 사실상 차단** |
| `youtube-comment-downloader` | 2026-07-29 | MIT | cid, text, time, author, channel, votes, replies, photo, heart, paid | 관리는 양호하나 전체 댓글이 다 받아지지 않는다는 보고가 반복된다 |
| `youtube-transcript-api` | 2026-05-13 | MIT | 자동생성 자막 포함 전사, 번역 자막 | **심각.** 일부 영상에서 토큰 요구로 빈 응답이 오고 우회법이 없다. 클라우드 IP는 대부분 차단된다 |
| `pytubefix` | 2026-09-07 | MIT | pytube 호환 API | 유지는 되지만 열린 이슈 대부분이 토큰·403 문제 |

**개인정보 주의**: 댓글 다운로더는 작성자명, 프로필 사진 URL, 채널 ID를 그대로 반환한다. 약관의 개인정보 조항에도 걸린다. 저장할 때 반드시 제거하거나 해시한다.

**자막은 합법 경로가 아예 없다.** 공식 `captions.download`는 영상 소유자 전용이다. 남의 영상 자막이 필요하면 비공식 경로뿐이고, 클라우드에서 실행하면 거의 확실히 실패한다. 로컬이나 주거용 IP를 전제해야 한다.

## 4. 쓰지 않는 것

| 도구 | 이유 |
|---|---|
| `pytube` | 마지막 커밋 2023-05-20. 3년 넘게 방치. 열린 이슈 769개. 현재 동작하지 않는다 |
| `scrapetube` | 유튜브가 렌더러 구조를 바꾼 뒤 깨졌다는 이슈가 2026-05에 올라왔고 댓글 없이 방치돼 있다. 마지막 커밋이 그 이슈보다 앞선다 |
| `youtube-search-python` | 저장소 아카이브됨 |
| `pytrends` | 아카이브됨. 2023-04 이후 방치 |

## 5. 채널 통계 시계열

**과거 시계열을 재현하는 유지보수되는 오픈소스는 확인되지 않았다.**

- Social Blade Business API가 존재하나 가격표가 개발자 대시보드 가입 후에만 공개된다(미검증). 유료 정식 API라 약관 리스크는 없다
- Playboard, NoxInfluencer, vidIQ의 공개 API 유무는 확인하지 못했다(미검증)
- **유일한 합법 자체 구축 경로**는 `channels.list(statistics)`를 매일 스냅샷으로 저장하는 것이다. 단 30일 보관 정책 대상이므로 원본이 아니라 집계 통계로 변환해 보관한다

## 6. 검색량 보조

- **구글 트렌드 공식 API**는 2025-07 발표됐으나 2026-09 현재도 신청 게이트가 걸린 알파다. 대부분 접근할 수 없다
- `pytrends`는 아카이브됐다. 비공식 대안(`trendspy`, `trendspyg`)은 소규모이고 언제든 깨진다
- 한국 시장 검색량은 네이버 데이터랩과 검색광고 키워드도구가 대안이다. 이 스킬에서 별도 검증하지 않았다. `naver-marketing` 스킬을 본다

## 7. 권장 조합

1. 수집 기반은 `google-api-python-client`
2. 채널 영상 순회는 uploads 재생목록 + `playlistItems.list`(1유닛). `search.list` 회피
3. 댓글은 `commentThreads.list` + `comments.list`. 정렬 기준을 기록
4. 형태소는 `kiwipiepy`, 감성은 `daekeun-ml/koelectra-small-v3-nsmc`, 키워드는 KeyBERT
5. 모든 저장 레코드에 `fetched_at`. 30일 갱신·삭제 잡 필수
6. 자막이 꼭 필요하면 비공식 경로를 리스크 고지 후 사용자 승인받고, 실패를 정상 경로로 처리

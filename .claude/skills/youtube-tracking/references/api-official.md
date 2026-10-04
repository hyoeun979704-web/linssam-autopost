# 공식 API: 무엇을 얻고 무엇을 못 얻는가

확인 시점 2026-09-09. 수치와 정책은 바뀐다. 중요한 결정 전에 원문을 다시 본다.

## 0. 세 개의 API를 구분한다

| API | 대상 | 인증 | 용도 |
|---|---|---|---|
| **Data API v3** | 공개 데이터 | API 키 | 남의 채널 포함 모든 공개 지표, 댓글, 메타 |
| **Analytics API** | 본인 채널 | OAuth | 지속률, 인구통계, 도시, 월 집계, 상대 유지 성과 |
| **Reporting API** | 본인 채널 | OAuth | **노출수·클릭률**, 대량 일별 벌크 리포트 |

**둘 중 하나만 붙이는 설계는 실패한다.** 노출수와 클릭률은 Reporting 전용이고, 도시·월 집계·상대 유지 성과는 Analytics 전용이다.

## 1. Data API v3 쿼터

프로젝트당 기본 **10,000 유닛/일**.

| 호출 | 유닛 | 비고 |
|---|---|---|
| `videos.list` | 1 | part를 여러 개 넣어도 1 |
| `channels.list` | 1 | |
| `playlistItems.list` | 1 | 페이지당 최대 50 |
| `commentThreads.list` | 1 | 페이지당 최대 100 |
| `comments.list` | 1 | 대댓글용 |
| `search.list` | **100** | 하루 100회면 쿼터 전소 |
| `captions.list` | 50 | |
| `captions.download` | 200 | **영상 소유자만** |

**설계 원칙: `search.list`를 피한다.** 채널의 영상 목록은 채널의 uploads 재생목록 ID를 얻어 `playlistItems.list`로 순회한다. 1유닛으로 50개씩 가져온다. 같은 일을 search로 하면 100배 비싸다.

`search.list`는 결과가 약 500건에서 잘린다고 알려져 있다. 이 상한의 공식 문서 근거는 확인하지 못했다(미검증). 어느 쪽이든 전수 수집 수단으로 쓰지 않는다.

## 2. Data API로 얻는 필드

| 리소스 | part | 주요 필드 |
|---|---|---|
| `videos` | `snippet` | title, description, tags, categoryId, publishedAt, channelId, thumbnails, defaultAudioLanguage |
| | `statistics` | viewCount, likeCount, commentCount (**dislikeCount 없음**) |
| | `contentDetails` | duration, definition, caption(자막 존재 여부), licensedContent |
| | `topicDetails` | topicCategories |
| `channels` | `snippet` | title, description, customUrl, publishedAt, country |
| | `statistics` | subscriberCount(**반올림**), viewCount, videoCount, hiddenSubscriberCount |
| | `contentDetails` | relatedPlaylists.uploads ← 영상 순회의 출발점 |
| `commentThreads` | `snippet` | topLevelComment(textOriginal, textDisplay, authorDisplayName, authorChannelId, likeCount, publishedAt, updatedAt), totalReplyCount |
| `comments` | `snippet` | 대댓글. 필드 동일 |

**댓글 정렬 함정.** API `order` 기본값은 `time`(최신순)이고 웹 UI 기본은 인기순이다. 같은 영상이라도 표본이 달라진다. `relevance`의 랭킹 기준은 비공개 알고리즘이라 그것으로 뽑은 표본은 분포 주장에 쓸 수 없다. **정렬 기준을 결과물에 반드시 명시한다.**

구독자 수는 반올림된다. 세 자리 유효숫자로 내려오므로 소규모 증감 추적에는 쓸 수 없다.

## 3. 본인 채널 전용 지표

모든 Analytics·Reporting 요청은 **데이터를 소유한 채널 또는 콘텐츠 소유자의 인증**을 받아야 한다. 채널 필터를 쓸 때 요청을 승인하는 사용자가 그 채널의 소유자여야 한다.

### 스코프 함정

`reports.query`는 애널리틱스 읽기 권한만으로는 실패한다. 유튜브 읽기 권한도 함께 필요하다. 문서 최상단에 경고로 붙어 있다. **최소 두 개를 요청한다.**

수익 스코프는 채널 리포트에서 무용지물이다. 문서가 명시한다. 추정 수익과 광고 성과 지표는 채널 리포트에서 지원되지 않으며, 따라서 수익 스코프가 채널 리포트의 금액 데이터 접근을 부여하지 않는다. 수익은 콘텐츠 소유자 경로에서만 나온다.

### 노출수·클릭률 (Reporting API 전용)

2026-01-15에 리치 리포트가 신설되면서 생겼다. 그 전에는 스튜디오에서만 볼 수 있었다.

- 리포트: `channel_reach_basic_a1`, `channel_reach_combined_a1`
- 지표: `video_thumbnail_impressions`, `video_thumbnail_impressions_ctr`
- 기본 리포트 차원: date, channel_id, video_id
- 결합 리포트 차원: 위 + traffic_source_type, traffic_source_detail, operating_system, device_type

**노출 카운트 정의**: 썸네일이 1초 넘게 표시되고 화면에서 50% 이상 보일 때 1회로 센다.

Analytics API의 `reports.query` 지표 목록에 클릭률 관련 항목은 없다. 단발 호출로 얻으려는 시도는 실패한다. 벌크 잡을 스케줄해야 한다.

### 시청 지속률

- 필수 조합: 차원에 경과 시간 비율, 필터에 영상 ID **단 하나**
- 지표: audienceWatchRatio, relativeRetentionPerformance, startedWatching, stoppedWatching, totalSegmentImpressions
- 경과 시간 비율은 영상당 100개 데이터 포인트, 0.01~1.0
- **audienceWatchRatio는 1을 넘을 수 있다.** 같은 구간을 반복 시청하면 그렇게 된다
- relativeRetentionPerformance는 0~1. 0.5면 비슷한 길이 영상의 절반보다 낫고 절반보다 못하다
- 데이터 처리에 보통 1~2일 걸린다
- API 문서에 최소 조회수 요건은 없다(미검증). 스튜디오 UI의 하이라이트 기능에 있는 60초·100조회 요건은 API 요건이 아니다

### 인구통계

- 차원: ageGroup, gender. 지표: viewerPercentage
- **비공개·미등록 영상은 트래픽이 아무리 많아도 인구통계가 나오지 않는다.** 임계값 문제가 아니라 절대 규칙이다
- 영상 단위로 집계하면 연령대와 성별이 NULL로 익명화되는 조합이 문서화돼 있다
- 데이터가 비면 기간을 30일 이상으로 늘리거나 필터·분해를 줄이라는 것이 공식 안내다
- **구체적 임계값 수치는 공개되지 않았다.** "조회수 100회 이상", "고유 시청자 50명" 같은 시중 수치는 어떤 공식 문서에서도 확인되지 않는다(미검증)
- 2026-03-09부터 연령대에 18세 미만 추정 사용자가 포함된다

### 문서화된 하드 한도

| 제약 | 값 |
|---|---|
| 트래픽 소스 리포트 | **영상 수 × 날짜 수 ≤ 50,000**. 초과 시 에러 |
| 영상·재생목록·채널 필터 | 최대 500개 ID |
| 애널리틱스 그룹 | 최대 500개 항목 |
| maxResults | 인기 영상 200, 도시별 활동 250, 일부 트래픽 소스 상세 25 (모두 정렬 필수) |
| 지속률 | 영상 ID 단 하나 |
| province 차원 | **미국 주만**. 국가 필터가 미국이어야 한다 |

500개 영상을 트래픽 소스로 보려면 최대 100일이다. 코드에서 사전 검증해 청크로 쪼갠다.

## 4. 조회수 정의 변경 — 시계열이 끊기는 지점

| 날짜 | 변경 |
|---|---|
| 2025-04-24 | 타깃 쿼리에 쇼츠 조회수 반영. 참여 조회수 지표 도입 |
| 2025-06-24 | 벌크 리포트에 쇼츠 반영. 조회수 포함 리포트 버전이 전부 올라감(`_a2` → `_a3`), 구버전 2025-09-30 종료 |
| **2026-08-27** | 조회수 정의 통일. **조회수는 첫 프레임 재생 기준으로 변경**, **참여 조회수는 불변**, 노출은 불변 |

**기본 지표를 참여 조회수로 잡는다.** 두 차례 정의 변경을 피해 가는 유일한 축이다. 조회수를 써야 하면 2025-04-30과 2026-08-27 경계를 걸치는 구간에 단절 표시를 넣는다.

## 5. 조용히 실패하는 것

- **콘텐츠 소유자의 도시별 활동 리포트는 2026-06-25부터 빈 결과를 반환한다.** 에러가 아니라 빈 결과다. 코드가 성공으로 판단한다
- **`isCurated` 차원은 2025-04-22에 완전히 제거됐다.** 쓰면 하드 실패한다
- Reporting API는 지표가 없는 행을 아예 생략한다. 조회수 0인 국가는 행 자체가 없다. 0으로 채우려면 클라이언트가 채워야 한다

## 6. Analytics와 Reporting의 실무 차이

| 항목 | Analytics | Reporting |
|---|---|---|
| 열거값 | 텍스트 | **정수**. 매핑 필요 |
| 필터링 | 서버측 | **미지원**. 클라이언트가 구현 |
| 정렬 | 지원, 최대 200행 | 미지원 |
| 기간 단위 | 월 집계 가능 | **일 단위만** |
| 차원 이름 | camelCase | **snake_case** |
| 빈 행 | 포함 | 생략 |
| Reporting에 없는 것 | — | 도시, 경과 시간 비율, 월 |

## 7. 추정치와 확정치

- 시청 지표는 이름부터 추정이다
- 수익은 월말 조정 대상이다
- 수익화 재생 지표의 예상 오차는 ±2.0%로 문서화돼 있다
- 확정 수익은 Reporting API의 시스템 관리 리포트에서만 나온다
- 날짜 경계는 태평양시 기준이다. 서머타임 전환일은 23시간 또는 25시간짜리 날이 된다

## 8. 보관 정책

개발자 정책상 저장한 API 데이터는 **30일 내 갱신하거나 삭제**해야 한다. 사용자 삭제 요청 시 **7일 내** 삭제해야 한다.

시계열 대시보드를 만들면 정면으로 부딪힌다. 매일 스냅샷을 쌓는 것이 구독자 이력을 얻는 유일한 합법 경로인데, 그 스냅샷이 30일 정책 대상이다. 집계 통계로 변환해 보관하는 설계가 필요하다(`ethics.md`).

## 9. 미검증 항목

- Analytics·Reporting API의 구체적 일일 할당량 수치. 공식 문서에 수치 테이블이 없다. 문서 간 기술도 상충한다. 실제 코스트는 API 콘솔의 할당량 패널에서 확인해야 한다
- `search.list`의 500건 상한 근거
- 인구통계 임계값 구체 수치
- 지속률 최소 조회수 요건
- Reporting API의 재생목록 지속률 지원 여부. 개요 페이지는 지원한다고 하는데 차원·리포트 문서에는 관련 항목이 하나도 없다. **개요 페이지를 구현 근거로 쓰지 않는다**

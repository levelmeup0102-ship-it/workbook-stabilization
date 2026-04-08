# Refactoring Tracker

> 리팩토링 필요 작업과 고도화로 넘긴 작업을 추적하는 문서입니다.
> 해결된 작업은 날짜별 파일(YYYY-MM-DD.md)로 이동합니다.

---

## 리팩토링 필요 작업 (구현 순서)

### P1 - 긴급 + 높은 영향

#### Phase 1: 즉시 수정 (독립적, 빠르게 가능)

- [x] **APP_PASSWORD 기본값 하드코딩 제거**
  - 현재: main.py: `os.getenv()`삭제
  - 변경: 기본값 제거, 환경변수 필수화 (미설정 시 서버 시작 실패)

- [x] **content_match 정답 셔플 오류 수정** — 코드 확인 결과 이미 (text, is_correct) 쌍 셔플로 구현됨 (수정 불필요)

#### Phase 1.5: 로깅 시스템 구축

- [x] **Simple Loguru 로깅 시스템 구축 (`app/log/`)**
  - app/log/logging.py: setup_logger() — console sink only, 레벨별 색상
  - app/log/events.py: 얇은 로깅 헬퍼 (앱 코드에서 loguru 직접 사용 금지)

- [ ] **커스텀 에러 클래스 + exception handler**
  - 에러 분류가 실제로 필요해지는 시점에 생성 (현재 보류)

- [ ] **BaseModel 기반 API 응답 스키마 (`app/schemas/responses.py`)**
  - HTTP 상태 코드별 구조화된 응답 모델
  - Phase 5에서 각 엔드포인트에 적용

- [x] **환경 변수 관리 (`app/config.py`)**
  - Pydantic BaseSettings + Field로 엄격한 검증 (서버 시작 전 100% 문제 감지)
  - `@lru_cache` 데코레이터로 Singleton 패턴 (잦은 호출 성능 저하 방지)
  - 대상: APP_PASSWORD, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, PORT, ENV
  - 기존 `os.getenv()` 산재 → `get_settings().XXX`로 통일
  - 필수 변수 누락 시 서버 시작 실패 (ValidationError)

#### Phase 2: 데이터 레이어 기반 구축

- [x] **로컬 passages.json 제거 (확정)**
  - Supabase 전용으로 전환
  - `_load_db()`, `_save_db()`의 로컬 JSON 읽기/쓰기 코드 삭제

- [x] **`_load_db()` / `_save_db()` → repository 레이어 분리**
  - 현재: main.py 전역 함수
  - 변경: repositories/ 하위로 이동

- [x] **supa 모듈 의존성 패턴 정리**
  - 현재: 함수 내부에서 `import supa` + try/except 반복
  - 변경: 의존성 주입 또는 모듈 레벨 import로 통일

- [x] **passages 테이블 스키마 변경**
  - 현재: book, unit, pid, title, passage_text
  - 변경: id(PK, auto increment), book_name, unit, lesson(구 pid), english_text, korean_translation, updated_at
  - title 컬럼 삭제 (프론트에서 unit+lesson 조합 표시), korean_translation 컬럼 추가

- [ ] **중첩 dict → flat row 구조 전환**
  - 현재: `db["books"][book]["units"][unit]["passages"][pid]` (3단계 중첩)
  - 변경: flat row 리스트 (`[{book_name, unit, lesson, ...}, ...]`)
  - `_load_db()`, `_save_db()`, 모든 엔드포인트에서 접근 패턴 변경

- [ ] **workbook_contents 테이블 신규 생성 (step_cache 대체)**
  - 컬럼: id(PK), passage_id(FK → passages.id), stage_name, workbook_data(JSON), updated_at
  - 기존 step_cache 테이블 미사용
  - updated_at 기반 유효성 검증: 생성 시작 시 pu_snapshot 저장 → 완료 시 pu_current 비교
  - passage 단위 비교 (지문 변경 시 전체 stage 재생성)
  - 생성 중 지문 수정 대응: 워크북은 정상 저장, 변경 시에만 응답에 `passage_changed: true` 포함 → 프론트에서 재생성 여부 confirm

#### Phase 3: API 클라이언트 교체

- [ ] **curl subprocess → anthropic SDK 또는 httpx 교체**
  - 현재 pipeline.py에서 curl로 Claude API 호출 중
  - Claude 관련 코드는 `app/services/claude/` 하위로 분리
    - `client.py`: call_claude(), call_claude_json()
    - `json_parser.py`: _parse_json_robust(), _fix_json_quotes() (방어 코드로 유지)

- [ ] **requirements.txt에 anthropic SDK 추가**
  - curl → SDK 교체 시 함께 처리

#### Phase 4: Pipeline 재구성

- [ ] **pipeline 전역변수 경로 주입 제거**
  - 현재: main.py에서 `pl.DATA_DIR = ...` 식으로 덮어쓰기 (507-510행)
  - CLI 코드 삭제 후 불필요. 함수 인자로 전달하는 방식으로 변경

- [ ] **Step → Stage 재구성**
  - Claude 호출을 stage별로 분리 (최대 8회, 최소 0회)
  - Stage 1(어휘), 5(순서), 6(빈칸), 7(주제), 8-1(어법괄호), 8-2(어법서술), 9-1(어휘심화), 9-2(내용일치)
  - Stage 2,3,4,10은 DB + 로컬 처리 (Claude 호출 0회)

- [ ] **extract_base_data() (기존 step1) 제거**
  - sentences: split_sentences() regex로 로컬 처리
  - translation, sentence_translations: 업로드 시 영문+해석 분리 저장
  - key_sentences: Stage 4 관련 처리로 이동

- [ ] **step1_basic_analysis() 프롬프트에서 translation, sentences, sentence_translations 제외**

- [ ] **test_a/b/c 코드에서 알고리즘으로 생성 전환 + 정답도 같이 자동 생성**
  - vocab 14개에서 코드로 랜덤 추출 (셔플 → 슬라이싱)
  - 정답: vocab의 meaning/synonyms/word 매칭으로 자동 생성
  - step1 Claude 프롬프트에서 test_a/b/c 항목 제거

- [ ] **step5(어법), step6(어휘+내용일치) 분리**
  - step5 → stage8_bracket + stage8_error
  - step6 → stage9_vocab + stage9_content_match

#### Phase 5: API 레이어 정비

- [ ] **업로드 시 english_text + korean_translation 분리 파싱**
  - 현재: `###제목###` 구분자로 제목+지문만 파싱
  - 변경: 영문 지문과 한글 해석을 분리하여 저장

- [ ] **DELETE 엔드포인트 RESTful 재설계 (방안 A 확정)**
  - `DELETE /api/passages/books/{book_name}` → 교재 삭제
  - `DELETE /api/passages/units/{book_name}/{unit}` → 단원 삭제
  - `DELETE /api/passages/{book_name}/{unit}/{lesson}` → 강/과 삭제
  - 내부: repository.delete() 공통 함수 1개로 쿼리 재사용
  - 기존 `DELETE /api/books` 제거 (passages로 통합)

- [ ] **`POST /api/clear-cache` 엔드포인트 삭제**
  - 캐싱 전략 제거에 따라 불필요

- [ ] **`POST /api/sync-supabase` 엔드포인트 삭제**
  - 로컬 JSON 이중 저장 제거에 따라 불필요

- [ ] **Pydantic schema 적용 (Request body 유효성 검증)**
  - 현재: `await request.json()`으로 직접 파싱, 유효성 검증 없음
  - 변경: BaseModel로 타입/필수값 검증

- [ ] **GET /api/passages 응답에서 title, cache_status 제거**
  - title: 스키마에서 삭제 예정
  - cache_status: 캐싱 전략 제거로 불필요

- [ ] **API 응답 포맷 표준화**
  - 현재: 엔드포인트마다 응답 형식 제각각, HTTP 상태 코드 미활용
  - 변경: 공통 응답 스키마 (BaseModel) + 적절한 HTTP 상태 코드 반환

#### Phase 6: 비동기 전환

- [ ] **`_run_async()` 우회 패턴 제거 + pipeline async 전환 + 병렬 처리**
  - 현재: sync 함수에서 async supa 호출을 위해 ThreadPoolExecutor 사용 (234-246행)
  - process_passage()가 sync → main.py의 async `/generate`에서 이벤트 루프 블로킹
  - pipeline을 async로 전환하면 `_run_async()` 제거 가능
  - 독립 stage 간 병렬 실행 (asyncio.gather 등)
  - 업로드/삭제/생성 간 동시성 제어 (race condition 방지)

### P2 - 보통 긴급성 + 보통 영향

- [ ] **캐싱 전략 전환 (파일/step_cache → updated_at 기반)**
  - 로컬 캐싱(step*.json 파일) 제거
  - Supabase step_cache 테이블 미사용 → workbook_contents로 대체
  - `_ck()`, `_is_cached()`, `save_step()`, `load_step()` 함수 제거
  - supa.py의 step_cache 관련 함수 제거
  - sitecustomize.py: anthropic SDK 교체 후 필요 여부 확인

- [ ] **merge_to_template_data() 제거**
  - 각 stage 함수가 템플릿 키 이름으로 직접 반환
  - orchestrator에서 template_data.update()로 누적

- [ ] **프롬프트 관리 체계화**
  - Python 파일로 관리 (f-string 변수 삽입)
  - 위치: `app/services/pipeline/prompts/` (pipeline 하위)
  - stage별 파일: stage1_vocab.py, stage5_order.py, stage6_blank.py 등
  - Claude 응답도 BaseModel/RootModel로 구조 검증

- [ ] **검증/재시도 로직 공통화**
  - **Supabase 통신**
    - 네트워크 오류/타임아웃: 최대 3회 재시도
    - 인증 실패 (401): 즉시 중단
    - Rate limit (429): 백오프 후 재시도
  - **Claude API 호출**
    - 네트워크 오류/타임아웃: 최대 3회 재시도
    - Rate limit (429): 백오프 후 재시도
    - Context length 초과: 즉시 중단 (재시도 무의미)
    - 응답 JSON 파싱 실패: 1회 재시도
  - **기존 pipeline 재시도 (제각각 → 통일)**
    - step2(468-486행): 블록수 불일치 → 1회 재시도 → 원문 폴백
    - step5(616-626행): 문장수 체크 → 1회 재시도 → 끝
    - step6(681-692행): 10개 미만 → 1회 재시도 → 부분 교체
  - 제각각인 패턴을 데코레이터 또는 wrapper로 통일

- [ ] **전체 프롬프트 점검: 코드로 처리 가능한 항목을 Claude에게 요청하고 있는지 확인**
  - step1에서 test_a/b/c 발견 → 코드 전환 확정
  - step2~7 프롬프트도 동일 패턴 점검 필요
  - 코드 처리 가능 항목은 프롬프트에서 제거 → API 비용 절감 + 실패 가능성 감소
  - ⚠️ 프롬프트 관리 체계화 + 검증/재시도 공통화 완료 후 진행

- [ ] **XSS 취약점 수정 (index.html)**
  - p.title, p.unit, p.id 등이 이스케이프 없이 HTML에 삽입 (355-365행)
  - 변경: textContent 사용 또는 이스케이프 함수 적용

- [ ] **CORS allow_origins 제한**
  - 현재: main.py:30 `allow_origins=["*"]` (모든 도메인 허용)
  - 변경: 환경변수로 허용 도메인 설정 (프로덕션에서 특정 도메인만)

- [ ] **입력값 길이 제한 + book 경로 탐색 방지**
  - 프론트: 교재명, 지문 텍스트 등 길이 상한선 설정
  - 백엔드: Pydantic schema에서 max_length 검증
  - book에 `../` 등 경로 문자 검증 (화이트리스트: 알파벳/숫자/한글/공백만 허용)
  - ⚠️ P1 Phase 5의 Pydantic 적용과 연동

- [ ] **except Exception 남용 수정 + silent failure 제거**
  - main.py 71,141,151,188행 등: 예외 타입 구분 없이 print()만
  - 변경: 예외 타입별 분기 + logging 모듈 사용

- [ ] **supa.py JSON 파싱 에러 처리 추가**
  - 42행: json.loads(raw) 실패 시 crash 가능
  - 변경: try-except 감싸기 + 명시적 에러 반환

- [ ] **삭제 작업 원자성 보장**
  - main.py 287-351행: 로컬 삭제 → Supabase 삭제 순서, 중간 실패 시 불일치
  - 변경: Supabase 전용 전환 후 트랜잭션 또는 롤백 처리

- [ ] **경로 처리 일관성 확보**
  - main.py 24-25,162,508행: 절대/상대 경로 혼용
  - 변경: `__file__` 기준 절대 경로로 통일

- [ ] **JSON 파싱 탐욕적 매칭 수정 (pipeline.py)**
  - 174-198행: `\{[\s\S]*\}`가 다중 객체에서 오작동 가능
  - 변경: 중괄호 스택 기반 파싱 또는 첫 번째 완전한 객체만 추출

- [ ] **requirements.txt 버전 고정**
  - 현재: `fastapi`, `uvicorn` 등 버전 미지정
  - 변경: `fastapi==0.x.x` 형태로 고정 (배포 재현성 보장)

- [ ] **Dockerfile/nixpacks.toml에서 curl 패키지 제거**
  - P1 Phase 3 SDK 전환 후 불필요

### P3 - 낮은 긴급성 + 경미한 영향

- [ ] **step8_answers → Jinja2 이전 + 정답 개선**
  - Python에서 HTML 조립하는 방식 → template.html에서 Jinja2로 렌더링
  - step8_answers 함수 삭제, 데이터만 템플릿에 전달
  - Stage 1 어휘 테스트: 하드코딩 문구 → vocab 데이터에서 word/meaning 매칭하여 정답 기입

- [ ] **토큰 만료 처리 일관화 (index.html)**
  - 현재: /api/passages만 401 처리, 다른 API(deletePassage 등)는 미처리
  - 변경: 모든 fetch 호출에 공통 401 처리 적용

- [ ] **인증 실패 메시지 통일**
  - 현재: main.py:204-209 "wrong password"로 비밀번호 필드 존재 노출
  - 변경: "Authentication failed"로 통일 (공격자에게 힌트 차단)

- [ ] **캐시 로드 후 필드 검증 추가**
  - pipeline.py 303-306행: 손상된 캐시 반환 시 downstream KeyError
  - 변경: 캐시 로드 후 필수 필드 존재 여부 검증
  - ⚠️ P2 캐싱 전략 전환 전까지만 유효

- [ ] **임시 파일 정리 보장 (pipeline.py)**
  - 107-125행: curl 호출용 tempfile이 실패 시 남음
  - 변경: finally 블록에서 안전하게 정리
  - ⚠️ P1 Phase 3 SDK 전환 후 자연 해소

- [ ] **template.html CSS 클래스명과 정의 불일치 수정**
  - `il--w70`, `il--h13` 등 클래스 사용 중 CSS 정의 없음
  - 변경: 미사용 클래스 제거 또는 CSS 정의 추가

- [ ] **CMD/시작 명령 통일**
  - Dockerfile:8-9 주석 처리된 CMD와 실제 CMD 혼재
  - Procfile은 `uvicorn main:app`, Dockerfile은 `python main.py`
  - 변경: 하나로 통일

- [ ] **.gitignore에 프로젝트 고유 경로 추가**
  - `data/`, `output/` 등 런타임 생성 디렉토리 추가

- [ ] **max_tokens 최적화**
  - 기존 값 유지, 문제 발견 시 alert 요청

---

## 미결 사항

- [x] orchestrator.py → `workbook_service.py` 확정
- [x] step8_answers → Jinja2 이전 확정 + vocab 정답 기입
- [x] 프롬프트 구조 → `app/services/pipeline/prompts/` 하위 stage별 파일
- [x] 타입체크 → BaseModel/RootModel 사용 확정
- [x] passages.json → 삭제 확정 (Supabase 전용)
- [x] step2(stage1 어휘 테스트) 답안 매칭 → DB 조회 불필요, vocab에서 코드로 매칭 (비용 0)
- [x] 전체 프로젝트 파일 전수 점검 완료 (2026-03-27)
- [x] 로깅 시스템 구축 범위/방식 확정 → P1 Phase 1.5로 등록 (구조화된 로깅 + BaseModel 응답 스키마 + 커스텀 에러)
- [ ] 로깅 시스템 프레임 계획한 파일 첨부하여, 로깅 시스템 구현 기획 진행하기

---

## 고도화로 넘긴 작업

- [ ] 다중 사용자 환경에서 사용자별 데이터 분리
- [ ] 프롬프트를 비개발자도 수정 가능한 형태로 전환 (현재는 Python 파일)
- [ ] 프론트엔드에서 지문 등록/수정 UI 분리 (현재는 upsert 통합 처리)
- [ ] loadPassages() 다중 사용자 환경 고려한 재조회 정책
- [ ] stage 8-1/8-2 참조용 파일 추가 (어법 문제 참조 파일)
- [ ] 프론트엔드 CSS 분리 (index.html → css/index.css)
  - JS 분리는 현재 불필요 (페이지 1개, JS 700줄, 한 파일 관리 가능)
  - JS 분리 시점: 코드 1500줄 이상 또는 페이지 추가 시
- [ ] template.html CSS 분리
- [ ] 생성 작업 타임아웃/취소 기능 (process_passage에 타임아웃, 사용자 중단 UI)
- [ ] API 재시도 전략 고도화 (에러 타입별 분기: rate_limit → 백오프, context_length → 프롬프트 단축 등)
- [ ] 설정 관리 중앙화 (model, max_tokens 등 상수를 config 파일로 외부화)
- [ ] 진행 상황 세분화 (stage별 프로그레스 바, 예상 완료 시간)
- [ ] 업로드 형식 프리뷰 (파싱 결과 미리보기 후 저장)
- [ ] 지문 검색 기능 (교재/단원 외에 텍스트 검색)
- [ ] PWA 아이콘 512px 추가 (manifest.json)
- [ ] dev/staging/prod 환경 분리 (Railway 환경 단위 활용, 변수·설정 환경별 분리)
- [ ] 시크릿 정기 교체 체계 (JWT_SECRET, 서드파티 API 키, DB 비밀번호 등)
- [ ] 구조화된 로깅 시스템 고도화 (Simple Loguru → 본격 전환)
  - 구조화된 JSON 로그 (Prod: INFO 이상, stdout)
  - 요청/응답 미들웨어 (method, path, status, time)
  - Claude API 호출 로그 (stage명, 소요 시간, 재시도, 성공/실패)
  - 기존 print(), _safe_print() 일괄 제거 후 loguru 전환
  - Pydantic 이벤트 기반으로 events.py 내부 전환
  - 커스텀 에러 클래스 + exception handler (에러→HTTP 매핑)

---

*마지막 업데이트: 2026-04-03*

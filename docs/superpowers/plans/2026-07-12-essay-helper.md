# 에세이 첨삭 도우미 (essay_helper) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 에세이 초안 + 선택한 지침으로 첨삭 프롬프트를 생성·복사하고, AI 결과물을 원문과 비교·localStorage에 저장하는 정적 웹앱.

**Architecture:** 서버·빌드 도구 없는 순수 정적 웹앱. 프롬프트 조립(`buildPrompt`)과 히스토리 로직(`history.js`)은 DOM 없는 순수 모듈로 분리해 `node:test`로 단위 테스트하고, `app.js`는 DOM 배선만 담당한다. blog_widget_maker와 동일한 패턴.

**Tech Stack:** HTML + CSS + 바닐라 JS(ESM), `node --test` (Node 내장 테스트 러너), localStorage.

**스펙 대비 구조 변경 1건:** 스펙 3.3은 `buildPrompt`를 `app.js`에 두라고 했으나, DOM 코드가 섞인 `app.js`는 Node 테스트에서 import할 수 없다. blog_widget_maker의 `widget-templates.js` 패턴을 따라 `prompt-builder.js`(순수 함수)와 `history.js`(스토리지 주입형)로 분리한다. 스펙의 의도(순수 함수 + 단위 테스트)를 지키기 위한 변경.

## Global Constraints

- 외부 의존성 금지: 프레임워크·CDN·API 호출 없음. 모든 코드는 `essay_helper/` 폴더 내 순수 JS
- localStorage 키는 정확히 `essay_helper_history`
- 히스토리 항목 스키마: `{ id, date, title, original, result, options }` (title = 원문 첫 줄 30자)
- 스타일 지침 id 4종: `psychology`, `hooking`, `warmth`, `worker`
- 플랫폼 id 4종: `naver`, `brunch`, `instagram`, `general` — 플랫폼 미선택 시 `general` 가이드로 동작
- 커밋 메시지는 기존 컨벤션대로 `feat(essay_helper): ...` 형식의 한국어
- 테스트 실행은 `essay_helper/` 디렉터리에서 `node --test tests/`

## File Structure

```
essay_helper/
  index.html          — 페이지 마크업 (Task 3)
  style.css           — 스타일 (Task 3)
  prompts.js          — 지시문 데이터만 (Task 1)
  prompt-builder.js   — buildPrompt 순수 함수 (Task 1)
  history.js          — localStorage 히스토리 로직, storage 주입형 (Task 2)
  app.js              — DOM 배선·상태·이벤트 (Task 4)
  package.json        — { "type": "module" } (Task 1)
  tests/
    prompt-builder.test.js  (Task 1)
    history.test.js         (Task 2)
```

---

### Task 1: 프롬프트 데이터 + buildPrompt 순수 함수

**Files:**
- Create: `essay_helper/package.json`
- Create: `essay_helper/prompts.js`
- Create: `essay_helper/prompt-builder.js`
- Test: `essay_helper/tests/prompt-builder.test.js`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `prompts.js`: `export const ROLE_PREAMBLE /* string */`, `export const STYLE_GUIDES /* { [id]: { label: string, text: string } } */`, `export const PLATFORM_GUIDES /* 동일 구조 */`
  - `prompt-builder.js`: `export function buildPrompt({ original, styles = [], situation = '', platforms = [] }): string`

- [ ] **Step 1: package.json 생성**

`essay_helper/package.json`:

```json
{
  "name": "essay-helper",
  "private": true,
  "type": "module"
}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`essay_helper/tests/prompt-builder.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPrompt } from '../prompt-builder.js';
import { ROLE_PREAMBLE, STYLE_GUIDES, PLATFORM_GUIDES } from '../prompts.js';

test('항상 역할 정의(ROLE_PREAMBLE)로 시작한다', () => {
  const prompt = buildPrompt({ original: '내 에세이' });
  assert.ok(prompt.startsWith(ROLE_PREAMBLE));
});

test('원문이 프롬프트 말미에 구분자와 함께 포함된다', () => {
  const prompt = buildPrompt({ original: '오늘 퇴근길에 문득 생각했다.' });
  assert.ok(prompt.endsWith('원문:\n"""\n오늘 퇴근길에 문득 생각했다.\n"""'));
});

test('선택한 스타일 지침만 포함된다', () => {
  const prompt = buildPrompt({ original: '글', styles: ['psychology', 'worker'] });
  assert.ok(prompt.includes(STYLE_GUIDES.psychology.text));
  assert.ok(prompt.includes(STYLE_GUIDES.worker.text));
  assert.ok(!prompt.includes(STYLE_GUIDES.hooking.text));
  assert.ok(!prompt.includes(STYLE_GUIDES.warmth.text));
});

test('스타일을 하나도 선택하지 않으면 스타일 지침 섹션이 없다', () => {
  const prompt = buildPrompt({ original: '글', styles: [] });
  assert.ok(!prompt.includes('스타일 지침:'));
});

test('알 수 없는 스타일 id는 무시한다', () => {
  const prompt = buildPrompt({ original: '글', styles: ['nonsense'] });
  assert.ok(!prompt.includes('스타일 지침:'));
});

test('상황 텍스트를 입력하면 상황 설정 섹션에 반영된다', () => {
  const prompt = buildPrompt({ original: '글', situation: '이직을 고민하는 후배에게 하는 말처럼' });
  assert.ok(prompt.includes('상황 설정:\n- 이직을 고민하는 후배에게 하는 말처럼'));
});

test('상황 텍스트가 공백뿐이면 상황 설정 섹션이 없다', () => {
  const prompt = buildPrompt({ original: '글', situation: '   ' });
  assert.ok(!prompt.includes('상황 설정:'));
});

test('선택한 플랫폼 가이드가 모두 포함된다', () => {
  const prompt = buildPrompt({ original: '글', platforms: ['naver', 'brunch'] });
  assert.ok(prompt.includes(PLATFORM_GUIDES.naver.text));
  assert.ok(prompt.includes(PLATFORM_GUIDES.brunch.text));
  assert.ok(!prompt.includes(PLATFORM_GUIDES.instagram.text));
});

test('플랫폼 미선택 시 general 가이드가 기본으로 들어간다', () => {
  const prompt = buildPrompt({ original: '글', platforms: [] });
  assert.ok(prompt.includes(PLATFORM_GUIDES.general.text));
});
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run (in `essay_helper/`): `node --test tests/`
Expected: FAIL — `Cannot find module ... prompt-builder.js`

- [ ] **Step 4: prompts.js 작성 (데이터만, 로직 없음)**

`essay_helper/prompts.js`:

```js
export const ROLE_PREAMBLE = `당신은 에세이 첨삭 전문가입니다. 아래 원문 에세이를 지침에 따라 수정·보완해 주세요.

공통 원칙:
- 원문의 경험과 핵심 메시지는 그대로 유지하고, 표현과 구성만 다듬습니다.
- 글쓴이의 목소리와 어투를 지우지 않습니다.
- 결과는 수정된 에세이 전문만 출력합니다(설명이나 주석 없이).`;

export const STYLE_GUIDES = {
  psychology: {
    label: '심리·철학 쉽게 풀기',
    text: '- 심리학·철학 개념이 나오면 전문용어 대신 일상 언어와 생활 속 비유로 쉽게 풀어 씁니다.',
  },
  hooking: {
    label: '후킹 문구로 맛깔스럽게',
    text: '- 에피소드 도입부에 궁금증을 일으키는 후킹 문구를 넣고, 밋밋한 서술은 장면이 그려지듯 생동감 있게 다듬습니다.',
  },
  warmth: {
    label: '따뜻한 위로·용기·희망',
    text: '- 글 전체에 따뜻한 위로와 용기, 희망이 느껴지는 긍정적인 톤을 유지하고, 마무리에 여운을 남깁니다.',
  },
  worker: {
    label: '직장인 공감',
    text: '- 직장인이 "내 얘기네" 하고 공감할 수 있는 디테일(출퇴근, 회의, 상사·동료 관계, 점심시간 등)을 살립니다.',
  },
};

export const PLATFORM_GUIDES = {
  naver: {
    label: '네이버 블로그',
    text: '- 네이버 블로그용: 한 문단은 2~3문장으로 짧게 끊고, 가독성을 최우선으로, 흐름이 바뀌는 곳에는 소제목을 답니다.',
  },
  brunch: {
    label: '브런치',
    text: '- 브런치용: 에세이 톤의 긴 호흡을 살리고, 문학적인 문체로 씁니다.',
  },
  instagram: {
    label: '인스타그램',
    text: '- 인스타그램용: 짧은 호흡의 카드뉴스형 문장으로 쓰고, 줄바꿈을 자주 사용합니다.',
  },
  general: {
    label: '일반',
    text: '- 특정 플랫폼에 매이지 않는 일반적인 에세이 스타일로 씁니다.',
  },
};
```

- [ ] **Step 5: prompt-builder.js 작성**

`essay_helper/prompt-builder.js`:

```js
import { ROLE_PREAMBLE, STYLE_GUIDES, PLATFORM_GUIDES } from './prompts.js';

export function buildPrompt({ original, styles = [], situation = '', platforms = [] }) {
  const sections = [ROLE_PREAMBLE];

  const styleTexts = styles
    .filter((id) => STYLE_GUIDES[id])
    .map((id) => STYLE_GUIDES[id].text);
  if (styleTexts.length > 0) {
    sections.push('스타일 지침:\n' + styleTexts.join('\n'));
  }

  const trimmedSituation = situation.trim();
  if (trimmedSituation) {
    sections.push('상황 설정:\n- ' + trimmedSituation);
  }

  const platformIds = platforms.filter((id) => PLATFORM_GUIDES[id]);
  const effectivePlatforms = platformIds.length > 0 ? platformIds : ['general'];
  sections.push(
    '형식 가이드:\n' + effectivePlatforms.map((id) => PLATFORM_GUIDES[id].text).join('\n')
  );

  sections.push('원문:\n"""\n' + original + '\n"""');

  return sections.join('\n\n');
}
```

- [ ] **Step 6: 테스트 통과 확인**

Run (in `essay_helper/`): `node --test tests/`
Expected: PASS — 9 tests pass

- [ ] **Step 7: 커밋**

```bash
git add essay_helper/package.json essay_helper/prompts.js essay_helper/prompt-builder.js essay_helper/tests/prompt-builder.test.js
git commit -m "feat(essay_helper): 프롬프트 지시문 데이터 및 buildPrompt 조립 함수 추가"
```

---

### Task 2: localStorage 히스토리 모듈

**Files:**
- Create: `essay_helper/history.js`
- Test: `essay_helper/tests/history.test.js`

**Interfaces:**
- Consumes: 없음 (독립 모듈, storage는 인자로 주입 — 브라우저에선 `window.localStorage`, 테스트에선 fake)
- Produces:
  - `export const HISTORY_KEY = 'essay_helper_history'`
  - `export function makeTitle(original: string): string` — 첫 줄 30자, 빈 문자열이면 `'(제목 없음)'`
  - `export function loadHistory(storage): Array<Entry>` — 파싱 실패·비배열이면 `[]`
  - `export function saveEntry(storage, { original, result, options }): Entry` — 새 항목을 맨 앞에 추가. storage 쓰기 실패(용량 초과)는 그대로 throw — 호출자(app.js)가 처리
  - `export function deleteEntry(storage, id): Array<Entry>` — 삭제 후 남은 배열 반환
  - `Entry = { id: string, date: string(ISO), title: string, original: string, result: string, options: { styles: string[], situation: string, platforms: string[] } }`

- [ ] **Step 1: 실패하는 테스트 작성**

`essay_helper/tests/history.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HISTORY_KEY, makeTitle, loadHistory, saveEntry, deleteEntry } from '../history.js';

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    _dump: () => data,
  };
}

test('HISTORY_KEY는 스펙에 정의된 키와 일치한다', () => {
  assert.equal(HISTORY_KEY, 'essay_helper_history');
});

test('makeTitle은 원문 첫 줄을 30자로 자른다', () => {
  const long = '가'.repeat(50) + '\n둘째 줄';
  assert.equal(makeTitle(long), '가'.repeat(30));
  assert.equal(makeTitle('짧은 제목\n본문'), '짧은 제목');
});

test('makeTitle은 빈 원문에 (제목 없음)을 반환한다', () => {
  assert.equal(makeTitle(''), '(제목 없음)');
  assert.equal(makeTitle('   \n   '), '(제목 없음)');
});

test('loadHistory는 저장된 것이 없으면 빈 배열을 반환한다', () => {
  assert.deepEqual(loadHistory(fakeStorage()), []);
});

test('loadHistory는 깨진 JSON이나 비배열 값에도 빈 배열을 반환한다', () => {
  assert.deepEqual(loadHistory(fakeStorage({ [HISTORY_KEY]: '{깨진 json' })), []);
  assert.deepEqual(loadHistory(fakeStorage({ [HISTORY_KEY]: '"문자열"' })), []);
});

test('saveEntry는 항목을 맨 앞에 추가하고 저장한다', () => {
  const storage = fakeStorage();
  const options = { styles: ['warmth'], situation: '', platforms: ['naver'] };
  saveEntry(storage, { original: '첫 글\n본문', result: '결과1', options });
  const second = saveEntry(storage, { original: '둘째 글', result: '결과2', options });

  const entries = loadHistory(storage);
  assert.equal(entries.length, 2);
  assert.equal(entries[0].id, second.id);
  assert.equal(entries[0].title, '둘째 글');
  assert.equal(entries[1].title, '첫 글');
  assert.equal(entries[0].result, '결과2');
  assert.deepEqual(entries[0].options, options);
  assert.ok(entries[0].id !== entries[1].id);
  assert.ok(!Number.isNaN(Date.parse(entries[0].date)));
});

test('deleteEntry는 해당 id만 제거한다', () => {
  const storage = fakeStorage();
  const opts = { styles: [], situation: '', platforms: [] };
  const a = saveEntry(storage, { original: 'A', result: '', options: opts });
  const b = saveEntry(storage, { original: 'B', result: '', options: opts });

  const remaining = deleteEntry(storage, a.id);
  assert.equal(remaining.length, 1);
  assert.equal(remaining[0].id, b.id);
  assert.equal(loadHistory(storage).length, 1);
});

test('saveEntry는 storage 쓰기 실패를 그대로 던진다', () => {
  const storage = {
    getItem: () => null,
    setItem: () => { throw new Error('QuotaExceededError'); },
  };
  assert.throws(
    () => saveEntry(storage, { original: 'X', result: '', options: { styles: [], situation: '', platforms: [] } }),
    /QuotaExceededError/
  );
});
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run (in `essay_helper/`): `node --test tests/`
Expected: FAIL — `Cannot find module ... history.js` (Task 1 테스트 9개는 PASS)

- [ ] **Step 3: history.js 작성**

`essay_helper/history.js`:

```js
export const HISTORY_KEY = 'essay_helper_history';

const MAX_TITLE_LENGTH = 30;

export function makeTitle(original) {
  const firstLine = original.trim().split('\n')[0].trim();
  return firstLine.slice(0, MAX_TITLE_LENGTH) || '(제목 없음)';
}

export function loadHistory(storage) {
  try {
    const raw = storage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveEntry(storage, { original, result, options }) {
  const entries = loadHistory(storage);
  const entry = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    date: new Date().toISOString(),
    title: makeTitle(original),
    original,
    result,
    options,
  };
  entries.unshift(entry);
  storage.setItem(HISTORY_KEY, JSON.stringify(entries));
  return entry;
}

export function deleteEntry(storage, id) {
  const entries = loadHistory(storage).filter((e) => e.id !== id);
  storage.setItem(HISTORY_KEY, JSON.stringify(entries));
  return entries;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run (in `essay_helper/`): `node --test tests/`
Expected: PASS — 17 tests pass (Task 1의 9개 + 이번 8개)

- [ ] **Step 5: 커밋**

```bash
git add essay_helper/history.js essay_helper/tests/history.test.js
git commit -m "feat(essay_helper): localStorage 히스토리 모듈 추가"
```

---

### Task 3: 페이지 마크업 + 스타일

**Files:**
- Create: `essay_helper/index.html`
- Create: `essay_helper/style.css`

**Interfaces:**
- Consumes: 없음 (정적 마크업 — 체크박스는 Task 4의 app.js가 `STYLE_GUIDES`/`PLATFORM_GUIDES`로부터 렌더링하므로 fieldset은 비워 둠)
- Produces: Task 4의 app.js가 참조하는 DOM id들 — `original-input`, `char-count`, `style-options`, `situation-input`, `platform-options`, `generate-btn`, `prompt-output-wrap`, `prompt-output`, `copy-btn`, `copy-status`, `result-input`, `compare-grid`, `compare-original`, `compare-result`, `save-btn`, `save-status`, `history-list`, `history-empty`

- [ ] **Step 1: index.html 작성**

`essay_helper/index.html`:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>에세이 첨삭 도우미</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="app-header">
    <h1>에세이 첨삭 도우미</h1>
    <p class="tagline">초안을 붙여넣고 지침을 고르면, AI에게 건넬 첨삭 프롬프트를 만들어 드려요.</p>
  </header>

  <main>
    <section class="card" id="input-section">
      <h2>1. 초안 붙여넣기</h2>
      <textarea id="original-input" rows="12"
        placeholder="에세이 초안을 붙여넣거나 작성하세요..."></textarea>
      <div class="char-count"><span id="char-count">0</span>자</div>
    </section>

    <section class="card" id="options-section">
      <h2>2. 지침 선택</h2>
      <fieldset id="style-options">
        <legend>스타일 지침</legend>
        <!-- app.js가 STYLE_GUIDES로부터 체크박스를 렌더링 -->
      </fieldset>
      <fieldset>
        <legend>상황 제시 (선택)</legend>
        <input type="text" id="situation-input"
          placeholder="예: 이직을 고민하는 후배에게 하는 말처럼">
      </fieldset>
      <fieldset id="platform-options">
        <legend>발행 플랫폼</legend>
        <!-- app.js가 PLATFORM_GUIDES로부터 체크박스를 렌더링 -->
      </fieldset>
    </section>

    <section class="card" id="prompt-section">
      <h2>3. 프롬프트 생성</h2>
      <button id="generate-btn" class="primary" disabled>프롬프트 생성</button>
      <p class="hint">초안을 입력하면 버튼이 활성화됩니다.</p>
      <div id="prompt-output-wrap" hidden>
        <textarea id="prompt-output" rows="10" readonly></textarea>
        <div class="row">
          <button id="copy-btn" class="primary">복사</button>
          <span id="copy-status" role="status"></span>
        </div>
        <p class="hint">복사한 프롬프트를 ChatGPT나 Claude에 붙여넣으세요.</p>
      </div>
    </section>

    <section class="card" id="compare-section">
      <h2>4. 결과 비교</h2>
      <textarea id="result-input" rows="8"
        placeholder="AI가 첨삭한 결과를 붙여넣으세요..."></textarea>
      <div class="compare-grid" id="compare-grid" hidden>
        <div>
          <h3>원문</h3>
          <div class="compare-panel" id="compare-original"></div>
        </div>
        <div>
          <h3>첨삭 결과</h3>
          <div class="compare-panel" id="compare-result"></div>
        </div>
      </div>
      <div class="row">
        <button id="save-btn" class="primary" disabled>히스토리에 저장</button>
        <span id="save-status" role="status"></span>
      </div>
    </section>

    <section class="card" id="history-section">
      <h2>5. 히스토리</h2>
      <ul id="history-list"></ul>
      <p id="history-empty" class="hint">저장된 기록이 없습니다.</p>
    </section>
  </main>

  <script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: style.css 작성**

`essay_helper/style.css`:

```css
:root {
  --bg: #fdf8f2;
  --card: #ffffff;
  --ink: #3d3630;
  --sub: #8a7f73;
  --accent: #e8735a;
  --accent-soft: #fbe3dc;
  --line: #eee3d6;
  --radius: 12px;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
}

.app-header {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 20px 8px;
  text-align: center;
}

.app-header h1 { margin: 0 0 6px; font-size: 1.7rem; }
.tagline { margin: 0; color: var(--sub); }

main {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px 20px 60px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 22px 24px;
}

.card h2 { margin: 0 0 14px; font-size: 1.1rem; }
.card h3 { margin: 0 0 8px; font-size: 0.95rem; color: var(--sub); }

textarea, input[type="text"] {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  font: inherit;
  color: inherit;
  background: #fffdfa;
  resize: vertical;
}

textarea:focus, input[type="text"]:focus {
  outline: 2px solid var(--accent-soft);
  border-color: var(--accent);
}

.char-count { text-align: right; color: var(--sub); font-size: 0.85rem; margin-top: 4px; }

fieldset {
  border: 1px solid var(--line);
  border-radius: 8px;
  margin: 0 0 14px;
  padding: 12px 14px;
}

legend { padding: 0 6px; color: var(--sub); font-size: 0.9rem; }

.check-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 4px 14px 4px 0;
  cursor: pointer;
}

button.primary {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 22px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

button.primary:hover:not(:disabled) { filter: brightness(0.95); }
button.primary:disabled { background: var(--line); color: var(--sub); cursor: not-allowed; }

.hint { color: var(--sub); font-size: 0.85rem; margin: 8px 0 0; }
.row { display: flex; align-items: center; gap: 12px; margin-top: 10px; }

#copy-status, #save-status { color: var(--accent); font-size: 0.9rem; }

.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.compare-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fffdfa;
  padding: 14px;
  white-space: pre-wrap;
  max-height: 420px;
  overflow-y: auto;
  font-size: 0.95rem;
}

#history-list { list-style: none; margin: 0; padding: 0; }

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--line);
}

.history-item:last-child { border-bottom: none; }

.history-load {
  background: none;
  border: none;
  font: inherit;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  flex: 1;
  padding: 0;
}

.history-load:hover { color: var(--accent); }
.history-date { color: var(--sub); font-size: 0.8rem; margin-left: 8px; }

.history-delete {
  background: none;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--sub);
  cursor: pointer;
  padding: 2px 10px;
  font-size: 0.85rem;
}

.history-delete:hover { color: var(--accent); border-color: var(--accent); }

@media (max-width: 800px) {
  .compare-grid { grid-template-columns: 1fr; }
  .card { padding: 18px 16px; }
}
```

- [ ] **Step 3: 브라우저에서 마크업 확인**

Run (in repo root): `python -m http.server 8300 --directory C:/youtube/essay_helper` 후 브라우저에서 `http://localhost:8300` 열기 (또는 Claude Code 환경이면 launch.json의 `essay-helper` 설정으로 preview — Task 4 Step 1에서 추가하므로 이 시점엔 직접 실행).
Expected: 5개 카드 섹션이 세로로 배치되고, 콘솔에 app.js 404 외 오류 없음 (app.js는 Task 4에서 추가).

- [ ] **Step 4: 커밋**

```bash
git add essay_helper/index.html essay_helper/style.css
git commit -m "feat(essay_helper): 페이지 마크업 및 스타일 추가"
```

---

### Task 4: app.js DOM 배선 + launch.json + 수동 검증

**Files:**
- Create: `essay_helper/app.js`
- Modify: `.claude/launch.json` (configurations 배열에 항목 추가)

**Interfaces:**
- Consumes:
  - `prompts.js`의 `STYLE_GUIDES`, `PLATFORM_GUIDES` (체크박스 렌더링용 — `{ [id]: { label } }`)
  - `prompt-builder.js`의 `buildPrompt({ original, styles, situation, platforms })`
  - `history.js`의 `loadHistory(storage)`, `saveEntry(storage, { original, result, options })`, `deleteEntry(storage, id)`
  - Task 3의 DOM id 전부
- Produces: 완성된 앱 (이후 태스크 없음)

- [ ] **Step 1: launch.json에 정적 서버 항목 추가**

`.claude/launch.json`의 `configurations` 배열 끝에 추가:

```json
{
  "name": "essay-helper",
  "runtimeExecutable": "python",
  "runtimeArgs": ["-m", "http.server", "8300", "--directory", "C:/youtube/essay_helper"],
  "port": 8300
}
```

- [ ] **Step 2: app.js 작성**

`essay_helper/app.js`:

```js
import { STYLE_GUIDES, PLATFORM_GUIDES } from './prompts.js';
import { buildPrompt } from './prompt-builder.js';
import { loadHistory, saveEntry, deleteEntry } from './history.js';

const $ = (id) => document.getElementById(id);

const els = {
  original: $('original-input'),
  charCount: $('char-count'),
  styleOptions: $('style-options'),
  situation: $('situation-input'),
  platformOptions: $('platform-options'),
  generateBtn: $('generate-btn'),
  promptWrap: $('prompt-output-wrap'),
  promptOutput: $('prompt-output'),
  copyBtn: $('copy-btn'),
  copyStatus: $('copy-status'),
  resultInput: $('result-input'),
  compareGrid: $('compare-grid'),
  compareOriginal: $('compare-original'),
  compareResult: $('compare-result'),
  saveBtn: $('save-btn'),
  saveStatus: $('save-status'),
  historyList: $('history-list'),
  historyEmpty: $('history-empty'),
};

// ── 체크박스 렌더링 ──────────────────────────────────────────

function renderCheckboxes(container, guides, name, checkedByDefault) {
  for (const [id, guide] of Object.entries(guides)) {
    const label = document.createElement('label');
    label.className = 'check-item';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = name;
    input.value = id;
    input.checked = checkedByDefault;
    label.append(input, document.createTextNode(guide.label));
    container.appendChild(label);
  }
}

renderCheckboxes(els.styleOptions, STYLE_GUIDES, 'style', true);
renderCheckboxes(els.platformOptions, PLATFORM_GUIDES, 'platform', false);

function checkedValues(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
}

function readOptions() {
  return {
    styles: checkedValues('style'),
    situation: els.situation.value,
    platforms: checkedValues('platform'),
  };
}

// ── 초안 입력 ────────────────────────────────────────────────

function refreshInputState() {
  const text = els.original.value;
  els.charCount.textContent = String(text.length);
  els.generateBtn.disabled = text.trim() === '';
  refreshCompare();
}

els.original.addEventListener('input', refreshInputState);

// ── 프롬프트 생성 + 복사 ─────────────────────────────────────

els.generateBtn.addEventListener('click', () => {
  const prompt = buildPrompt({ original: els.original.value, ...readOptions() });
  els.promptOutput.value = prompt;
  els.promptWrap.hidden = false;
  els.copyStatus.textContent = '';
});

els.copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(els.promptOutput.value);
    els.copyStatus.textContent = '복사되었습니다!';
  } catch {
    els.promptOutput.select();
    els.copyStatus.textContent = '자동 복사가 안 되어 전체 선택했어요. Ctrl+C를 눌러주세요.';
  }
  setTimeout(() => { els.copyStatus.textContent = ''; }, 4000);
});

// ── 결과 비교 ────────────────────────────────────────────────

function refreshCompare() {
  const original = els.original.value.trim();
  const result = els.resultInput.value.trim();
  const showCompare = original !== '' && result !== '';
  els.compareGrid.hidden = !showCompare;
  if (showCompare) {
    els.compareOriginal.textContent = els.original.value;
    els.compareResult.textContent = els.resultInput.value;
  }
  els.saveBtn.disabled = !showCompare;
}

els.resultInput.addEventListener('input', refreshCompare);

// ── 히스토리 ─────────────────────────────────────────────────

function formatDate(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

function renderHistory() {
  const entries = loadHistory(localStorage);
  els.historyList.replaceChildren();
  els.historyEmpty.hidden = entries.length > 0;

  for (const entry of entries) {
    const li = document.createElement('li');
    li.className = 'history-item';

    const loadBtn = document.createElement('button');
    loadBtn.className = 'history-load';
    loadBtn.textContent = entry.title;
    const date = document.createElement('span');
    date.className = 'history-date';
    date.textContent = formatDate(entry.date);
    loadBtn.appendChild(date);
    loadBtn.addEventListener('click', () => restoreEntry(entry));

    const delBtn = document.createElement('button');
    delBtn.className = 'history-delete';
    delBtn.textContent = '삭제';
    delBtn.addEventListener('click', () => {
      deleteEntry(localStorage, entry.id);
      renderHistory();
    });

    li.append(loadBtn, delBtn);
    els.historyList.appendChild(li);
  }
}

function restoreEntry(entry) {
  els.original.value = entry.original;
  els.resultInput.value = entry.result;
  els.situation.value = entry.options.situation ?? '';
  for (const input of document.querySelectorAll('input[name="style"]')) {
    input.checked = (entry.options.styles ?? []).includes(input.value);
  }
  for (const input of document.querySelectorAll('input[name="platform"]')) {
    input.checked = (entry.options.platforms ?? []).includes(input.value);
  }
  els.promptWrap.hidden = true;
  refreshInputState();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

els.saveBtn.addEventListener('click', () => {
  try {
    saveEntry(localStorage, {
      original: els.original.value,
      result: els.resultInput.value,
      options: readOptions(),
    });
    els.saveStatus.textContent = '저장되었습니다!';
    renderHistory();
  } catch {
    els.saveStatus.textContent = '저장 공간이 부족합니다. 오래된 기록을 삭제해 주세요.';
  }
  setTimeout(() => { els.saveStatus.textContent = ''; }, 4000);
});

// ── 초기화 ───────────────────────────────────────────────────

refreshInputState();
renderHistory();
```

- [ ] **Step 3: 전체 단위 테스트 재실행**

Run (in `essay_helper/`): `node --test tests/`
Expected: PASS — 17 tests (app.js는 테스트 대상 아님, 회귀 확인용)

- [ ] **Step 4: 브라우저 수동 검증**

launch.json의 `essay-helper` 서버를 시작하고 `http://localhost:8300`에서 확인:

1. 초안 비어 있음 → [프롬프트 생성] 비활성
2. 초안 입력 → 글자 수 갱신, 버튼 활성화
3. 스타일 4종 기본 체크 상태, 플랫폼은 미체크 → 생성 시 프롬프트에 스타일 4종 + `general` 형식 가이드 포함 확인
4. 플랫폼 `네이버 블로그` 체크 + 상황 입력 → 프롬프트에 반영 확인
5. [복사] → "복사되었습니다!" 표시
6. 결과 텍스트 붙여넣기 → 비교 그리드 표시, [저장] 활성화
7. [저장] → 히스토리 목록에 제목·날짜 표시
8. 새로고침 → 히스토리 유지, 클릭 시 원문·결과·옵션 복원
9. [삭제] → 항목 제거
10. 창 폭 <800px → 비교 뷰 상하 배치
11. 콘솔 오류 0건

- [ ] **Step 5: 커밋**

```bash
git add essay_helper/app.js .claude/launch.json
git commit -m "feat(essay_helper): 폼 배선·프롬프트 생성·비교 뷰·히스토리 UI 구현"
```

---

### Task 5: README

**Files:**
- Create: `essay_helper/README.md`

**Interfaces:**
- Consumes: 완성된 앱 (Task 1~4)
- Produces: 사용 안내 문서

- [ ] **Step 1: README.md 작성**

`essay_helper/README.md`:

```markdown
# 에세이 첨삭 도우미

에세이 초안을 붙여넣고 스타일 지침을 고르면, ChatGPT/Claude에 붙여넣을 첨삭 프롬프트를 만들어 주는 정적 웹앱입니다. AI 결과물을 다시 붙여넣으면 원문과 나란히 비교하고 브라우저(localStorage)에 저장할 수 있습니다.

## 실행

빌드·서버 불필요 — `index.html`을 브라우저로 열면 됩니다.

로컬 서버로 띄우려면:

    python -m http.server 8300 --directory .

## 사용 흐름

1. 초안 붙여넣기
2. 스타일 지침(심리·철학 쉽게 / 후킹 문구 / 따뜻한 위로 / 직장인 공감), 상황, 플랫폼 선택
3. [프롬프트 생성] → [복사] → ChatGPT/Claude에 붙여넣기
4. AI 결과를 "결과 비교"에 붙여넣어 원문과 비교
5. [히스토리에 저장] — 새로고침해도 유지, 클릭으로 복원

## 테스트

    node --test tests/

## 파일 구성

- `prompts.js` — 지침·플랫폼 지시문 텍스트 (문구 수정은 여기서)
- `prompt-builder.js` — 프롬프트 조립 순수 함수
- `history.js` — localStorage 히스토리
- `app.js` — DOM 배선
```

- [ ] **Step 2: 커밋**

```bash
git add essay_helper/README.md
git commit -m "docs(essay_helper): README 추가"
```

# 네이버 블로그 위젯 메이커 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 블로그 정보(이름·슬로건·운영시간·이미지·메뉴)를 입력하면 네이버 블로그 위젯용 HTML 코드와 PC/모바일 배경 이미지를 만들어주는, 서버 없는 정적 웹앱을 구현한다.

**Architecture:** 빌드 도구 없는 순수 HTML+CSS+바닐라 JS(ES 모듈). 순수 함수(위젯 코드 생성, 크롭 좌표 계산)는 `node --test`로 단위 테스트하고, DOM/캔버스 상호작용은 브라우저 preview 도구로 수동 검증한다.

**Tech Stack:** HTML5, CSS3, 바닐라 JavaScript(ES Modules), Canvas API, Node.js 내장 테스트 러너(`node:test`). 외부 패키지·프레임워크·서버 없음.

## Global Constraints

- 서버 없음 — 빌드 도구·백엔드 없이 정적 파일(HTML/CSS/JS)만으로 구현한다
- 외부 의존성 없음 — npm 패키지, CDN, 외부 API 호출 없음. 테스트는 Node 내장 `node:test`/`node:assert`만 사용
- 데이터 저장 없음 — `localStorage`/DB 사용 금지. 새로고침 시 초기화되는 것이 의도된 동작
- AI 없음 — 어떤 AI 호출도 하지 않는다
- 위젯 코드 안의 이미지는 사용자가 입력한 외부 URL을 그대로 참조한다 — 서버는 이미지를 저장·호스팅하지 않는다
- 배경 이미지(PC 1920×700, 모바일 700×700)는 브라우저 `<canvas>`에서 크롭/리사이즈해 다운로드 파일로만 제공한다 — URL로 노출하지 않는다
- 메뉴 항목은 최대 5개로 제한한다
- 비용 0원 (무료 정적 호스팅 전제)

---

## Task 1: 프로젝트 스캐폴드

**Files:**
- Create: `blog_widget_maker/index.html`
- Create: `blog_widget_maker/style.css`
- Create: `blog_widget_maker/package.json`
- Create: `blog_widget_maker/README.md`
- Modify: `.claude/launch.json`

**Interfaces:**
- Produces: 이후 모든 태스크가 참조하는 DOM 요소 id 목록 — `blogName`, `slogan`, `hours`, `profileImageUrl`, `profileImageUrlWarning`, `customBgColor`, `.bwm-color-btn`(data-color), `qlHome`, `qlBlogMap`, `qlReserve`, `qlPhone`, `menuList`, `addMenuBtn`, `menuLimitWarning`, `profileWidgetCode`, `menuWidgetCode`, `copyProfileBtn`, `copyMenuBtn`, `profilePreviewFrame`, `menuPreviewFrame`, `bgImageInput`, `bgImageWarning`, `cropCanvasPC`, `cropCanvasMobile`, `downloadPCBtn`, `downloadMobileBtn`, `checklist-section`

- [ ] **Step 1: `blog_widget_maker/index.html` 작성**

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>네이버 블로그 위젯 메이커</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="bwm-header">
    <h1>네이버 블로그 위젯 메이커</h1>
    <p>블로그 정보를 입력하면 위젯 코드와 배경 이미지를 만들어드립니다.</p>
  </header>

  <main class="bwm-layout">
    <section id="form-section" class="bwm-panel">
      <h2>1. 블로그 정보 입력</h2>
      <label>블로그명
        <input type="text" id="blogName" placeholder="예. 마루웍스 공유오피스" />
      </label>
      <label>슬로건
        <input type="text" id="slogan" placeholder="예. 편리하고 깨끗한 공유오피스" />
      </label>
      <label>운영시간
        <input type="text" id="hours" placeholder="예. 24시간 언제나 이용 가능" />
      </label>
      <label>프로필 이미지 URL
        <input type="url" id="profileImageUrl" placeholder="https://..." />
        <span class="bwm-warning" id="profileImageUrlWarning" hidden>http(s):// 로 시작하는 URL을 입력하세요</span>
      </label>

      <fieldset>
        <legend>배경색</legend>
        <div class="bwm-color-presets">
          <button type="button" class="bwm-color-btn" data-color="#ffffff" style="background:#ffffff" title="화이트"></button>
          <button type="button" class="bwm-color-btn" data-color="#000000" style="background:#000000" title="블랙"></button>
          <button type="button" class="bwm-color-btn" data-color="#ff7a00" style="background:#ff7a00" title="오렌지"></button>
          <button type="button" class="bwm-color-btn" data-color="#001a72" style="background:#001a72" title="네이비"></button>
        </div>
        <label>커스텀 색상
          <input type="color" id="customBgColor" value="#ffffff" />
        </label>
      </fieldset>

      <fieldset>
        <legend>대표 링크</legend>
        <label>홈 <input type="url" id="qlHome" placeholder="https://..." /></label>
        <label>블로그맵 <input type="url" id="qlBlogMap" placeholder="https://..." /></label>
        <label>예약하기 <input type="url" id="qlReserve" placeholder="https://..." /></label>
        <label>전화걸기 <input type="tel" id="qlPhone" placeholder="tel:01012345678" /></label>
      </fieldset>

      <fieldset>
        <legend>메뉴 (최대 5개)</legend>
        <div id="menuList"></div>
        <button type="button" id="addMenuBtn">+ 메뉴 추가</button>
        <span class="bwm-warning" id="menuLimitWarning" hidden>최대 5개까지 등록 가능합니다</span>
      </fieldset>
    </section>

    <section id="output-section" class="bwm-panel">
      <h2>2. 위젯 코드</h2>
      <div class="bwm-code-block">
        <div class="bwm-code-header">
          <h3>프로필 위젯</h3>
          <button type="button" id="copyProfileBtn">복사</button>
        </div>
        <pre id="profileWidgetCode"></pre>
        <iframe id="profilePreviewFrame" class="bwm-preview-frame" title="프로필 위젯 미리보기"></iframe>
      </div>
      <div class="bwm-code-block">
        <div class="bwm-code-header">
          <h3>메뉴 위젯</h3>
          <button type="button" id="copyMenuBtn">복사</button>
        </div>
        <pre id="menuWidgetCode"></pre>
        <iframe id="menuPreviewFrame" class="bwm-preview-frame" title="메뉴 위젯 미리보기"></iframe>
      </div>
    </section>

    <section id="cropper-section" class="bwm-panel">
      <h2>3. 배경 이미지 만들기</h2>
      <input type="file" id="bgImageInput" accept="image/jpeg,image/png,image/webp" />
      <span class="bwm-warning" id="bgImageWarning" hidden></span>
      <div class="bwm-crop-row">
        <div>
          <h3>PC (1920×700)</h3>
          <canvas id="cropCanvasPC" width="480" height="175"></canvas>
          <button type="button" id="downloadPCBtn" disabled>PC 배경 다운로드</button>
        </div>
        <div>
          <h3>모바일 (700×700)</h3>
          <canvas id="cropCanvasMobile" width="240" height="240"></canvas>
          <button type="button" id="downloadMobileBtn" disabled>모바일 배경 다운로드</button>
        </div>
      </div>
    </section>

    <section id="checklist-section" class="bwm-panel">
      <h2>4. 진행 체크리스트</h2>
      <ol id="checklist">
        <li><label><input type="checkbox" /> 블로그 개설 (네이버에서 직접 진행)</label></li>
        <li><label><input type="checkbox" /> 배경 이미지 준비 → <a href="#cropper-section">3번 섹션</a></label></li>
        <li><label><input type="checkbox" /> 카테고리 생성 (네이버에서 직접 진행)</label></li>
        <li><label><input type="checkbox" /> 스킨 선택 (네이버에서 직접 진행)</label></li>
        <li><label><input type="checkbox" /> 정보 입력 → <a href="#form-section">1번 섹션</a></label></li>
        <li><label><input type="checkbox" /> 위젯 등록 → <a href="#output-section">2번 섹션 코드 복사 후 네이버 위젯에 붙여넣기</a></label></li>
        <li><label><input type="checkbox" /> 배경 이미지 저장 후 등록 → <a href="#cropper-section">3번 섹션 다운로드 파일을 네이버 스킨 설정에 업로드</a></label></li>
        <li><label><input type="checkbox" /> 모든 작업 완료 확인</label></li>
      </ol>
    </section>
  </main>

  <script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: `blog_widget_maker/style.css` 작성**

```css
:root {
  --bwm-accent: #00a3ff;
  --bwm-border: #ddd;
  --bwm-bg: #fafafa;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, "Pretendard", "Malgun Gothic", sans-serif;
  background: var(--bwm-bg);
  color: #222;
}
.bwm-header {
  padding: 24px 32px;
  background: #fff;
  border-bottom: 1px solid var(--bwm-border);
}
.bwm-header h1 { margin: 0 0 4px; font-size: 20px; }
.bwm-header p { margin: 0; color: #666; font-size: 14px; }
.bwm-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  padding: 24px 32px;
  max-width: 1200px;
  margin: 0 auto;
}
.bwm-panel {
  background: #fff;
  border: 1px solid var(--bwm-border);
  border-radius: 8px;
  padding: 20px;
}
.bwm-panel h2 { margin-top: 0; font-size: 16px; }
.bwm-panel label {
  display: block;
  margin-bottom: 12px;
  font-size: 13px;
  color: #444;
}
.bwm-panel input[type="text"],
.bwm-panel input[type="url"],
.bwm-panel input[type="tel"] {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: 1px solid var(--bwm-border);
  border-radius: 4px;
  font-size: 14px;
}
.bwm-warning {
  display: block;
  color: #d1451f;
  font-size: 12px;
  margin-top: 4px;
}
.bwm-color-presets { display: flex; gap: 8px; margin-bottom: 8px; }
.bwm-color-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--bwm-border);
  cursor: pointer;
}
.bwm-menu-item-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
}
.bwm-menu-item-row select { width: 90px; }
.bwm-menu-item-row input { flex: 1; padding: 6px; }
.bwm-code-block { margin-bottom: 24px; }
.bwm-code-header { display: flex; justify-content: space-between; align-items: center; }
.bwm-code-block pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.bwm-preview-frame {
  width: 100%;
  height: 140px;
  border: 1px dashed var(--bwm-border);
  border-radius: 6px;
}
.bwm-crop-row { display: flex; gap: 24px; flex-wrap: wrap; }
.bwm-crop-row canvas {
  border: 1px solid var(--bwm-border);
  cursor: grab;
  touch-action: none;
}
#checklist-section ol { padding-left: 20px; }
#checklist-section li { margin-bottom: 8px; }
```

- [ ] **Step 3: `blog_widget_maker/package.json` 작성**

```json
{
  "name": "blog-widget-maker",
  "private": true,
  "type": "module"
}
```

`"type": "module"`은 이후 태스크에서 `import`/`export` 구문과 `node --test`를 쓰기 위한 설정이다. 의존성이나 빌드 스크립트는 없다.

- [ ] **Step 4: `blog_widget_maker/README.md` 작성**

```markdown
# 네이버 블로그 위젯 메이커

블로그 이름·슬로건·운영시간·이미지·메뉴 등을 입력하면 네이버 블로그 위젯용 HTML 코드와 스킨 배경 이미지(PC 1920×700 / 모바일 700×700)를 만들어주는 정적 웹앱입니다.

## 실행 방법

빌드 없이 정적 파일만 있으면 됩니다.

```
python -m http.server 8200 --directory blog_widget_maker
```

브라우저에서 http://localhost:8200 접속.

## 테스트

```
node --test blog_widget_maker/tests
```

## 사용 흐름

1. 좌측 폼에 블로그 정보를 입력하면 우측 위젯 코드와 미리보기가 실시간으로 갱신됩니다.
2. "복사" 버튼으로 위젯 코드를 클립보드에 복사해 네이버 블로그 위젯 등록 화면에 붙여넣습니다.
3. 배경 이미지 섹션에서 사진을 업로드하고 크롭 박스를 드래그해 PC/모바일용 배경을 각각 다운로드합니다.
4. 체크리스트로 전체 진행 상황을 확인합니다 (네이버 블로그 개설/카테고리/스킨 선택은 네이버에서 직접 진행).

## 주의

- 위젯 코드에 들어가는 이미지(프로필 사진 등)는 이 도구가 호스팅하지 않습니다. 외부에 직접 업로드한 이미지 URL을 입력하세요.
- 배경 이미지는 다운로드한 파일을 네이버 블로그 스킨 설정에 직접 업로드해야 합니다.
```

- [ ] **Step 5: `.claude/launch.json`에 정적 서버 설정 추가**

`.claude/launch.json`의 `configurations` 배열 끝에 다음 항목을 추가:

```json
{
  "name": "blog-widget-maker",
  "runtimeExecutable": "python",
  "runtimeArgs": ["-m", "http.server", "8200", "--directory", "C:/youtube/blog_widget_maker"],
  "port": 8200
}
```

- [ ] **Step 6: 브라우저에서 스캐폴드 확인**

`blog_widget_maker` 정적 서버를 실행하고 `http://localhost:8200`을 열어 4개 섹션 제목("1. 블로그 정보 입력", "2. 위젯 코드", "3. 배경 이미지 만들기", "4. 진행 체크리스트")과 체크리스트 8개 항목이 모두 보이는지 확인한다. `app.js`가 아직 없어 콘솔에 404 에러가 뜨는 것은 정상이다(다음 태스크에서 생성).

- [ ] **Step 7: 커밋**

```bash
git add blog_widget_maker/index.html blog_widget_maker/style.css blog_widget_maker/package.json blog_widget_maker/README.md .claude/launch.json
git commit -m "feat(blog_widget_maker): 정적 웹앱 스캐폴드 추가"
```

---

## Task 2: 아이콘 세트 (`icons.js`)

**Files:**
- Create: `blog_widget_maker/icons.js`
- Test: `blog_widget_maker/tests/icons.test.js`

**Interfaces:**
- Produces: `ICONS` (object, key→SVG 문자열), `ICON_KEYS` (string[]), `getIconSvg(key: string): string` — Task 3(위젯 템플릿)과 Task 5(메뉴 아이콘 선택 UI)가 사용

- [ ] **Step 1: 실패하는 테스트 작성**

`blog_widget_maker/tests/icons.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ICONS, ICON_KEYS, getIconSvg } from '../icons.js';

test('every icon key maps to an svg string', () => {
  for (const key of ICON_KEYS) {
    assert.match(ICONS[key], /^<svg/);
  }
});

test('getIconSvg falls back to etc icon for unknown key', () => {
  assert.equal(getIconSvg('unknown-key'), ICONS.etc);
});

test('getIconSvg returns matching icon for known key', () => {
  assert.equal(getIconSvg('home'), ICONS.home);
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test blog_widget_maker/tests/icons.test.js`
Expected: FAIL — `Cannot find module '../icons.js'`

- [ ] **Step 3: `blog_widget_maker/icons.js` 작성**

```js
export const ICONS = {
  home: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/></svg>',
  map: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 20l-6-3V4l6 3 6-3 6 3v13l-6-3-6 3z"/></svg>',
  reserve: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
  phone: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.4 2.1L8 9.7a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.8.3 1.7.5 2.6.6a2 2 0 0 1 1.7 2z"/></svg>',
  info: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>',
  price: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.6 12.6L12 21.2 2.8 12 3.6 3.6 12 2.8l8.6 9.2a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/></svg>',
  location: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  etc: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></svg>',
};

export const ICON_KEYS = Object.keys(ICONS);

export function getIconSvg(key) {
  return ICONS[key] || ICONS.etc;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test blog_widget_maker/tests/icons.test.js`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add blog_widget_maker/icons.js blog_widget_maker/tests/icons.test.js
git commit -m "feat(blog_widget_maker): 아이콘 세트 추가"
```

---

## Task 3: 위젯 코드 생성기 (`widget-templates.js`)

**Files:**
- Create: `blog_widget_maker/widget-templates.js`
- Test: `blog_widget_maker/tests/widget-templates.test.js`

**Interfaces:**
- Consumes: `getIconSvg(key: string): string` from `icons.js` (Task 2)
- Produces: `escapeHtml(str: string): string`, `renderProfileWidgetCode(state): string`, `renderMenuWidgetCode(state): string` — Task 5(app.js)가 폼 상태 변경마다 호출

`state` 형태(문서화용):
```
{
  blogName: string,
  slogan: string,
  hours: string,
  profileImageUrl: string,
  bgColor: string,               // hex, 예: "#ffffff"
  quickLinks: { home, blogMap, reserve, phone },  // 각 string
  menus: [{ icon, text, url }],  // 최대 5개, 초과분은 렌더 함수가 자체적으로 무시
}
```

- [ ] **Step 1: 실패하는 테스트 작성**

`blog_widget_maker/tests/widget-templates.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml, renderProfileWidgetCode, renderMenuWidgetCode } from '../widget-templates.js';

test('escapeHtml escapes special characters', () => {
  assert.equal(escapeHtml(`<b>"a" & 'b'</b>`), '&lt;b&gt;&quot;a&quot; &amp; &#39;b&#39;&lt;/b&gt;');
});

test('renderProfileWidgetCode shows placeholder when blogName is empty', () => {
  const html = renderProfileWidgetCode({
    blogName: '', slogan: '', hours: '', profileImageUrl: '', bgColor: '#ffffff',
    quickLinks: {}, menus: [],
  });
  assert.match(html, /블로그명을 입력하세요/);
});

test('renderProfileWidgetCode includes escaped blog name, image url and bg color', () => {
  const html = renderProfileWidgetCode({
    blogName: '<script>', slogan: '슬로건', hours: '24시간', profileImageUrl: 'https://x.com/a.png',
    bgColor: '#000000', quickLinks: { home: 'https://a.com' }, menus: [],
  });
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /https:\/\/x\.com\/a\.png/);
  assert.match(html, /background:#000000/);
});

test('renderMenuWidgetCode shows empty message with no menus', () => {
  const html = renderMenuWidgetCode({ menus: [] });
  assert.match(html, /메뉴를 추가하세요/);
});

test('renderMenuWidgetCode renders up to 5 menus and ignores extras', () => {
  const menus = Array.from({ length: 7 }, (_, i) => ({ icon: 'home', text: `메뉴${i}`, url: `https://x.com/${i}` }));
  const html = renderMenuWidgetCode({ menus });
  const matches = html.match(/bwm-menu-item/g) || [];
  assert.equal(matches.length, 5);
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test blog_widget_maker/tests/widget-templates.test.js`
Expected: FAIL — `Cannot find module '../widget-templates.js'`

- [ ] **Step 3: `blog_widget_maker/widget-templates.js` 작성**

```js
import { getIconSvg } from './icons.js';

const QUICK_LINK_DEFS = [
  { key: 'home', label: '홈', icon: 'home' },
  { key: 'blogMap', label: '블로그맵', icon: 'map' },
  { key: 'reserve', label: '예약하기', icon: 'reserve' },
  { key: 'phone', label: '전화걸기', icon: 'phone' },
];

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function renderProfileWidgetCode(state) {
  const name = state.blogName && state.blogName.trim()
    ? escapeHtml(state.blogName.trim())
    : '블로그명을 입력하세요';
  const slogan = state.slogan && state.slogan.trim() ? escapeHtml(state.slogan.trim()) : '';
  const hours = state.hours && state.hours.trim() ? escapeHtml(state.hours.trim()) : '';
  const imgUrl = state.profileImageUrl && state.profileImageUrl.trim()
    ? escapeHtml(state.profileImageUrl.trim())
    : '';
  const bg = state.bgColor || '#ffffff';
  const links = state.quickLinks || {};

  const linkItems = QUICK_LINK_DEFS.map((def) => {
    const url = links[def.key] && links[def.key].trim() ? escapeHtml(links[def.key].trim()) : '#';
    return `<a href="${url}" target="_blank" rel="noopener" class="bwm-quicklink" title="${def.label}">${getIconSvg(def.icon)}</a>`;
  }).join('');

  return [
    `<div class="bwm-profile-widget" style="background:${bg}">`,
    imgUrl ? `  <img src="${imgUrl}" alt="${name}" class="bwm-profile-img" />` : '',
    `  <div class="bwm-profile-name">${name}</div>`,
    slogan ? `  <div class="bwm-profile-slogan">${slogan}</div>` : '',
    hours ? `  <div class="bwm-profile-hours">${hours}</div>` : '',
    `  <div class="bwm-quicklinks">${linkItems}</div>`,
    `</div>`,
  ].filter(Boolean).join('\n');
}

export function renderMenuWidgetCode(state) {
  const menus = Array.isArray(state.menus) ? state.menus.slice(0, 5) : [];
  if (menus.length === 0) {
    return `<div class="bwm-menu-widget">\n  <div class="bwm-menu-empty">메뉴를 추가하세요</div>\n</div>`;
  }
  const items = menus.map((m) => {
    const text = m.text && m.text.trim() ? escapeHtml(m.text.trim()) : '메뉴';
    const url = m.url && m.url.trim() ? escapeHtml(m.url.trim()) : '#';
    return `  <a href="${url}" target="_blank" rel="noopener" class="bwm-menu-item">${getIconSvg(m.icon)}<span>${text}</span></a>`;
  }).join('\n');
  return `<div class="bwm-menu-widget">\n${items}\n</div>`;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test blog_widget_maker/tests/widget-templates.test.js`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add blog_widget_maker/widget-templates.js blog_widget_maker/tests/widget-templates.test.js
git commit -m "feat(blog_widget_maker): 위젯 코드 생성 함수 추가"
```

---

## Task 4: 크롭 좌표 계산 (`cropper.js` 순수 함수)

**Files:**
- Create: `blog_widget_maker/cropper.js`
- Test: `blog_widget_maker/tests/cropper.test.js`

**Interfaces:**
- Produces: `computeInitialCropRect(imgWidth, imgHeight, targetRatio): {x,y,width,height}`, `clampCropRect(rect, imgWidth, imgHeight): {x,y,width,height}` — Task 6(크롭 UI)이 사용

- [ ] **Step 1: 실패하는 테스트 작성**

`blog_widget_maker/tests/cropper.test.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeInitialCropRect, clampCropRect } from '../cropper.js';

test('computeInitialCropRect centers a wide crop inside a taller image', () => {
  const rect = computeInitialCropRect(1000, 1000, 1920 / 700);
  assert.ok(Math.abs(rect.width / rect.height - 1920 / 700) < 0.001);
  assert.equal(rect.x, 0);
  assert.ok(rect.y > 0);
});

test('computeInitialCropRect centers a square crop inside a wider image', () => {
  const rect = computeInitialCropRect(2000, 500, 1);
  assert.ok(Math.abs(rect.width / rect.height - 1) < 0.001);
  assert.equal(rect.y, 0);
  assert.ok(rect.x > 0);
});

test('clampCropRect keeps rect within image bounds', () => {
  const rect = clampCropRect({ x: -50, y: 9999, width: 300, height: 200 }, 1000, 800);
  assert.equal(rect.x, 0);
  assert.equal(rect.y, 600);
  assert.equal(rect.width, 300);
  assert.equal(rect.height, 200);
});

test('clampCropRect shrinks a rect larger than the image', () => {
  const rect = clampCropRect({ x: 0, y: 0, width: 5000, height: 4000 }, 1000, 800);
  assert.equal(rect.width, 1000);
  assert.equal(rect.height, 800);
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test blog_widget_maker/tests/cropper.test.js`
Expected: FAIL — `Cannot find module '../cropper.js'`

- [ ] **Step 3: `blog_widget_maker/cropper.js` 작성 (순수 함수만)**

```js
export function computeInitialCropRect(imgWidth, imgHeight, targetRatio) {
  const imgRatio = imgWidth / imgHeight;
  let width, height;
  if (imgRatio > targetRatio) {
    height = imgHeight;
    width = height * targetRatio;
  } else {
    width = imgWidth;
    height = width / targetRatio;
  }
  return {
    x: (imgWidth - width) / 2,
    y: (imgHeight - height) / 2,
    width,
    height,
  };
}

export function clampCropRect(rect, imgWidth, imgHeight) {
  const width = Math.min(rect.width, imgWidth);
  const height = Math.min(rect.height, imgHeight);
  const x = Math.max(0, Math.min(rect.x, imgWidth - width));
  const y = Math.max(0, Math.min(rect.y, imgHeight - height));
  return { x, y, width, height };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test blog_widget_maker/tests/cropper.test.js`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add blog_widget_maker/cropper.js blog_widget_maker/tests/cropper.test.js
git commit -m "feat(blog_widget_maker): 크롭 좌표 계산 함수 추가"
```

---

## Task 5: 폼 상태 관리 & 실시간 코드 렌더링 (`app.js`)

**Files:**
- Create: `blog_widget_maker/app.js`

**Interfaces:**
- Consumes: `renderProfileWidgetCode`, `renderMenuWidgetCode` (Task 3), `ICON_KEYS` (Task 2)
- Produces: 브라우저 전역에서 동작하는 `state` 객체(모듈 내부, export 없음) — Task 6이 같은 파일에 이어서 코드를 추가함

- [ ] **Step 1: `blog_widget_maker/app.js` 작성**

```js
import { renderProfileWidgetCode, renderMenuWidgetCode } from './widget-templates.js';
import { ICON_KEYS } from './icons.js';

const MAX_MENUS = 5;

function createDefaultState() {
  return {
    blogName: '',
    slogan: '',
    hours: '',
    profileImageUrl: '',
    bgColor: '#ffffff',
    quickLinks: { home: '', blogMap: '', reserve: '', phone: '' },
    menus: [],
  };
}

const state = createDefaultState();

const el = (id) => document.getElementById(id);

function renderAll() {
  const profileCode = renderProfileWidgetCode(state);
  const menuCode = renderMenuWidgetCode(state);
  el('profileWidgetCode').textContent = profileCode;
  el('menuWidgetCode').textContent = menuCode;
  el('profilePreviewFrame').srcdoc = `<style>body{margin:0;font-family:sans-serif;}</style>${profileCode}`;
  el('menuPreviewFrame').srcdoc = `<style>body{margin:0;font-family:sans-serif;}</style>${menuCode}`;
}

function bindTextField(id, stateKey) {
  el(id).addEventListener('input', (e) => {
    state[stateKey] = e.target.value;
    renderAll();
  });
}

function bindQuickLink(id, key) {
  el(id).addEventListener('input', (e) => {
    state.quickLinks[key] = e.target.value;
    renderAll();
  });
}

bindTextField('blogName', 'blogName');
bindTextField('slogan', 'slogan');
bindTextField('hours', 'hours');
bindTextField('profileImageUrl', 'profileImageUrl');
bindQuickLink('qlHome', 'home');
bindQuickLink('qlBlogMap', 'blogMap');
bindQuickLink('qlReserve', 'reserve');
bindQuickLink('qlPhone', 'phone');

document.querySelectorAll('.bwm-color-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.bgColor = btn.dataset.color;
    el('customBgColor').value = btn.dataset.color;
    renderAll();
  });
});
el('customBgColor').addEventListener('input', (e) => {
  state.bgColor = e.target.value;
  renderAll();
});

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
  } finally {
    document.body.removeChild(ta);
  }
  done();
}

function copyToClipboard(text, button) {
  const done = () => {
    const original = button.textContent;
    button.textContent = '복사됨!';
    setTimeout(() => {
      button.textContent = original;
    }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

el('copyProfileBtn').addEventListener('click', () => {
  copyToClipboard(el('profileWidgetCode').textContent, el('copyProfileBtn'));
});
el('copyMenuBtn').addEventListener('click', () => {
  copyToClipboard(el('menuWidgetCode').textContent, el('copyMenuBtn'));
});

function menuItemTemplate(index) {
  const wrap = document.createElement('div');
  wrap.className = 'bwm-menu-item-row';
  wrap.innerHTML = `
    <select class="bwm-menu-icon">
      ${ICON_KEYS.map((k) => `<option value="${k}">${k}</option>`).join('')}
    </select>
    <input type="text" class="bwm-menu-text" placeholder="예. 소개" />
    <input type="url" class="bwm-menu-url" placeholder="https://..." />
    <button type="button" class="bwm-menu-remove">삭제</button>
  `;
  const iconSel = wrap.querySelector('.bwm-menu-icon');
  const textInput = wrap.querySelector('.bwm-menu-text');
  const urlInput = wrap.querySelector('.bwm-menu-url');
  const removeBtn = wrap.querySelector('.bwm-menu-remove');

  const sync = () => {
    state.menus[index] = {
      icon: iconSel.value,
      text: textInput.value,
      url: urlInput.value,
    };
    renderAll();
  };
  iconSel.addEventListener('change', sync);
  textInput.addEventListener('input', sync);
  urlInput.addEventListener('input', sync);
  removeBtn.addEventListener('click', () => {
    state.menus.splice(index, 1);
    renderMenuList();
    renderAll();
  });
  return wrap;
}

function renderMenuList() {
  const container = el('menuList');
  container.innerHTML = '';
  state.menus.forEach((menu, index) => {
    const row = menuItemTemplate(index);
    row.querySelector('.bwm-menu-icon').value = menu.icon;
    row.querySelector('.bwm-menu-text').value = menu.text;
    row.querySelector('.bwm-menu-url').value = menu.url;
    container.appendChild(row);
  });
  el('addMenuBtn').disabled = state.menus.length >= MAX_MENUS;
  el('menuLimitWarning').hidden = state.menus.length < MAX_MENUS;
}

el('addMenuBtn').addEventListener('click', () => {
  if (state.menus.length >= MAX_MENUS) return;
  state.menus.push({ icon: ICON_KEYS[0], text: '', url: '' });
  renderMenuList();
  renderAll();
});

renderMenuList();
renderAll();
```

- [ ] **Step 2: 브라우저에서 폼 동작 확인**

`blog-widget-maker` 정적 서버(Task 1에서 등록)를 실행하고 페이지를 새로고침한다.

1. "블로그명"에 `<script>테스트</script>` 입력 → 우측 "프로필 위젯" 코드 블록에 `&lt;script&gt;테스트&lt;/script&gt;`로 이스케이프되어 나타나는지 확인
2. 배경색 프리셋(오렌지) 클릭 → 코드에 `background:#ff7a00`로 반영되는지 확인
3. "+ 메뉴 추가"를 5번 클릭 → 버튼이 비활성화되고 "최대 5개까지 등록 가능합니다" 문구가 보이는지 확인, 메뉴 텍스트/URL 입력 시 "메뉴 위젯" 코드 블록에 반영되는지 확인
4. "복사" 버튼 클릭 → 버튼 텍스트가 잠시 "복사됨!"으로 바뀌는지 확인

- [ ] **Step 3: 커밋**

```bash
git add blog_widget_maker/app.js
git commit -m "feat(blog_widget_maker): 폼 상태 관리 및 실시간 위젯 코드 렌더링 추가"
```

---

## Task 6: 배경 이미지 크롭 UI

**Files:**
- Modify: `blog_widget_maker/cropper.js` (Task 4에서 만든 파일 끝에 추가)
- Modify: `blog_widget_maker/app.js` (Task 5에서 만든 파일 끝에 추가)

**Interfaces:**
- Consumes: `computeInitialCropRect`, `clampCropRect` (같은 파일 내 Task 4 함수)
- Produces: `createCropController({canvas, image, target}): {toBlob(callback)}`, `TARGETS = {pc: {width,height}, mobile: {width,height}}`

- [ ] **Step 1: `blog_widget_maker/cropper.js` 끝에 다음 코드 추가**

```js
export const TARGETS = {
  pc: { width: 1920, height: 700 },
  mobile: { width: 700, height: 700 },
};

export function createCropController({ canvas, image, target }) {
  const { width: targetWidth, height: targetHeight } = target;
  const targetRatio = targetWidth / targetHeight;
  let rect = computeInitialCropRect(image.naturalWidth, image.naturalHeight, targetRatio);
  const ctx = canvas.getContext('2d');
  const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const offsetX = (canvas.width - image.naturalWidth * scale) / 2;
  const offsetY = (canvas.height - image.naturalHeight * scale) / 2;

  function toCanvasRect(r) {
    return {
      x: offsetX + r.x * scale,
      y: offsetY + r.y * scale,
      width: r.width * scale,
      height: r.height * scale,
    };
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, offsetX, offsetY, image.naturalWidth * scale, image.naturalHeight * scale);
    const c = toCanvasRect(rect);
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(offsetX, offsetY, image.naturalWidth * scale, c.y - offsetY);
    ctx.fillRect(
      offsetX,
      c.y + c.height,
      image.naturalWidth * scale,
      offsetY + image.naturalHeight * scale - (c.y + c.height)
    );
    ctx.fillRect(offsetX, c.y, c.x - offsetX, c.height);
    ctx.fillRect(c.x + c.width, c.y, offsetX + image.naturalWidth * scale - (c.x + c.width), c.height);
    ctx.strokeStyle = '#00a3ff';
    ctx.lineWidth = 2;
    ctx.strokeRect(c.x, c.y, c.width, c.height);
    ctx.restore();
  }

  let dragStart = null;
  canvas.addEventListener('pointerdown', (e) => {
    const r = canvas.getBoundingClientRect();
    dragStart = {
      x: e.clientX - r.left,
      y: e.clientY - r.top,
      rectX: rect.x,
      rectY: rect.y,
    };
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragStart) return;
    const r = canvas.getBoundingClientRect();
    const dx = (e.clientX - r.left - dragStart.x) / scale;
    const dy = (e.clientY - r.top - dragStart.y) / scale;
    rect = clampCropRect(
      { ...rect, x: dragStart.rectX + dx, y: dragStart.rectY + dy },
      image.naturalWidth,
      image.naturalHeight
    );
    draw();
  });
  window.addEventListener('pointerup', () => {
    dragStart = null;
  });

  draw();

  return {
    toBlob(callback) {
      const out = document.createElement('canvas');
      out.width = targetWidth;
      out.height = targetHeight;
      const octx = out.getContext('2d');
      octx.drawImage(image, rect.x, rect.y, rect.width, rect.height, 0, 0, targetWidth, targetHeight);
      out.toBlob(callback, 'image/png');
    },
  };
}
```

- [ ] **Step 2: `blog_widget_maker/app.js` 맨 위 import에 다음 줄 추가**

```js
import { createCropController, TARGETS } from './cropper.js';
```

- [ ] **Step 3: `blog_widget_maker/app.js` 끝에 다음 코드 추가**

```js
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

let pcController = null;
let mobileController = null;

el('bgImageInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const warning = el('bgImageWarning');
  warning.hidden = true;
  if (!file) return;
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    warning.textContent = 'JPG, PNG, WEBP 파일만 업로드할 수 있습니다.';
    warning.hidden = false;
    e.target.value = '';
    return;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    warning.textContent = '파일 크기는 10MB를 넘을 수 없습니다.';
    warning.hidden = false;
    e.target.value = '';
    return;
  }
  const img = new Image();
  img.onload = () => {
    pcController = createCropController({ canvas: el('cropCanvasPC'), image: img, target: TARGETS.pc });
    mobileController = createCropController({ canvas: el('cropCanvasMobile'), image: img, target: TARGETS.mobile });
    el('downloadPCBtn').disabled = false;
    el('downloadMobileBtn').disabled = false;
  };
  img.src = URL.createObjectURL(file);
});

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

el('downloadPCBtn').addEventListener('click', () => {
  if (!pcController) return;
  pcController.toBlob((blob) => downloadBlob(blob, 'bg-pc-1920x700.png'));
});
el('downloadMobileBtn').addEventListener('click', () => {
  if (!mobileController) return;
  mobileController.toBlob((blob) => downloadBlob(blob, 'bg-mobile-700x700.png'));
});
```

- [ ] **Step 4: node 테스트가 여전히 통과하는지 확인 (cropper.js에 추가한 DOM 코드가 순수 함수를 깨지 않았는지)**

Run: `node --test blog_widget_maker/tests`
Expected: PASS (모든 기존 테스트, `createCropController`는 `window`/`document`를 참조하므로 Node 테스트 대상 아님 — import 시점에는 실행되지 않는 함수 정의라 에러 없이 통과해야 함)

- [ ] **Step 5: 브라우저에서 크롭 동작 확인**

1. 임의의 사진 파일(JPG/PNG)을 "3. 배경 이미지 만들기" 섹션에 업로드
2. PC/모바일 캔버스에 각각 이미지와 크롭 박스(하늘색 테두리)가 보이는지 확인
3. 캔버스를 드래그해 크롭 박스 위치를 옮기면 박스가 이미지 밖으로 나가지 않는지 확인
4. "PC 배경 다운로드" 클릭 → `bg-pc-1920x700.png` 파일이 다운로드되는지 확인 (다운로드된 이미지를 열어 1920×700 크기인지 확인)
5. txt/exe 등 허용되지 않은 파일 업로드 시도 → "JPG, PNG, WEBP 파일만 업로드할 수 있습니다." 경고가 뜨는지 확인

- [ ] **Step 6: 커밋**

```bash
git add blog_widget_maker/cropper.js blog_widget_maker/app.js
git commit -m "feat(blog_widget_maker): 배경 이미지 크롭/다운로드 UI 추가"
```

---

## Task 7: URL 검증 경고 + 최종 점검

**Files:**
- Modify: `blog_widget_maker/app.js` (끝에 추가)

**Interfaces:**
- 없음 (최종 통합 태스크)

- [ ] **Step 1: `blog_widget_maker/app.js` 끝에 URL 검증 코드 추가**

```js
function isLikelyUrl(value) {
  return /^https?:\/\//i.test(value.trim());
}

function bindUrlWarning(inputId, warningId) {
  const input = el(inputId);
  const warning = el(warningId);
  input.addEventListener('blur', () => {
    warning.hidden = input.value.trim() === '' || isLikelyUrl(input.value);
  });
}

bindUrlWarning('profileImageUrl', 'profileImageUrlWarning');
```

- [ ] **Step 2: 브라우저에서 URL 검증 확인**

1. "프로필 이미지 URL" 필드에 `abc`를 입력하고 다른 필드로 포커스를 옮김(blur) → "http(s):// 로 시작하는 URL을 입력하세요" 경고가 보이는지 확인
2. 값을 `https://example.com/a.png`로 바꾸고 다시 blur → 경고가 사라지는지 확인
3. 필드를 비워두고 blur → 경고가 뜨지 않는지 확인 (빈 값은 강제하지 않음)

- [ ] **Step 3: 전체 회귀 테스트**

Run: `node --test blog_widget_maker/tests`
Expected: PASS (icons: 3, widget-templates: 5, cropper: 4 — 총 12개 테스트)

- [ ] **Step 4: 전체 수동 시나리오 재확인**

Task 5, 6에서 확인한 시나리오를 처음부터 한 번에 다시 실행해, 폼 입력 → 코드 실시간 갱신 → 복사 → 이미지 업로드 → 크롭 → 다운로드 → 체크리스트 체크박스 클릭까지 전체 흐름이 끊김 없이 동작하는지 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add blog_widget_maker/app.js
git commit -m "feat(blog_widget_maker): URL 형식 검증 경고 추가"
```

---

## Self-Review 결과

- **스펙 커버리지**: 정보 입력 폼(Task 1,5) / 배경 이미지 크롭 도구(Task 1,6) / 위젯 코드 생성기(Task 3,5) / 미리보기 패널(Task 5) / 단계별 체크리스트(Task 1) / 에러 처리 5항목(Task 6 파일검증, Task 7 URL경고, Task 5 메뉴5개제한·플레이스홀더, Task 5 클립보드 폴백) 모두 태스크로 매핑됨
- **플레이스홀더 스캔**: TBD/TODO 없음, 모든 코드 블록이 실행 가능한 완전한 코드임
- **타입/시그니처 일관성**: `state` 필드명(`blogName`, `quickLinks.home` 등)이 Task 5~7 전체에서 동일하게 사용됨. `ICON_KEYS`, `getIconSvg`, `renderProfileWidgetCode`, `renderMenuWidgetCode`, `computeInitialCropRect`, `clampCropRect`, `createCropController`, `TARGETS` 모두 정의한 태스크와 사용하는 태스크에서 이름이 일치함

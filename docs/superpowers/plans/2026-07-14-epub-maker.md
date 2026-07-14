# EPUB 메이커 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DOCX 원고를 넣으면 테마 디자인을 입힌 표준 EPUB3 전자책이 나오는 브라우저 단독 앱 (자가출판 플랫폼 등록 가능 품질).

**Architecture:** 순수 정적 웹앱(서버 없음). mammoth.js가 DOCX→HTML 변환, 자체 모듈이 챕터 분할·테마 CSS·EPUB3 파일 구조 생성·표준 검사를 담당, JSZip이 최종 ZIP 포장. DOM을 만지는 코드는 app.js에만 두고 나머지 모듈은 순수 함수로 작성해 Node 테스트로 검증한다.

**Tech Stack:** Vanilla JS (ES modules), mammoth.js 1.8 (vendor), JSZip 3.10 (vendor), node:test + node:assert/strict, python -m http.server (launch.bat)

**Spec:** `docs/superpowers/specs/2026-07-14-epub-maker-design.md`

## Global Constraints

- 완전 오프라인 동작: 외부 CDN 참조 금지, 라이브러리는 `epub_maker/vendor/`에 로컬 복사본
- Node 18+ 문법 사용 가능 (`crypto.randomUUID`, `atob` 전역 존재)
- 빌드 도구 없음: 브라우저가 ES 모듈을 직접 로드
- DOM 접근은 `app.js`(+ `cover.js`/`images.js`의 명시된 브라우저 전용 함수)에서만
- UI 문구·테스트 이름·커밋 메시지는 한국어, 커밋은 `feat(epub_maker): ...` 형식
- 테스트는 `node:test` + `node:assert/strict`, 실행은 `epub_maker/`에서 `node --test tests/`
- launch.bat 포트: **8400** (essay_helper=8300과 충돌 방지)
- EPUB 필수 메타데이터: 제목·저자·언어(기본 `ko`). 미입력 시 EPUB 생성 버튼 비활성
- KoPub 폰트 파일은 저장소에 커밋하지 않는다 (사용자가 `fonts/`에 직접 배치, 없으면 기기 기본 글꼴로 동작)

---

### Task 1: 프로젝트 뼈대 + vendor 라이브러리

**Files:**
- Create: `epub_maker/package.json`, `epub_maker/launch.bat`, `epub_maker/fonts/README.md`, `epub_maker/vendor/jszip.min.js`, `epub_maker/vendor/mammoth.browser.min.js`, `epub_maker/.gitignore`

**Interfaces:**
- Produces: 브라우저 전역 `window.JSZip`, `window.mammoth` (vendor 스크립트가 제공). 이후 모든 태스크의 작업 디렉터리 구조.

- [ ] **Step 1: 디렉터리와 package.json 생성**

```json
{
  "name": "epub-maker",
  "private": true,
  "type": "module"
}
```
경로: `epub_maker/package.json`

- [ ] **Step 2: vendor 라이브러리 다운로드**

```bash
cd C:/youtube/epub_maker
mkdir -p vendor fonts tests
curl -L -o vendor/jszip.min.js https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js
curl -L -o vendor/mammoth.browser.min.js https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.8.0/mammoth.browser.min.js
```
확인: 두 파일 크기가 각각 90KB 이상인지 (`ls -la vendor/`). 실패 시 jsdelivr(`https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js`, `https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js`)로 재시도.

- [ ] **Step 3: launch.bat 작성**

```bat
@echo off
rem EPUB Maker launcher: start local server (if not running) and open browser
netstat -ano | findstr ":8400" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "epub-maker-server" /min python -m http.server 8400 --directory "C:\youtube\epub_maker"
  ping -n 2 127.0.0.1 >nul
)
start "" http://localhost:8400/
```

- [ ] **Step 4: fonts/README.md 작성**

```markdown
# 글꼴 내장 안내

KoPub 글꼴(무료, 전자책 내장 허용)을 여기에 넣으면 EPUB에 내장됩니다.
없으면 "기기 기본 글꼴" 옵션만 동작합니다.

1. 한국출판인회의 KoPub 서체 배포처에서 KoPubWorld 바탕/돋움 TTF를 내려받습니다.
2. 아래 이름으로 바꿔 이 폴더에 넣습니다 (있는 것만 인식됨):
   - KoPubBatang-Light.ttf
   - KoPubBatang-Bold.ttf
   - KoPubDotum-Light.ttf
   - KoPubDotum-Bold.ttf
3. 글꼴 라이선스 고지는 EPUB 생성 시 자동으로 포함됩니다.
```

- [ ] **Step 5: .gitignore 작성**

```gitignore
fonts/*.ttf
fonts/*.otf
```
경로: `epub_maker/.gitignore`

- [ ] **Step 6: 커밋**

```bash
cd C:/youtube && git add epub_maker && git commit -m "chore(epub_maker): 프로젝트 뼈대와 vendor 라이브러리 추가"
```

---

### Task 2: themes.js — 테마 정의와 EPUB용 CSS 생성

**Files:**
- Create: `epub_maker/themes.js`
- Test: `epub_maker/tests/themes.test.js`

**Interfaces:**
- Produces:
  - `THEMES: { novel|practical|classic|minimal: { name: string, defaults: Options } }`
  - `themeDefaults(themeId: string): Options` (defaults의 복사본)
  - `buildThemeCss(options: Options, embeddedFonts?: {family,weight,file}[]): string`
  - `Options = { fontFamily:'kopub-batang'|'kopub-dotum'|'device', fontSize:number(%), lineHeight:number, paragraphSpacing:number(em), textIndent:number(em), sideMargin:number(%), headingAlign:'center'|'left', headingDivider:boolean, pageBreak:boolean }`

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/themes.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { THEMES, themeDefaults, buildThemeCss } from '../themes.js';

test('테마는 4종이고 각각 이름과 기본값을 가진다', () => {
  assert.deepEqual(Object.keys(THEMES), ['novel', 'practical', 'classic', 'minimal']);
  for (const t of Object.values(THEMES)) {
    assert.ok(t.name);
    assert.ok(t.defaults.fontFamily);
  }
});

test('themeDefaults는 복사본을 반환한다 (수정해도 원본 불변)', () => {
  const a = themeDefaults('novel');
  a.lineHeight = 999;
  assert.notEqual(THEMES.novel.defaults.lineHeight, 999);
});

test('소설 테마 CSS에 명조 글꼴·들여쓰기·가운데 제목이 반영된다', () => {
  const css = buildThemeCss(themeDefaults('novel'));
  assert.ok(css.includes('KoPub Batang'));
  assert.ok(css.includes('text-indent: 1em'));
  assert.ok(css.includes('text-align: center'));
});

test('실용 테마는 들여쓰기 대신 문단 간격을 쓴다', () => {
  const o = themeDefaults('practical');
  const css = buildThemeCss(o);
  assert.ok(css.includes('text-indent: 0em'));
  assert.ok(o.paragraphSpacing > 0);
});

test('클래식 테마는 제목 아래 장식 구분선을 넣는다', () => {
  const css = buildThemeCss(themeDefaults('classic'));
  assert.ok(css.includes('h1::after'));
});

test('pageBreak 옵션이 챕터 새 페이지 시작을 제어한다', () => {
  const on = buildThemeCss({ ...themeDefaults('novel'), pageBreak: true });
  const off = buildThemeCss({ ...themeDefaults('novel'), pageBreak: false });
  assert.ok(on.includes('page-break-before: always'));
  assert.ok(!off.includes('page-break-before'));
});

test('내장 글꼴 목록이 @font-face로 들어간다', () => {
  const css = buildThemeCss(themeDefaults('novel'), [
    { family: 'KoPub Batang', weight: 400, file: 'KoPubBatang-Light.ttf' },
  ]);
  assert.ok(css.includes('@font-face'));
  assert.ok(css.includes('url("fonts/KoPubBatang-Light.ttf")'));
});

test('device 글꼴 선택 시 KoPub 이름이 CSS에 없다', () => {
  const css = buildThemeCss({ ...themeDefaults('novel'), fontFamily: 'device' });
  assert.ok(!css.includes('KoPub'));
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd C:/youtube/epub_maker && node --test tests/themes.test.js`
Expected: FAIL (`Cannot find module '../themes.js'`)

- [ ] **Step 3: themes.js 구현**

```js
export const THEMES = {
  novel: {
    name: '소설·에세이',
    defaults: { fontFamily: 'kopub-batang', fontSize: 100, lineHeight: 1.9, paragraphSpacing: 0, textIndent: 1, sideMargin: 5, headingAlign: 'center', headingDivider: false, pageBreak: true },
  },
  practical: {
    name: '실용·자기계발',
    defaults: { fontFamily: 'kopub-dotum', fontSize: 100, lineHeight: 1.7, paragraphSpacing: 0.6, textIndent: 0, sideMargin: 4, headingAlign: 'left', headingDivider: false, pageBreak: true },
  },
  classic: {
    name: '클래식',
    defaults: { fontFamily: 'kopub-batang', fontSize: 100, lineHeight: 1.8, paragraphSpacing: 0, textIndent: 1, sideMargin: 6, headingAlign: 'center', headingDivider: true, pageBreak: true },
  },
  minimal: {
    name: '미니멀',
    defaults: { fontFamily: 'kopub-dotum', fontSize: 100, lineHeight: 1.7, paragraphSpacing: 0.8, textIndent: 0, sideMargin: 8, headingAlign: 'left', headingDivider: false, pageBreak: true },
  },
};

const FONT_STACKS = {
  'kopub-batang': '"KoPub Batang", serif',
  'kopub-dotum': '"KoPub Dotum", sans-serif',
  device: 'serif',
};

export function themeDefaults(themeId) {
  return { ...THEMES[themeId].defaults };
}

export function buildThemeCss(o, embeddedFonts = []) {
  const faces = embeddedFonts
    .map(f => `@font-face { font-family: "${f.family}"; font-weight: ${f.weight}; src: url("fonts/${f.file}"); }`)
    .join('\n');
  return `${faces}
body { font-family: ${FONT_STACKS[o.fontFamily]}; font-size: ${o.fontSize}%; line-height: ${o.lineHeight}; margin: 0 ${o.sideMargin}%; }
p { margin: 0 0 ${o.paragraphSpacing}em 0; text-indent: ${o.textIndent}em; text-align: justify; }
h1 { text-align: ${o.headingAlign}; font-size: 1.6em; line-height: 1.4; margin: 2.5em 0 1.5em;${o.pageBreak ? ' page-break-before: always;' : ''} }
${o.headingDivider ? 'h1::after { content: "\\2014 \\2756 \\2014"; display: block; font-size: 0.5em; margin-top: 0.8em; }\n' : ''}h2 { text-align: ${o.headingAlign}; font-size: 1.3em; margin: 2em 0 1em; }
img { max-width: 100%; }
figure { margin: 1em 0; text-align: center; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
td, th { border: 1px solid #999; padding: 0.4em; }
`;
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/themes.test.js`
Expected: PASS (8 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/themes.js epub_maker/tests/themes.test.js && git commit -m "feat(epub_maker): 테마 4종 정의와 EPUB용 CSS 생성"
```

---

### Task 3: docx-parser.js — 챕터 분할·이미지 추출·경고 요약

**Files:**
- Create: `epub_maker/docx-parser.js`
- Test: `epub_maker/tests/docx-parser.test.js`

**Interfaces:**
- Consumes: 없음 (mammoth 호출 자체는 app.js가 담당하고, 이 모듈은 mammoth의 결과 HTML/메시지를 가공)
- Produces:
  - `splitChapters(html: string): { title: string|null, html: string }[]` — h1 기준 분할, h1 없으면 전체가 title:null 단일 챕터, 첫 h1 앞 내용은 title:null 챕터
  - `extractImages(html: string): { html: string, images: { href, mediaType, base64 }[] }` — data URI를 `images/imgN.ext` 참조로 치환
  - `summarizeMessages(messages: {message:string}[]): string[]` — mammoth 경고를 한국어로, 중복 제거

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/docx-parser.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { splitChapters, extractImages, summarizeMessages } from '../docx-parser.js';

test('h1 기준으로 챕터가 나뉜다', () => {
  const html = '<h1>1장</h1><p>본문1</p><h1>2장</h1><p>본문2</p>';
  const ch = splitChapters(html);
  assert.equal(ch.length, 2);
  assert.equal(ch[0].title, '1장');
  assert.ok(ch[0].html.includes('본문1'));
  assert.equal(ch[1].title, '2장');
  assert.ok(ch[1].html.includes('본문2'));
});

test('h1이 없으면 전체가 제목 없는 단일 챕터가 된다', () => {
  const ch = splitChapters('<p>가</p><p>나</p>');
  assert.equal(ch.length, 1);
  assert.equal(ch[0].title, null);
});

test('첫 h1 앞의 내용은 별도 챕터로 보존된다', () => {
  const ch = splitChapters('<p>머리말</p><h1>1장</h1><p>본문</p>');
  assert.equal(ch.length, 2);
  assert.equal(ch[0].title, null);
  assert.ok(ch[0].html.includes('머리말'));
});

test('h1 안의 태그는 제목 텍스트에서 제거된다', () => {
  const ch = splitChapters('<h1><strong>강조</strong> 제목</h1><p>x</p>');
  assert.equal(ch[0].title, '강조 제목');
});

test('h1 앞 공백뿐인 내용은 챕터로 만들지 않는다', () => {
  const ch = splitChapters('<p> </p><h1>1장</h1><p>x</p>');
  assert.equal(ch.length, 1);
});

test('data URI 이미지가 파일 참조로 바뀌고 목록에 수집된다', () => {
  const html = '<p><img src="data:image/png;base64,AAAA" alt=""/></p>';
  const { html: out, images } = extractImages(html);
  assert.equal(images.length, 1);
  assert.equal(images[0].href, 'images/img1.png');
  assert.equal(images[0].mediaType, 'image/png');
  assert.equal(images[0].base64, 'AAAA');
  assert.ok(out.includes('src="images/img1.png"'));
  assert.ok(!out.includes('data:'));
});

test('이미지가 여러 개면 번호가 증가한다', () => {
  const html = '<img src="data:image/jpeg;base64,AA"/><img src="data:image/png;base64,BB"/>';
  const { images } = extractImages(html);
  assert.equal(images[0].href, 'images/img1.jpeg');
  assert.equal(images[1].href, 'images/img2.png');
});

test('mammoth 경고가 한국어로 요약되고 중복이 제거된다', () => {
  const out = summarizeMessages([
    { message: 'An unrecognised element was ignored: v:textbox' },
    { message: 'An unrecognised element was ignored: v:textbox' },
  ]);
  assert.equal(out.length, 1);
  assert.ok(out[0].includes('지원되지 않아'));
});

test('경고가 없으면 빈 배열을 반환한다', () => {
  assert.deepEqual(summarizeMessages([]), []);
  assert.deepEqual(summarizeMessages(undefined), []);
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/docx-parser.test.js`
Expected: FAIL (`Cannot find module '../docx-parser.js'`)

- [ ] **Step 3: docx-parser.js 구현**

```js
function stripTags(s) {
  return s.replace(/<[^>]*>/g, '');
}

export function splitChapters(html) {
  const re = /<h1[^>]*>([\s\S]*?)<\/h1>/g;
  const marks = [];
  let m;
  while ((m = re.exec(html)) !== null) {
    marks.push({ start: m.index, title: stripTags(m[1]).trim() });
  }
  if (marks.length === 0) return [{ title: null, html }];
  const chapters = [];
  const lead = html.slice(0, marks[0].start);
  if (stripTags(lead).trim()) chapters.push({ title: null, html: lead });
  marks.forEach((mark, i) => {
    const end = i + 1 < marks.length ? marks[i + 1].start : html.length;
    chapters.push({ title: mark.title || null, html: html.slice(mark.start, end) });
  });
  return chapters;
}

const EXT = { 'image/jpeg': 'jpeg', 'image/png': 'png', 'image/gif': 'gif' };

export function extractImages(html) {
  const images = [];
  const out = html.replace(
    /(<img[^>]*?src=")data:([^;"]+);base64,([^"]*)(")/g,
    (all, pre, mediaType, base64, post) => {
      const href = `images/img${images.length + 1}.${EXT[mediaType] || 'bin'}`;
      images.push({ href, mediaType, base64 });
      return pre + href + post;
    },
  );
  return { html: out, images };
}

const MESSAGE_RULES = [
  [/text box|textbox/i, '텍스트 상자는 본문 흐름으로 단순화되었습니다.'],
  [/column/i, '다단 배치는 한 단으로 합쳐졌습니다.'],
  [/style/i, '일부 문단 스타일이 기본 서식으로 바뀌었습니다.'],
];

export function summarizeMessages(messages) {
  const out = new Set();
  for (const msg of messages || []) {
    const hit = MESSAGE_RULES.find(([re]) => re.test(msg.message));
    out.add(hit ? hit[1] : '일부 요소가 지원되지 않아 단순화되었습니다.');
  }
  return [...out];
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/docx-parser.test.js`
Expected: PASS (9 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/docx-parser.js epub_maker/tests/docx-parser.test.js && git commit -m "feat(epub_maker): DOCX HTML 챕터 분할·이미지 추출·경고 요약"
```

---

### Task 4: epub-builder.js — EPUB3 파일 구조 조립

**Files:**
- Create: `epub_maker/epub-builder.js`
- Test: `epub_maker/tests/epub-builder.test.js`

**Interfaces:**
- Consumes: Task 2의 CSS 문자열(book.css로 전달받음), Task 3의 chapters/images 형태
- Produces:
  - `escapeXml(s: string): string`
  - `toXhtml(fragment: string): string` — img/br/hr 자기닫음, `&nbsp;` 수치 참조화
  - `buildEpubFiles(book): Map<string, string|Uint8Array>` — 경로→내용. `book = { meta: {title, author, language, isbn?, publisher?, pubDate?, description?, uuid?, modified?}, chapters: [{title, html}], images: [{href, mediaType, data}], cover: {href, mediaType, data}|null, css: string, fonts: [{file, family, weight, data}], licenseNote?: string }`
  - 생성 경로: `mimetype`, `META-INF/container.xml`, `OEBPS/content.opf`, `OEBPS/nav.xhtml`, `OEBPS/chapterN.xhtml`, `OEBPS/style.css`, `OEBPS/images/*`, `OEBPS/fonts/*`, (표지 시) `OEBPS/cover.xhtml`, (폰트 시) `OEBPS/fonts/LICENSE.txt`

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/epub-builder.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeXml, toXhtml, buildEpubFiles } from '../epub-builder.js';

function sampleBook(extra = {}) {
  return {
    meta: { title: '내 책', author: '홍길동', language: 'ko', uuid: '11111111-1111-4111-8111-111111111111', modified: '2026-07-14T00:00:00Z' },
    chapters: [
      { title: '1장', html: '<h1>1장</h1><p>본문 &amp; 내용</p>' },
      { title: '2장', html: '<h1>2장</h1><p><img src="images/img1.png" alt=""></p>' },
    ],
    images: [{ href: 'images/img1.png', mediaType: 'image/png', data: new Uint8Array([1]) }],
    cover: null,
    css: 'body{}',
    fonts: [],
    ...extra,
  };
}

test('escapeXml이 특수문자 5종을 이스케이프한다', () => {
  assert.equal(escapeXml(`<a & 'b' "c">`), '&lt;a &amp; &apos;b&apos; &quot;c&quot;&gt;');
});

test('toXhtml이 빈 요소를 자기닫음으로 바꾼다', () => {
  assert.equal(toXhtml('<img src="x.png" alt=""><br><hr>'), '<img src="x.png" alt=""/><br/><hr/>');
  assert.equal(toXhtml('<img src="x"/>'), '<img src="x"/>');
});

test('필수 파일이 모두 생성된다', () => {
  const files = buildEpubFiles(sampleBook());
  assert.equal(files.get('mimetype'), 'application/epub+zip');
  assert.ok(files.get('META-INF/container.xml').includes('full-path="OEBPS/content.opf"'));
  assert.ok(files.has('OEBPS/content.opf'));
  assert.ok(files.has('OEBPS/nav.xhtml'));
  assert.ok(files.has('OEBPS/chapter1.xhtml'));
  assert.ok(files.has('OEBPS/chapter2.xhtml'));
  assert.ok(files.has('OEBPS/style.css'));
  assert.ok(files.has('OEBPS/images/img1.png'));
});

test('OPF에 필수 메타데이터와 이스케이프된 제목이 들어간다', () => {
  const book = sampleBook();
  book.meta.title = '나 & 너';
  const opf = buildEpubFiles(book).get('OEBPS/content.opf');
  assert.ok(opf.includes('<dc:title>나 &amp; 너</dc:title>'));
  assert.ok(opf.includes('<dc:creator>홍길동</dc:creator>'));
  assert.ok(opf.includes('<dc:language>ko</dc:language>'));
  assert.ok(opf.includes('urn:uuid:11111111-1111-4111-8111-111111111111'));
  assert.ok(opf.includes('dcterms:modified">2026-07-14T00:00:00Z'));
});

test('선택 메타데이터는 입력했을 때만 들어간다', () => {
  const bare = buildEpubFiles(sampleBook()).get('OEBPS/content.opf');
  assert.ok(!bare.includes('dc:publisher'));
  const book = sampleBook();
  book.meta.isbn = '9791100000000';
  book.meta.publisher = '내출판사';
  const opf = buildEpubFiles(book).get('OEBPS/content.opf');
  assert.ok(opf.includes('urn:isbn:9791100000000'));
  assert.ok(opf.includes('<dc:publisher>내출판사</dc:publisher>'));
});

test('nav.xhtml 목차에 챕터 제목과 링크가 들어간다', () => {
  const nav = buildEpubFiles(sampleBook()).get('OEBPS/nav.xhtml');
  assert.ok(nav.includes('epub:type="toc"'));
  assert.ok(nav.includes('<a href="chapter1.xhtml">1장</a>'));
});

test('제목 없는 챕터는 목차에 "본문"으로 표시된다', () => {
  const book = sampleBook();
  book.chapters = [{ title: null, html: '<p>x</p>' }];
  const nav = buildEpubFiles(book).get('OEBPS/nav.xhtml');
  assert.ok(nav.includes('>본문</a>'));
});

test('표지가 있으면 cover.xhtml과 cover-image 속성이 생긴다', () => {
  const book = sampleBook({ cover: { href: 'images/cover.jpg', mediaType: 'image/jpeg', data: new Uint8Array([2]) } });
  const files = buildEpubFiles(book);
  assert.ok(files.has('OEBPS/cover.xhtml'));
  const opf = files.get('OEBPS/content.opf');
  assert.ok(opf.includes('properties="cover-image"'));
  assert.ok(/<spine>\s*<itemref idref="cover"\/>/.test(opf));
});

test('폰트가 있으면 파일·매니페스트·라이선스 고지가 들어간다', () => {
  const book = sampleBook({
    fonts: [{ file: 'KoPubBatang-Light.ttf', family: 'KoPub Batang', weight: 400, data: new Uint8Array([3]) }],
    licenseNote: 'KoPub 서체 라이선스 고지',
  });
  const files = buildEpubFiles(book);
  assert.ok(files.has('OEBPS/fonts/KoPubBatang-Light.ttf'));
  assert.ok(files.has('OEBPS/fonts/LICENSE.txt'));
  assert.ok(files.get('OEBPS/content.opf').includes('href="fonts/KoPubBatang-Light.ttf"'));
});

test('챕터 XHTML은 XML 선언과 자기닫음 img를 가진다', () => {
  const ch2 = buildEpubFiles(sampleBook()).get('OEBPS/chapter2.xhtml');
  assert.ok(ch2.startsWith('<?xml'));
  assert.ok(ch2.includes('<img src="images/img1.png" alt=""/>'));
});

test('uuid를 주지 않으면 자동 생성된다', () => {
  const book = sampleBook();
  delete book.meta.uuid;
  const opf = buildEpubFiles(book).get('OEBPS/content.opf');
  assert.ok(/urn:uuid:[0-9a-f-]{36}/.test(opf));
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/epub-builder.test.js`
Expected: FAIL (`Cannot find module '../epub-builder.js'`)

- [ ] **Step 3: epub-builder.js 구현**

```js
export function escapeXml(s) {
  return String(s).replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]));
}

export function toXhtml(fragment) {
  return fragment
    .replace(/<(img|br|hr)([^>]*?)\s*\/?>/g, '<$1$2/>')
    .replace(/&nbsp;/g, '&#160;');
}

function xhtmlDoc(title, bodyFragment) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ko">
<head><title>${escapeXml(title || '')}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>${toXhtml(bodyFragment)}</body>
</html>`;
}

function navDoc(chapters, hasCover) {
  const cover = hasCover ? '<li><a href="cover.xhtml">표지</a></li>' : '';
  const items = chapters.map(ch => `<li><a href="${ch.href}">${escapeXml(ch.title || '본문')}</a></li>`).join('');
  return xhtmlDoc('목차', `<nav epub:type="toc"><h1>목차</h1><ol>${cover}${items}</ol></nav>`);
}

function opfDoc(book, chapters) {
  const m = book.meta;
  const uuid = m.uuid || crypto.randomUUID();
  const modified = (m.modified || new Date().toISOString()).replace(/\.\d+Z$/, 'Z');
  const items = [
    '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
    '<item id="css" href="style.css" media-type="text/css"/>',
    ...chapters.map(ch => `<item id="${ch.id}" href="${ch.href}" media-type="application/xhtml+xml"/>`),
    ...(book.images || []).map((img, i) => `<item id="img${i + 1}" href="${img.href}" media-type="${img.mediaType}"/>`),
    ...(book.fonts || []).map((f, i) => `<item id="font${i + 1}" href="fonts/${f.file}" media-type="font/ttf"/>`),
  ];
  if (book.fonts && book.fonts.length) items.push('<item id="font-license" href="fonts/LICENSE.txt" media-type="text/plain"/>');
  if (book.cover) {
    items.push(`<item id="cover-image" href="${book.cover.href}" media-type="${book.cover.mediaType}" properties="cover-image"/>`);
    items.push('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>');
  }
  const spine = [
    ...(book.cover ? ['<itemref idref="cover"/>'] : []),
    ...chapters.map(ch => `<itemref idref="${ch.id}"/>`),
  ];
  const opt = [];
  if (m.isbn) opt.push(`<dc:identifier>urn:isbn:${escapeXml(m.isbn)}</dc:identifier>`);
  if (m.publisher) opt.push(`<dc:publisher>${escapeXml(m.publisher)}</dc:publisher>`);
  if (m.pubDate) opt.push(`<dc:date>${escapeXml(m.pubDate)}</dc:date>`);
  if (m.description) opt.push(`<dc:description>${escapeXml(m.description)}</dc:description>`);
  return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="${m.language}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:${uuid}</dc:identifier>
    <dc:title>${escapeXml(m.title)}</dc:title>
    <dc:creator>${escapeXml(m.author)}</dc:creator>
    <dc:language>${m.language}</dc:language>
    <meta property="dcterms:modified">${modified}</meta>
    ${opt.join('\n    ')}
  </metadata>
  <manifest>
    ${items.join('\n    ')}
  </manifest>
  <spine>
    ${spine.join('\n    ')}
  </spine>
</package>`;
}

export function buildEpubFiles(book) {
  const files = new Map();
  files.set('mimetype', 'application/epub+zip');
  files.set('META-INF/container.xml', `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>`);
  const chapters = book.chapters.map((ch, i) => ({ ...ch, id: `ch${i + 1}`, href: `chapter${i + 1}.xhtml` }));
  chapters.forEach(ch => files.set(`OEBPS/${ch.href}`, xhtmlDoc(ch.title || book.meta.title, ch.html)));
  files.set('OEBPS/style.css', book.css);
  (book.images || []).forEach(img => files.set(`OEBPS/${img.href}`, img.data));
  (book.fonts || []).forEach(f => files.set(`OEBPS/fonts/${f.file}`, f.data));
  if (book.fonts && book.fonts.length) {
    files.set('OEBPS/fonts/LICENSE.txt', book.licenseNote || 'KoPubWorld 서체: (사)한국출판인회의 배포, 전자책 내장 허용 라이선스.');
  }
  if (book.cover) {
    files.set(`OEBPS/${book.cover.href}`, book.cover.data);
    files.set('OEBPS/cover.xhtml', xhtmlDoc(book.meta.title, `<figure class="cover"><img src="${book.cover.href}" alt="표지"/></figure>`));
  }
  files.set('OEBPS/nav.xhtml', navDoc(chapters, !!book.cover));
  files.set('OEBPS/content.opf', opfDoc(book, chapters));
  return files;
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/epub-builder.test.js`
Expected: PASS (11 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/epub-builder.js epub_maker/tests/epub-builder.test.js && git commit -m "feat(epub_maker): EPUB3 파일 구조 조립기"
```

---

### Task 5: epub-validator.js — 표준 자동 검사

**Files:**
- Create: `epub_maker/epub-validator.js`
- Test: `epub_maker/tests/epub-validator.test.js`

**Interfaces:**
- Consumes: `buildEpubFiles`가 반환한 `Map<string, string|Uint8Array>`
- Produces: `validateEpub(files: Map): { ok: boolean, errors: string[] }` — 오류 메시지는 한국어

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/epub-validator.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildEpubFiles } from '../epub-builder.js';
import { validateEpub } from '../epub-validator.js';

function goodFiles() {
  return buildEpubFiles({
    meta: { title: '책', author: '나', language: 'ko' },
    chapters: [{ title: '1장', html: '<h1>1장</h1><p>x</p>' }],
    images: [],
    cover: null,
    css: 'body{}',
    fonts: [],
  });
}

test('정상 EPUB 파일 구조는 통과한다', () => {
  const r = validateEpub(goodFiles());
  assert.deepEqual(r, { ok: true, errors: [] });
});

test('mimetype이 잘못되면 실패한다', () => {
  const files = goodFiles();
  files.set('mimetype', 'text/plain');
  const r = validateEpub(files);
  assert.equal(r.ok, false);
  assert.ok(r.errors.some(e => e.includes('mimetype')));
});

test('container.xml이 없으면 실패한다', () => {
  const files = goodFiles();
  files.delete('META-INF/container.xml');
  assert.equal(validateEpub(files).ok, false);
});

test('매니페스트가 가리키는 파일이 없으면 실패한다', () => {
  const files = goodFiles();
  files.delete('OEBPS/chapter1.xhtml');
  const r = validateEpub(files);
  assert.ok(r.errors.some(e => e.includes('chapter1.xhtml')));
});

test('필수 메타데이터가 빠지면 실패한다', () => {
  const files = goodFiles();
  files.set('OEBPS/content.opf', files.get('OEBPS/content.opf').replace(/<dc:title>.*<\/dc:title>/, ''));
  const r = validateEpub(files);
  assert.ok(r.errors.some(e => e.includes('dc:title')));
});

test('nav 문서 지정이 없으면 실패한다', () => {
  const files = goodFiles();
  files.set('OEBPS/content.opf', files.get('OEBPS/content.opf').replace(' properties="nav"', ''));
  const r = validateEpub(files);
  assert.ok(r.errors.some(e => e.includes('nav')));
});

test('spine이 존재하지 않는 id를 가리키면 실패한다', () => {
  const files = goodFiles();
  files.set('OEBPS/content.opf', files.get('OEBPS/content.opf').replace('idref="ch1"', 'idref="ghost"'));
  const r = validateEpub(files);
  assert.ok(r.errors.some(e => e.includes('ghost')));
});

test('XHTML에 XML 선언이 없으면 실패한다', () => {
  const files = goodFiles();
  files.set('OEBPS/chapter1.xhtml', files.get('OEBPS/chapter1.xhtml').replace(/^<\?xml[^>]*\?>\n?/, ''));
  const r = validateEpub(files);
  assert.ok(r.errors.some(e => e.includes('chapter1.xhtml')));
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/epub-validator.test.js`
Expected: FAIL (`Cannot find module '../epub-validator.js'`)

- [ ] **Step 3: epub-validator.js 구현**

```js
export function validateEpub(files) {
  const errors = [];
  if (files.get('mimetype') !== 'application/epub+zip') {
    errors.push('mimetype 파일이 없거나 내용이 잘못되었습니다.');
  }
  const container = files.get('META-INF/container.xml') || '';
  const pathMatch = /full-path="([^"]+)"/.exec(container);
  if (!pathMatch) {
    errors.push('META-INF/container.xml이 없거나 OPF 경로를 찾을 수 없습니다.');
    return { ok: false, errors };
  }
  const opfPath = pathMatch[1];
  const opf = files.get(opfPath);
  if (!opf) {
    errors.push(`패키지 문서(${opfPath})가 없습니다.`);
    return { ok: false, errors };
  }
  for (const tag of ['dc:title', 'dc:identifier', 'dc:language']) {
    if (!opf.includes(`<${tag}`)) errors.push(`필수 정보 <${tag}>가 없습니다.`);
  }
  if (!opf.includes('dcterms:modified')) errors.push('수정 시각(dcterms:modified)이 없습니다.');

  const base = opfPath.replace(/[^/]+$/, '');
  const ids = new Set();
  let hasNav = false;
  for (const [tag] of opf.matchAll(/<item\s[^>]*\/>/g)) {
    const href = /href="([^"]+)"/.exec(tag)?.[1];
    const id = /\bid="([^"]+)"/.exec(tag)?.[1];
    if (id) ids.add(id);
    if (/properties="[^"]*\bnav\b[^"]*"/.test(tag)) hasNav = true;
    if (href && !files.has(base + href)) errors.push(`목록에 있는 파일이 실제로 없습니다: ${href}`);
  }
  if (!hasNav) errors.push('목차(nav) 문서가 지정되지 않았습니다.');
  for (const m of opf.matchAll(/<itemref\s[^>]*idref="([^"]+)"/g)) {
    if (!ids.has(m[1])) errors.push(`읽기 순서(spine)가 존재하지 않는 항목을 가리킵니다: ${m[1]}`);
  }
  for (const [path, content] of files) {
    if (path.endsWith('.xhtml') && !String(content).startsWith('<?xml')) {
      errors.push(`${path.replace(base, '')}: XML 선언이 없습니다.`);
    }
  }
  return { ok: errors.length === 0, errors };
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/epub-validator.test.js`
Expected: PASS (8 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/epub-validator.js epub_maker/tests/epub-validator.test.js && git commit -m "feat(epub_maker): EPUB 표준 자동 검사기"
```

---

### Task 6: cover.js — 표지 규격 검사와 자동 생성

**Files:**
- Create: `epub_maker/cover.js`
- Test: `epub_maker/tests/cover.test.js`

**Interfaces:**
- Produces:
  - `checkCoverSpec({width, height}): { ok: boolean, warnings: string[] }` (순수, 테스트 대상)
  - `drawCover(canvas, {title, author, themeId}): void` (브라우저 전용 — canvas 2D에 1600×2400 표지를 그림)

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/cover.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkCoverSpec } from '../cover.js';

test('권장 규격(1600x2400)은 경고 없이 통과한다', () => {
  assert.deepEqual(checkCoverSpec({ width: 1600, height: 2400 }), { ok: true, warnings: [] });
});

test('가로 1000px 미만이면 해상도 경고가 나온다', () => {
  const r = checkCoverSpec({ width: 800, height: 1200 });
  assert.equal(r.ok, false);
  assert.ok(r.warnings.some(w => w.includes('1000px')));
});

test('가로가 세로보다 길면 비율 경고가 나온다', () => {
  const r = checkCoverSpec({ width: 2000, height: 1500 });
  assert.ok(r.warnings.some(w => w.includes('비율')));
});

test('경계값: 비율 1.2와 1.7은 통과한다', () => {
  assert.equal(checkCoverSpec({ width: 1000, height: 1200 }).ok, true);
  assert.equal(checkCoverSpec({ width: 1000, height: 1700 }).ok, true);
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/cover.test.js`
Expected: FAIL (`Cannot find module '../cover.js'`)

- [ ] **Step 3: cover.js 구현**

```js
export function checkCoverSpec({ width, height }) {
  const warnings = [];
  if (width < 1000) warnings.push(`표지 가로가 ${width}px입니다. 1000px 이상을 권장합니다.`);
  const ratio = height / width;
  if (ratio < 1.2 || ratio > 1.7) {
    warnings.push('표지 비율은 세로가 긴 형태(가로:세로 = 1:1.2 ~ 1:1.7)를 권장합니다.');
  }
  return { ok: warnings.length === 0, warnings };
}

const PALETTES = {
  novel: { bg: '#2C3639', fg: '#F5EDE3' },
  practical: { bg: '#0C447C', fg: '#FFFFFF' },
  classic: { bg: '#4A1B0C', fg: '#F5EDE3' },
  minimal: { bg: '#F5F5F2', fg: '#222222' },
};

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(/\s+/);
  let line = '';
  for (const word of words) {
    const probe = line ? `${line} ${word}` : word;
    if (ctx.measureText(probe).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = probe;
    }
  }
  ctx.fillText(line, x, y);
  return y;
}

export function drawCover(canvas, { title, author, themeId }) {
  const p = PALETTES[themeId] || PALETTES.novel;
  canvas.width = 1600;
  canvas.height = 2400;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = p.bg;
  ctx.fillRect(0, 0, 1600, 2400);
  ctx.fillStyle = p.fg;
  ctx.textAlign = 'center';
  ctx.font = 'bold 130px sans-serif';
  wrapText(ctx, title || '제목', 800, 850, 1300, 170);
  ctx.fillRect(700, 1780, 200, 4);
  ctx.font = '64px sans-serif';
  ctx.fillText(author || '', 800, 1940);
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/cover.test.js`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/cover.js epub_maker/tests/cover.test.js && git commit -m "feat(epub_maker): 표지 규격 검사와 자동 생성"
```

---

### Task 7: images.js — 이미지 압축 판단과 변환

**Files:**
- Create: `epub_maker/images.js`
- Test: `epub_maker/tests/images.test.js`

**Interfaces:**
- Produces:
  - `planImageOutput({width, byteLength, keepOriginal}): { resize: boolean, targetWidth?: number, quality?: number }` (순수)
  - `base64ToBytes(b64: string): Uint8Array` (순수 — Node 18+ 전역 `atob` 사용)
  - `compressImage(base64, mediaType, plan): Promise<{data: Uint8Array, mediaType: string}>` (브라우저 전용 — canvas로 리사이즈, JPEG 품질 plan.quality로 재인코딩. plan.resize가 false면 원본 바이트 반환)

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/images.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { planImageOutput, base64ToBytes } from '../images.js';

test('작은 이미지는 압축하지 않는다', () => {
  assert.deepEqual(planImageOutput({ width: 800, byteLength: 100 * 1024 }), { resize: false });
});

test('가로 1600px 초과면 1600으로 줄인다', () => {
  const p = planImageOutput({ width: 3000, byteLength: 100 * 1024 });
  assert.equal(p.resize, true);
  assert.equal(p.targetWidth, 1600);
  assert.equal(p.quality, 0.8);
});

test('500KB 초과면 크기 유지하고 재압축한다', () => {
  const p = planImageOutput({ width: 1200, byteLength: 900 * 1024 });
  assert.equal(p.resize, true);
  assert.equal(p.targetWidth, 1200);
});

test('원본 유지 옵션이면 어떤 경우에도 압축하지 않는다', () => {
  assert.deepEqual(planImageOutput({ width: 5000, byteLength: 10 * 1024 * 1024, keepOriginal: true }), { resize: false });
});

test('base64ToBytes가 바이트 배열로 변환한다', () => {
  assert.deepEqual(base64ToBytes('AQID'), new Uint8Array([1, 2, 3]));
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/images.test.js`
Expected: FAIL (`Cannot find module '../images.js'`)

- [ ] **Step 3: images.js 구현**

```js
const MAX_WIDTH = 1600;
const MAX_BYTES = 500 * 1024;

export function planImageOutput({ width, byteLength, keepOriginal = false }) {
  if (keepOriginal) return { resize: false };
  if (width > MAX_WIDTH || byteLength > MAX_BYTES) {
    return { resize: true, targetWidth: Math.min(width, MAX_WIDTH), quality: 0.8 };
  }
  return { resize: false };
}

export function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export async function compressImage(base64, mediaType, plan) {
  if (!plan.resize) return { data: base64ToBytes(base64), mediaType };
  const img = await new Promise((resolve, reject) => {
    const el = new Image();
    el.onload = () => resolve(el);
    el.onerror = reject;
    el.src = `data:${mediaType};base64,${base64}`;
  });
  const scale = plan.targetWidth / img.naturalWidth;
  const canvas = document.createElement('canvas');
  canvas.width = plan.targetWidth;
  canvas.height = Math.round(img.naturalHeight * scale);
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', plan.quality));
  return { data: new Uint8Array(await blob.arrayBuffer()), mediaType: 'image/jpeg' };
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/images.test.js`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
cd C:/youtube && git add epub_maker/images.js epub_maker/tests/images.test.js && git commit -m "feat(epub_maker): 이미지 압축 판단·변환"
```

---

### Task 8: storage.js — 설정 자동 저장

**Files:**
- Create: `epub_maker/storage.js`
- Test: `epub_maker/tests/storage.test.js`

**Interfaces:**
- Produces: `createSettingsStore(backing): { save(state), load(): state|null }` — backing은 localStorage 호환 객체(`getItem`/`setItem`). 저장 키 `epub_maker_state_v1`. 저장 대상은 `{ meta, themeId, options, coverMode, keepOriginalImages }` (원고·이미지 데이터는 저장하지 않음).

- [ ] **Step 1: 실패하는 테스트 작성** (`epub_maker/tests/storage.test.js`)

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createSettingsStore } from '../storage.js';

function fakeBacking() {
  const m = new Map();
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) };
}

test('저장한 설정을 그대로 복원한다', () => {
  const store = createSettingsStore(fakeBacking());
  const state = { meta: { title: '책' }, themeId: 'classic', options: { lineHeight: 2 } };
  store.save(state);
  assert.deepEqual(store.load(), state);
});

test('저장된 것이 없으면 null을 반환한다', () => {
  assert.equal(createSettingsStore(fakeBacking()).load(), null);
});

test('깨진 JSON이 저장돼 있으면 null을 반환한다 (예외 없음)', () => {
  const backing = fakeBacking();
  backing.setItem('epub_maker_state_v1', '{깨짐');
  assert.equal(createSettingsStore(backing).load(), null);
});

test('setItem이 예외를 던져도 save는 조용히 넘어간다', () => {
  const store = createSettingsStore({ getItem: () => null, setItem: () => { throw new Error('꽉 참'); } });
  assert.doesNotThrow(() => store.save({ a: 1 }));
});
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/storage.test.js`
Expected: FAIL (`Cannot find module '../storage.js'`)

- [ ] **Step 3: storage.js 구현**

```js
const KEY = 'epub_maker_state_v1';

export function createSettingsStore(backing) {
  return {
    save(state) {
      try { backing.setItem(KEY, JSON.stringify(state)); } catch { /* 저장 실패는 치명적이지 않음 */ }
    },
    load() {
      try {
        const raw = backing.getItem(KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    },
  };
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/storage.test.js`
Expected: PASS (4 tests)

- [ ] **Step 5: 전체 테스트 일괄 확인 후 커밋**

Run: `node --test tests/`
Expected: 전체 PASS

```bash
cd C:/youtube && git add epub_maker/storage.js epub_maker/tests/storage.test.js && git commit -m "feat(epub_maker): 설정 localStorage 저장·복원"
```

---

### Task 9: index.html + style.css — 앱 화면 뼈대

**Files:**
- Create: `epub_maker/index.html`, `epub_maker/style.css`

**Interfaces:**
- Produces: app.js(Task 10)가 참조할 DOM id들 — `#drop-zone`, `#file-input`, `#meta-form`(내부 input들: `#meta-title #meta-author #meta-isbn #meta-publisher #meta-pubdate #meta-description`), `#cover-mode`(select: auto/upload/none), `#cover-file`, `#cover-preview`(canvas), `#cover-warnings`, `#chapter-list`, `#preview-frame`(iframe), `#theme-list`, `#opt-font #opt-fontsize #opt-lineheight #opt-paraspacing #opt-indent #opt-margin #opt-headingalign #opt-divider #opt-pagebreak #opt-keeporiginal`, `#messages`, `#validation`, `#btn-download`, `#step-indicator`

- [ ] **Step 1: index.html 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EPUB 메이커</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>EPUB 메이커</h1>
  <ol id="step-indicator">
    <li class="active">1. 문서 올리기</li>
    <li>2. 디자인 꾸미기</li>
    <li>3. EPUB 내려받기</li>
  </ol>
</header>
<main>
  <aside class="panel-left">
    <section id="upload-section">
      <div id="drop-zone" role="button" tabindex="0" aria-label="DOCX 파일 올리기">
        <p>DOCX 파일을 끌어다 놓거나<br>클릭해서 선택하세요</p>
        <input type="file" id="file-input" accept=".docx,.doc" hidden>
      </div>
      <ul id="messages" aria-live="polite"></ul>
    </section>
    <section>
      <h2>책 정보</h2>
      <form id="meta-form">
        <label>제목 * <input id="meta-title" required></label>
        <label>저자 * <input id="meta-author" required></label>
        <label>ISBN <input id="meta-isbn" placeholder="9791100000000"></label>
        <label>출판사 <input id="meta-publisher"></label>
        <label>발행일 <input id="meta-pubdate" type="date"></label>
        <label>책 소개 <textarea id="meta-description" rows="3"></textarea></label>
      </form>
    </section>
    <section>
      <h2>표지</h2>
      <label>방식
        <select id="cover-mode">
          <option value="auto">자동 생성 (제목·저자)</option>
          <option value="upload">이미지 업로드</option>
          <option value="none">표지 없음</option>
        </select>
      </label>
      <input type="file" id="cover-file" accept="image/jpeg,image/png" hidden>
      <canvas id="cover-preview" width="160" height="240" aria-label="표지 미리보기"></canvas>
      <ul id="cover-warnings" aria-live="polite"></ul>
    </section>
    <section>
      <h2>챕터</h2>
      <ol id="chapter-list"></ol>
    </section>
  </aside>
  <section class="panel-center">
    <iframe id="preview-frame" title="전자책 미리보기"></iframe>
  </section>
  <aside class="panel-right">
    <section>
      <h2>테마</h2>
      <div id="theme-list" role="radiogroup" aria-label="테마 선택"></div>
    </section>
    <section>
      <h2>세부 조정</h2>
      <label>글꼴
        <select id="opt-font">
          <option value="kopub-batang">KoPub 바탕 (명조)</option>
          <option value="kopub-dotum">KoPub 돋움 (고딕)</option>
          <option value="device">기기 기본 글꼴</option>
        </select>
      </label>
      <label>글자 크기 <input type="range" id="opt-fontsize" min="85" max="130" step="5"> <output for="opt-fontsize"></output>%</label>
      <label>줄 간격 <input type="range" id="opt-lineheight" min="1.4" max="2.4" step="0.1"> <output for="opt-lineheight"></output></label>
      <label>문단 간격 <input type="range" id="opt-paraspacing" min="0" max="1.5" step="0.1"> <output for="opt-paraspacing"></output>em</label>
      <label>들여쓰기 <input type="range" id="opt-indent" min="0" max="2" step="0.5"> <output for="opt-indent"></output>em</label>
      <label>좌우 여백 <input type="range" id="opt-margin" min="0" max="12" step="1"> <output for="opt-margin"></output>%</label>
      <label>제목 정렬
        <select id="opt-headingalign"><option value="center">가운데</option><option value="left">왼쪽</option></select>
      </label>
      <label><input type="checkbox" id="opt-divider"> 제목 아래 장식 구분선</label>
      <label><input type="checkbox" id="opt-pagebreak"> 챕터를 새 페이지에서 시작</label>
      <label><input type="checkbox" id="opt-keeporiginal"> 이미지 원본 유지 (압축 안 함)</label>
    </section>
    <section>
      <button id="btn-download" disabled>EPUB 만들기</button>
      <ul id="validation" aria-live="polite"></ul>
    </section>
  </aside>
</main>
<script src="vendor/mammoth.browser.min.js"></script>
<script src="vendor/jszip.min.js"></script>
<script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: style.css 작성**

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: "Malgun Gothic", sans-serif; background: #f4f2ee; color: #222; }
header { display: flex; align-items: center; gap: 24px; padding: 12px 20px; background: #fff; border-bottom: 1px solid #ddd; }
header h1 { font-size: 18px; margin: 0; }
#step-indicator { display: flex; gap: 16px; list-style: none; margin: 0; padding: 0; font-size: 13px; color: #888; }
#step-indicator .active { color: #1d6ee0; font-weight: 700; }
main { display: grid; grid-template-columns: 280px 1fr 260px; gap: 12px; padding: 12px 20px; height: calc(100vh - 57px); }
.panel-left, .panel-right { overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
section { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
section h2 { font-size: 14px; margin: 0 0 10px; }
#drop-zone { border: 2px dashed #bbb; border-radius: 8px; padding: 24px 12px; text-align: center; color: #777; cursor: pointer; font-size: 13px; }
#drop-zone.dragover { border-color: #1d6ee0; background: #eef4fd; }
label { display: block; font-size: 12px; margin-bottom: 8px; color: #555; }
input:not([type=checkbox]):not([type=range]), select, textarea { width: 100%; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; margin-top: 2px; }
input[type=range] { width: 60%; vertical-align: middle; }
.panel-center { display: flex; }
#preview-frame { flex: 1; border: 1px solid #ddd; border-radius: 8px; background: #fff; }
#theme-list label { display: flex; align-items: center; gap: 6px; padding: 8px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 6px; cursor: pointer; font-size: 13px; }
#theme-list label.selected { border-color: #1d6ee0; background: #eef4fd; }
#chapter-list { margin: 0; padding-left: 20px; font-size: 13px; }
#chapter-list li { cursor: pointer; padding: 3px 0; }
#chapter-list li.current { color: #1d6ee0; font-weight: 700; }
#cover-preview { width: 100%; max-width: 160px; border: 1px solid #ddd; border-radius: 4px; display: block; margin-top: 8px; }
#messages, #validation, #cover-warnings { list-style: none; padding: 0; margin: 8px 0 0; font-size: 12px; }
#messages li { color: #8a5a00; background: #fff6e5; border-radius: 4px; padding: 6px 8px; margin-bottom: 4px; }
#validation li.error { color: #a32d2d; background: #fceded; border-radius: 4px; padding: 6px 8px; margin-bottom: 4px; }
#validation li.ok { color: #0f6e56; background: #e6f5ef; border-radius: 4px; padding: 6px 8px; }
#cover-warnings li { color: #8a5a00; }
#btn-download { width: 100%; padding: 12px; font-size: 15px; font-weight: 700; color: #fff; background: #1d6ee0; border: 0; border-radius: 8px; cursor: pointer; }
#btn-download:disabled { background: #b9c6d8; cursor: not-allowed; }
```

- [ ] **Step 3: 브라우저에서 뼈대 확인**

launch.bat 또는 dev 서버로 `http://localhost:8400/` 열어 3패널 레이아웃이 그려지는지 확인 (콘솔에 app.js 404 오류는 정상 — 다음 태스크에서 작성).

- [ ] **Step 4: 커밋**

```bash
cd C:/youtube && git add epub_maker/index.html epub_maker/style.css && git commit -m "feat(epub_maker): 3패널 앱 화면 뼈대"
```

---

### Task 10: app.js — 전체 배선

**Files:**
- Create: `epub_maker/app.js`
- Create: `epub_maker/tests/make_sample_docx.py` (수동 검증용 샘플 생성)

**Interfaces:**
- Consumes: Task 2~8의 모든 공개 함수 (`THEMES, themeDefaults, buildThemeCss`, `splitChapters, extractImages, summarizeMessages`, `buildEpubFiles`, `validateEpub`, `checkCoverSpec, drawCover`, `planImageOutput, base64ToBytes, compressImage`, `createSettingsStore`), 전역 `window.mammoth`, `window.JSZip`, Task 9의 DOM id들
- Produces: 완성된 앱 (사용자용 최종 산출물)

- [ ] **Step 1: app.js 작성**

```js
import { THEMES, themeDefaults, buildThemeCss } from './themes.js';
import { splitChapters, extractImages, summarizeMessages } from './docx-parser.js';
import { buildEpubFiles } from './epub-builder.js';
import { validateEpub } from './epub-validator.js';
import { checkCoverSpec, drawCover } from './cover.js';
import { planImageOutput, base64ToBytes, compressImage } from './images.js';
import { createSettingsStore } from './storage.js';

const $ = id => document.getElementById(id);
const store = createSettingsStore(window.localStorage);

const FONT_FILES = [
  { file: 'KoPubBatang-Light.ttf', family: 'KoPub Batang', weight: 400 },
  { file: 'KoPubBatang-Bold.ttf', family: 'KoPub Batang', weight: 700 },
  { file: 'KoPubDotum-Light.ttf', family: 'KoPub Dotum', weight: 400 },
  { file: 'KoPubDotum-Bold.ttf', family: 'KoPub Dotum', weight: 700 },
];

const state = {
  meta: { title: '', author: '', language: 'ko', isbn: '', publisher: '', pubDate: '', description: '' },
  themeId: 'novel',
  options: themeDefaults('novel'),
  coverMode: 'auto',
  keepOriginalImages: false,
  chapters: [],
  images: [],
  messages: [],
  uploadedCover: null,
  currentChapter: 0,
  availableFonts: [],
};

// ---------- 초기화 ----------

async function init() {
  const saved = store.load();
  if (saved) {
    Object.assign(state.meta, saved.meta || {});
    state.themeId = saved.themeId || 'novel';
    state.options = { ...themeDefaults(state.themeId), ...(saved.options || {}) };
    state.coverMode = saved.coverMode || 'auto';
    state.keepOriginalImages = !!saved.keepOriginalImages;
  }
  state.availableFonts = await detectFonts();
  renderThemeList();
  bindMetaForm();
  bindOptions();
  bindUpload();
  bindCover();
  bindDownload();
  syncOptionInputs();
  renderCover();
  renderPreview();
  updateDownloadEnabled();
}

async function detectFonts() {
  const out = [];
  for (const f of FONT_FILES) {
    try {
      const res = await fetch(`fonts/${f.file}`, { method: 'HEAD' });
      if (res.ok) out.push(f);
    } catch { /* 폰트 없음: 기기 기본 글꼴로 동작 */ }
  }
  return out;
}

function persist() {
  store.save({
    meta: state.meta,
    themeId: state.themeId,
    options: state.options,
    coverMode: state.coverMode,
    keepOriginalImages: state.keepOriginalImages,
  });
}

// ---------- 문서 업로드 ----------

function bindUpload() {
  const zone = $('drop-zone');
  const input = $('file-input');
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') input.click(); });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files[0]) handleFile(input.files[0]); });
}

async function handleFile(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.doc') && !name.endsWith('.docx')) {
    showMessages(['구형 .doc 형식은 지원하지 않습니다. 워드에서 "다른 이름으로 저장 → Word 문서(.docx)"로 저장한 뒤 다시 올려주세요.']);
    return;
  }
  if (!name.endsWith('.docx')) {
    showMessages(['.docx 파일만 올릴 수 있습니다.']);
    return;
  }
  showMessages(['변환 중...']);
  try {
    const arrayBuffer = await file.arrayBuffer();
    const result = await window.mammoth.convertToHtml({ arrayBuffer });
    const extracted = extractImages(result.value);
    let html = extracted.html;
    const images = [];
    for (const img of extracted.images) {
      const bytes = base64ToBytes(img.base64);
      const size = await imageSize(img.base64, img.mediaType);
      const plan = planImageOutput({ width: size.width, byteLength: bytes.length, keepOriginal: state.keepOriginalImages });
      const out = await compressImage(img.base64, img.mediaType, plan);
      let href = img.href;
      if (out.mediaType !== img.mediaType) {
        const newHref = href.replace(/\.\w+$/, '.jpeg');
        html = html.split(href).join(newHref);
        href = newHref;
      }
      images.push({ href, mediaType: out.mediaType, data: out.data, base64ForPreview: img.base64, originalType: img.mediaType });
    }
    state.images = images;
    state.chapters = splitChapters(html);
    state.messages = summarizeMessages(result.messages);
    if (state.chapters.length === 1 && state.chapters[0].title === null) {
      state.messages.push('제목 스타일을 찾지 못해 책 전체가 한 챕터가 되었습니다. 워드에서 챕터 제목에 "제목 1" 스타일을 적용하면 자동으로 나뉩니다.');
    }
    state.currentChapter = 0;
    setStep(2);
    showMessages(state.messages);
    renderChapterList();
    renderPreview();
    updateDownloadEnabled();
  } catch (err) {
    showMessages([`문서를 읽지 못했습니다: ${err.message}`]);
  }
}

function imageSize(base64, mediaType) {
  return new Promise(resolve => {
    const el = new Image();
    el.onload = () => resolve({ width: el.naturalWidth, height: el.naturalHeight });
    el.onerror = () => resolve({ width: 0, height: 0 });
    el.src = `data:${mediaType};base64,${base64}`;
  });
}

// ---------- 책 정보 ----------

const META_FIELDS = [
  ['meta-title', 'title'], ['meta-author', 'author'], ['meta-isbn', 'isbn'],
  ['meta-publisher', 'publisher'], ['meta-pubdate', 'pubDate'], ['meta-description', 'description'],
];

function bindMetaForm() {
  for (const [id, key] of META_FIELDS) {
    const el = $(id);
    el.value = state.meta[key] || '';
    el.addEventListener('input', () => {
      state.meta[key] = el.value.trim();
      persist();
      updateDownloadEnabled();
      if (state.coverMode === 'auto' && (key === 'title' || key === 'author')) renderCover();
    });
  }
}

// ---------- 테마·옵션 ----------

function renderThemeList() {
  const box = $('theme-list');
  box.innerHTML = '';
  for (const [id, theme] of Object.entries(THEMES)) {
    const label = document.createElement('label');
    label.className = id === state.themeId ? 'selected' : '';
    label.innerHTML = `<input type="radio" name="theme" value="${id}" ${id === state.themeId ? 'checked' : ''}> ${theme.name}`;
    label.querySelector('input').addEventListener('change', () => {
      state.themeId = id;
      state.options = themeDefaults(id);
      persist();
      renderThemeList();
      syncOptionInputs();
      renderCover();
      renderPreview();
    });
    box.appendChild(label);
  }
}

const OPTION_INPUTS = [
  ['opt-font', 'fontFamily', 'select'], ['opt-fontsize', 'fontSize', 'number'],
  ['opt-lineheight', 'lineHeight', 'number'], ['opt-paraspacing', 'paragraphSpacing', 'number'],
  ['opt-indent', 'textIndent', 'number'], ['opt-margin', 'sideMargin', 'number'],
  ['opt-headingalign', 'headingAlign', 'select'], ['opt-divider', 'headingDivider', 'checkbox'],
  ['opt-pagebreak', 'pageBreak', 'checkbox'],
];

function bindOptions() {
  for (const [id, key, kind] of OPTION_INPUTS) {
    $(id).addEventListener('input', () => {
      const el = $(id);
      state.options[key] = kind === 'checkbox' ? el.checked : kind === 'number' ? Number(el.value) : el.value;
      persist();
      syncOutputs();
      renderPreview();
    });
  }
  $('opt-keeporiginal').addEventListener('change', () => {
    state.keepOriginalImages = $('opt-keeporiginal').checked;
    persist();
    if (state.chapters.length) showMessages([...state.messages, '이미지 압축 설정이 바뀌었습니다. 문서를 다시 올리면 적용됩니다.']);
  });
}

function syncOptionInputs() {
  for (const [id, key, kind] of OPTION_INPUTS) {
    const el = $(id);
    if (kind === 'checkbox') el.checked = !!state.options[key];
    else el.value = state.options[key];
  }
  $('opt-keeporiginal').checked = state.keepOriginalImages;
  if (state.availableFonts.length === 0) {
    for (const opt of $('opt-font').options) {
      if (opt.value !== 'device') { opt.disabled = true; opt.text += ' (fonts 폴더에 파일 없음)'; }
    }
    state.options.fontFamily = 'device';
    $('opt-font').value = 'device';
  }
  syncOutputs();
}

function syncOutputs() {
  for (const out of document.querySelectorAll('output')) {
    out.textContent = $(out.getAttribute('for')).value;
  }
}

// ---------- 표지 ----------

function bindCover() {
  $('cover-mode').value = state.coverMode;
  $('cover-mode').addEventListener('change', () => {
    state.coverMode = $('cover-mode').value;
    persist();
    if (state.coverMode === 'upload') $('cover-file').click();
    renderCover();
  });
  $('cover-file').addEventListener('change', async () => {
    const file = $('cover-file').files[0];
    if (!file) return;
    const bitmap = await createImageBitmap(file);
    const check = checkCoverSpec({ width: bitmap.width, height: bitmap.height });
    renderList($('cover-warnings'), check.warnings);
    state.uploadedCover = { data: new Uint8Array(await file.arrayBuffer()), mediaType: file.type, bitmap };
    renderCover();
  });
}

function renderCover() {
  const canvas = $('cover-preview');
  const ctx = canvas.getContext('2d');
  canvas.width = 160; canvas.height = 240;
  ctx.clearRect(0, 0, 160, 240);
  if (state.coverMode === 'none') return;
  if (state.coverMode === 'upload' && state.uploadedCover) {
    ctx.drawImage(state.uploadedCover.bitmap, 0, 0, 160, 240);
  } else if (state.coverMode === 'auto') {
    const big = document.createElement('canvas');
    drawCover(big, { title: state.meta.title, author: state.meta.author, themeId: state.themeId });
    ctx.drawImage(big, 0, 0, 160, 240);
  }
}

async function buildCoverForEpub() {
  if (state.coverMode === 'none') return null;
  if (state.coverMode === 'upload' && state.uploadedCover) {
    const ext = state.uploadedCover.mediaType === 'image/png' ? 'png' : 'jpg';
    return { href: `images/cover.${ext}`, mediaType: state.uploadedCover.mediaType, data: state.uploadedCover.data };
  }
  const canvas = document.createElement('canvas');
  drawCover(canvas, { title: state.meta.title, author: state.meta.author, themeId: state.themeId });
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  return { href: 'images/cover.jpg', mediaType: 'image/jpeg', data: new Uint8Array(await blob.arrayBuffer()) };
}

// ---------- 미리보기 ----------

function embeddedFontsForCss() {
  const want = state.options.fontFamily === 'kopub-batang' ? 'KoPub Batang' : state.options.fontFamily === 'kopub-dotum' ? 'KoPub Dotum' : null;
  return want ? state.availableFonts.filter(f => f.family === want) : [];
}

function renderChapterList() {
  const list = $('chapter-list');
  list.innerHTML = '';
  state.chapters.forEach((ch, i) => {
    const li = document.createElement('li');
    li.textContent = ch.title || '(제목 없는 본문)';
    li.className = i === state.currentChapter ? 'current' : '';
    li.addEventListener('click', () => { state.currentChapter = i; renderChapterList(); renderPreview(); });
    list.appendChild(li);
  });
}

function renderPreview() {
  const css = buildThemeCss(state.options, embeddedFontsForCss());
  const ch = state.chapters[state.currentChapter];
  let html = ch ? ch.html : '<p style="color:#888">문서를 올리면 미리보기가 여기 표시됩니다.</p>';
  for (const img of state.images) {
    html = html.split(`src="${img.href}"`).join(`src="data:${img.originalType};base64,${img.base64ForPreview}"`);
  }
  $('preview-frame').srcdoc = `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>${css}</style></head><body>${html}</body></html>`;
}

// ---------- 생성·다운로드 ----------

function updateDownloadEnabled() {
  const ready = state.chapters.length > 0 && state.meta.title && state.meta.author;
  $('btn-download').disabled = !ready;
  $('btn-download').title = ready ? '' : '문서를 올리고 제목·저자를 입력하면 활성화됩니다.';
}

function bindDownload() {
  $('btn-download').addEventListener('click', async () => {
    const fonts = [];
    for (const f of embeddedFontsForCss()) {
      const res = await fetch(`fonts/${f.file}`);
      fonts.push({ ...f, data: new Uint8Array(await res.arrayBuffer()) });
    }
    const book = {
      meta: state.meta,
      chapters: state.chapters,
      images: state.images.map(({ href, mediaType, data }) => ({ href, mediaType, data })),
      cover: await buildCoverForEpub(),
      css: buildThemeCss(state.options, fonts),
      fonts,
    };
    const files = buildEpubFiles(book);
    const check = validateEpub(files);
    const box = $('validation');
    box.innerHTML = '';
    if (!check.ok) {
      for (const e of check.errors) {
        const li = document.createElement('li');
        li.className = 'error';
        li.textContent = e;
        box.appendChild(li);
      }
      return;
    }
    const zip = new window.JSZip();
    zip.file('mimetype', files.get('mimetype'), { compression: 'STORE' });
    for (const [path, content] of files) {
      if (path !== 'mimetype') zip.file(path, content);
    }
    const blob = await zip.generateAsync({ type: 'blob', mimeType: 'application/epub+zip', compression: 'DEFLATE' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${state.meta.title || 'book'}.epub`;
    a.click();
    URL.revokeObjectURL(a.href);
    const li = document.createElement('li');
    li.className = 'ok';
    li.textContent = '표준 검사를 통과했습니다. EPUB이 다운로드되었습니다.';
    box.appendChild(li);
    setStep(3);
  });
}

// ---------- 공용 UI ----------

function setStep(n) {
  document.querySelectorAll('#step-indicator li').forEach((li, i) => {
    li.classList.toggle('active', i === n - 1);
  });
}

function showMessages(list) {
  renderList($('messages'), list);
}

function renderList(el, items) {
  el.innerHTML = '';
  for (const text of items) {
    const li = document.createElement('li');
    li.textContent = text;
    el.appendChild(li);
  }
}

init();
```

- [ ] **Step 2: 수동 검증용 샘플 DOCX 생성 스크립트 작성** (`epub_maker/tests/make_sample_docx.py`)

```python
"""표준 라이브러리만으로 최소 DOCX 샘플을 만든다. 실행: python tests/make_sample_docx.py"""
import zipfile

DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>1장 시작</w:t></w:r></w:p>
<w:p><w:r><w:t>첫 챕터의 본문입니다. 강산이 &amp; 바다가 있다.</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>2장 여정</w:t></w:r></w:p>
<w:p><w:r><w:t>두 번째 챕터의 본문입니다.</w:t></w:r></w:p>
</w:body></w:document>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

with zipfile.ZipFile("tests/sample.docx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CONTENT_TYPES)
    z.writestr("_rels/.rels", RELS)
    z.writestr("word/_rels/document.xml.rels", DOC_RELS)
    z.writestr("word/document.xml", DOCUMENT)
    z.writestr("word/styles.xml", STYLES)
print("tests/sample.docx 생성 완료")
```

- [ ] **Step 3: 샘플 생성 후 브라우저 종단 검증**

```bash
cd C:/youtube/epub_maker && python tests/make_sample_docx.py
```

브라우저(`http://localhost:8400/`)에서:
1. `tests/sample.docx` 업로드 → 챕터 목록에 "1장 시작", "2장 여정" 표시 확인
2. 제목·저자 입력 → "EPUB 만들기" 버튼 활성화 확인
3. 테마 변경·슬라이더 조정 → 미리보기 즉시 반영 확인
4. "EPUB 만들기" 클릭 → 검사 통과 메시지 + .epub 다운로드 확인
5. 콘솔 오류 0건 확인

- [ ] **Step 4: 전체 테스트 재확인 후 커밋**

Run: `cd C:/youtube/epub_maker && node --test tests/`
Expected: 전체 PASS

```bash
cd C:/youtube && git add epub_maker/app.js epub_maker/tests/make_sample_docx.py && git commit -m "feat(epub_maker): 앱 전체 배선 (업로드→디자인→EPUB 생성)"
```

---

### Task 11: README + 최종 수동 검증

**Files:**
- Create: `epub_maker/README.md`

**Interfaces:**
- Consumes: 완성된 앱 전체

- [ ] **Step 1: README.md 작성**

```markdown
# EPUB 메이커

DOCX 원고를 넣으면 디자인을 입힌 표준 EPUB 전자책을 만들어 주는 브라우저 앱.
부크크 같은 자가출판 플랫폼에 등록 가능한 EPUB3 규격을 목표로 한다.

## 실행

launch.bat 더블클릭 (또는 `python -m http.server 8400 --directory epub_maker` 후 http://localhost:8400 접속).
인터넷 연결 불필요.

## 사용법

1. **문서 올리기** — .docx 파일을 끌어다 놓는다. 워드에서 챕터 제목에
   "제목 1" 스타일을 적용해 두면 챕터가 자동으로 나뉜다.
2. **책 정보** — 제목·저자(필수), ISBN·출판사·발행일·소개(선택) 입력.
3. **표지** — 이미지 업로드(권장: 가로 1000px 이상, 세로가 긴 비율) 또는
   제목·저자 기반 자동 생성.
4. **디자인** — 테마 4종 중 선택 후 글꼴·크기·줄 간격·여백 등 조정.
   미리보기에 즉시 반영된다.
5. **EPUB 만들기** — 표준 검사를 통과하면 .epub이 다운로드된다.

## 글꼴 내장

fonts/README.md 참고. KoPub TTF를 fonts/에 넣으면 EPUB에 내장된다.
없으면 "기기 기본 글꼴"로 동작한다.

## 개발

- 테스트: `node --test tests/`
- 샘플 DOCX 생성: `python tests/make_sample_docx.py`
- 최종 확인(선택): [epubcheck](https://github.com/w3c/epubcheck) 설치 후
  `java -jar epubcheck.jar 생성파일.epub`
```

- [ ] **Step 2: 전체 테스트 + 브라우저 최종 점검**

```bash
cd C:/youtube/epub_maker && node --test tests/
```
Expected: 전체 PASS

브라우저에서 한 번 더: 새로고침 후 저장된 설정(테마·책 정보)이 복원되는지 확인.

- [ ] **Step 3: (선택) epubcheck 공식 검증**

Java가 설치되어 있으면:
```bash
java -jar epubcheck.jar 다운로드된책.epub
```
Expected: `No errors or warnings detected` (없으면 이 단계는 건너뛰고 리디북스 뷰어/Calibre에서 열어 확인)

- [ ] **Step 4: 커밋**

```bash
cd C:/youtube && git add epub_maker/README.md && git commit -m "docs(epub_maker): README 추가"
```

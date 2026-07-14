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

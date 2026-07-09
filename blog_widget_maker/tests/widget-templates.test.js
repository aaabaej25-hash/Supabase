import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml, renderProfileWidgetCode, renderMenuWidgetCode } from '../widget-templates.js';

test('escapeHtml escapes special characters', () => {
  assert.equal(escapeHtml(`<b>"a" & 'b'</b>`), '&lt;b&gt;&quot;a&quot; &amp; &#39;b&#39;&lt;/b&gt;');
});

test('renderProfileWidgetCode shows placeholder when blogName is empty', () => {
  const html = renderProfileWidgetCode({
    blogName: '', slogan: '', hours: '', profileImageUrl: '', bgColor: '#ffffff',
    menus: [],
  });
  assert.match(html, /블로그명을 입력하세요/);
});

test('renderProfileWidgetCode includes escaped blog name, image url and bg color', () => {
  const html = renderProfileWidgetCode({
    blogName: '<script>', slogan: '슬로건', hours: '24시간', profileImageUrl: 'https://x.com/a.png',
    bgColor: '#000000', menus: [],
  });
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /https:\/\/x\.com\/a\.png/);
  assert.match(html, /background:#000000/);
});

test('renderProfileWidgetCode quicklink icons mirror the menu list (icon + url, up to 5)', () => {
  const menus = Array.from({ length: 7 }, (_, i) => ({ icon: 'map', text: `카테고리${i}`, url: `https://x.com/${i}` }));
  const html = renderProfileWidgetCode({
    blogName: '블로그', slogan: '', hours: '', profileImageUrl: '', bgColor: '#ffffff', menus,
  });
  const matches = html.match(/class="bwm-quicklink"/g) || [];
  assert.equal(matches.length, 5);
  assert.match(html, /https:\/\/x\.com\/0/);
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

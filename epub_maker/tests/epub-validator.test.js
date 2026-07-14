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

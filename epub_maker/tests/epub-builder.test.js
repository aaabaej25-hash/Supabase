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

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

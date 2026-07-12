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

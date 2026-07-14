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

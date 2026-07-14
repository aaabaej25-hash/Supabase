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

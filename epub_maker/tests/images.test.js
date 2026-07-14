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

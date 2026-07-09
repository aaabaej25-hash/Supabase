import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeInitialCropRect, clampCropRect } from '../cropper.js';

test('computeInitialCropRect centers a wide crop inside a taller image', () => {
  const rect = computeInitialCropRect(1000, 1000, 1920 / 700);
  assert.ok(Math.abs(rect.width / rect.height - 1920 / 700) < 0.001);
  assert.equal(rect.x, 0);
  assert.ok(rect.y > 0);
});

test('computeInitialCropRect centers a square crop inside a wider image', () => {
  const rect = computeInitialCropRect(2000, 500, 1);
  assert.ok(Math.abs(rect.width / rect.height - 1) < 0.001);
  assert.equal(rect.y, 0);
  assert.ok(rect.x > 0);
});

test('clampCropRect keeps rect within image bounds', () => {
  const rect = clampCropRect({ x: -50, y: 9999, width: 300, height: 200 }, 1000, 800);
  assert.equal(rect.x, 0);
  assert.equal(rect.y, 600);
  assert.equal(rect.width, 300);
  assert.equal(rect.height, 200);
});

test('clampCropRect shrinks a rect larger than the image', () => {
  const rect = clampCropRect({ x: 0, y: 0, width: 5000, height: 4000 }, 1000, 800);
  assert.equal(rect.width, 1000);
  assert.equal(rect.height, 800);
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ICONS, ICON_KEYS, getIconSvg } from '../icons.js';

test('every icon key maps to an svg string', () => {
  for (const key of ICON_KEYS) {
    assert.match(ICONS[key], /^<svg/);
  }
});

test('getIconSvg falls back to etc icon for unknown key', () => {
  assert.equal(getIconSvg('unknown-key'), ICONS.etc);
});

test('getIconSvg returns matching icon for known key', () => {
  assert.equal(getIconSvg('home'), ICONS.home);
});

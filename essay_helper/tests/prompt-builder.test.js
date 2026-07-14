import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPrompt } from '../prompt-builder.js';
import { ROLE_PREAMBLE, STYLE_GUIDES, PLATFORM_GUIDES } from '../prompts.js';

test('항상 역할 정의(ROLE_PREAMBLE)로 시작한다', () => {
  const prompt = buildPrompt({ original: '내 에세이' });
  assert.ok(prompt.startsWith(ROLE_PREAMBLE));
});

test('원문이 프롬프트 말미에 구분자와 함께 포함된다', () => {
  const prompt = buildPrompt({ original: '오늘 퇴근길에 문득 생각했다.' });
  assert.ok(prompt.endsWith('원문:\n"""\n오늘 퇴근길에 문득 생각했다.\n"""'));
});

test('선택한 스타일 지침만 포함된다', () => {
  const prompt = buildPrompt({ original: '글', styles: ['psychology', 'worker'] });
  assert.ok(prompt.includes(STYLE_GUIDES.psychology.text));
  assert.ok(prompt.includes(STYLE_GUIDES.worker.text));
  assert.ok(!prompt.includes(STYLE_GUIDES.hooking.text));
  assert.ok(!prompt.includes(STYLE_GUIDES.warmth.text));
});

test('스타일을 하나도 선택하지 않으면 스타일 지침 섹션이 없다', () => {
  const prompt = buildPrompt({ original: '글', styles: [] });
  assert.ok(!prompt.includes('스타일 지침:'));
});

test('알 수 없는 스타일 id는 무시한다', () => {
  const prompt = buildPrompt({ original: '글', styles: ['nonsense'] });
  assert.ok(!prompt.includes('스타일 지침:'));
});

test('상황 텍스트를 입력하면 상황 설정 섹션에 반영된다', () => {
  const prompt = buildPrompt({ original: '글', situation: '이직을 고민하는 후배에게 하는 말처럼' });
  assert.ok(prompt.includes('상황 설정:\n- 이직을 고민하는 후배에게 하는 말처럼'));
});

test('상황 텍스트가 공백뿐이면 상황 설정 섹션이 없다', () => {
  const prompt = buildPrompt({ original: '글', situation: '   ' });
  assert.ok(!prompt.includes('상황 설정:'));
});

test('선택한 플랫폼 가이드가 모두 포함된다', () => {
  const prompt = buildPrompt({ original: '글', platforms: ['naver', 'brunch'] });
  assert.ok(prompt.includes(PLATFORM_GUIDES.naver.text));
  assert.ok(prompt.includes(PLATFORM_GUIDES.brunch.text));
  assert.ok(!prompt.includes(PLATFORM_GUIDES.instagram.text));
});

test('플랫폼 미선택 시 general 가이드가 기본으로 들어간다', () => {
  const prompt = buildPrompt({ original: '글', platforms: [] });
  assert.ok(prompt.includes(PLATFORM_GUIDES.general.text));
});

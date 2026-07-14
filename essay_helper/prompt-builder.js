import { ROLE_PREAMBLE, STYLE_GUIDES, PLATFORM_GUIDES } from './prompts.js';

export function buildPrompt({ original, styles = [], situation = '', platforms = [] }) {
  const sections = [ROLE_PREAMBLE];

  const styleTexts = styles
    .filter((id) => STYLE_GUIDES[id])
    .map((id) => STYLE_GUIDES[id].text);
  if (styleTexts.length > 0) {
    sections.push('스타일 지침:\n' + styleTexts.join('\n'));
  }

  const trimmedSituation = situation.trim();
  if (trimmedSituation) {
    sections.push('상황 설정:\n- ' + trimmedSituation);
  }

  const platformIds = platforms.filter((id) => PLATFORM_GUIDES[id]);
  const effectivePlatforms = platformIds.length > 0 ? platformIds : ['general'];
  sections.push(
    '형식 가이드:\n' + effectivePlatforms.map((id) => PLATFORM_GUIDES[id].text).join('\n')
  );

  sections.push('원문:\n"""\n' + original + '\n"""');

  return sections.join('\n\n');
}

export const THEMES = {
  novel: {
    name: '소설·에세이',
    defaults: { fontFamily: 'kopub-batang', fontSize: 100, lineHeight: 1.9, paragraphSpacing: 0, textIndent: 1, sideMargin: 5, headingAlign: 'center', headingDivider: false, pageBreak: true },
  },
  practical: {
    name: '실용·자기계발',
    defaults: { fontFamily: 'kopub-dotum', fontSize: 100, lineHeight: 1.7, paragraphSpacing: 0.6, textIndent: 0, sideMargin: 4, headingAlign: 'left', headingDivider: false, pageBreak: true },
  },
  classic: {
    name: '클래식',
    defaults: { fontFamily: 'kopub-batang', fontSize: 100, lineHeight: 1.8, paragraphSpacing: 0, textIndent: 1, sideMargin: 6, headingAlign: 'center', headingDivider: true, pageBreak: true },
  },
  minimal: {
    name: '미니멀',
    defaults: { fontFamily: 'kopub-dotum', fontSize: 100, lineHeight: 1.7, paragraphSpacing: 0.8, textIndent: 0, sideMargin: 8, headingAlign: 'left', headingDivider: false, pageBreak: true },
  },
};

const FONT_STACKS = {
  'kopub-batang': '"KoPub Batang", serif',
  'kopub-dotum': '"KoPub Dotum", sans-serif',
  device: 'serif',
};

export function themeDefaults(themeId) {
  return { ...THEMES[themeId].defaults };
}

export function buildThemeCss(o, embeddedFonts = []) {
  const faces = embeddedFonts
    .map(f => `@font-face { font-family: "${f.family}"; font-weight: ${f.weight}; src: url("fonts/${f.file}"); }`)
    .join('\n');
  return `${faces}
body { font-family: ${FONT_STACKS[o.fontFamily]}; font-size: ${o.fontSize}%; line-height: ${o.lineHeight}; margin: 0 ${o.sideMargin}%; }
p { margin: 0 0 ${o.paragraphSpacing}em 0; text-indent: ${o.textIndent}em; text-align: justify; }
h1 { text-align: ${o.headingAlign}; font-size: 1.6em; line-height: 1.4; margin: 2.5em 0 1.5em;${o.pageBreak ? ' page-break-before: always;' : ''} }
${o.headingDivider ? 'h1::after { content: "\\2014 \\2756 \\2014"; display: block; font-size: 0.5em; margin-top: 0.8em; }\n' : ''}h2 { text-align: ${o.headingAlign}; font-size: 1.3em; margin: 2em 0 1em; }
img { max-width: 100%; }
figure { margin: 1em 0; text-align: center; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
td, th { border: 1px solid #999; padding: 0.4em; }
`;
}

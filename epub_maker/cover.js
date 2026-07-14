export function checkCoverSpec({ width, height }) {
  const warnings = [];
  if (width < 1000) warnings.push(`표지 가로가 ${width}px입니다. 1000px 이상을 권장합니다.`);
  const ratio = height / width;
  if (ratio < 1.2 || ratio > 1.7) {
    warnings.push('표지 비율은 세로가 긴 형태(가로:세로 = 1:1.2 ~ 1:1.7)를 권장합니다.');
  }
  return { ok: warnings.length === 0, warnings };
}

const PALETTES = {
  novel: { bg: '#2C3639', fg: '#F5EDE3' },
  practical: { bg: '#0C447C', fg: '#FFFFFF' },
  classic: { bg: '#4A1B0C', fg: '#F5EDE3' },
  minimal: { bg: '#F5F5F2', fg: '#222222' },
};

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(/\s+/);
  let line = '';
  for (const word of words) {
    const probe = line ? `${line} ${word}` : word;
    if (ctx.measureText(probe).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = probe;
    }
  }
  ctx.fillText(line, x, y);
  return y;
}

export function drawCover(canvas, { title, author, themeId }) {
  const p = PALETTES[themeId] || PALETTES.novel;
  canvas.width = 1600;
  canvas.height = 2400;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = p.bg;
  ctx.fillRect(0, 0, 1600, 2400);
  ctx.fillStyle = p.fg;
  ctx.textAlign = 'center';
  ctx.font = 'bold 130px sans-serif';
  wrapText(ctx, title || '제목', 800, 850, 1300, 170);
  ctx.fillRect(700, 1780, 200, 4);
  ctx.font = '64px sans-serif';
  ctx.fillText(author || '', 800, 1940);
}

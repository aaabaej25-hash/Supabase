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

export function breakLines(text, maxWidth, measure, maxLines = 4) {
  const lines = [];
  let line = '';
  for (const ch of String(text).trim()) {
    const probe = line + ch;
    if (measure(probe) > maxWidth && line) {
      lines.push(line);
      if (lines.length === maxLines) return { lines, truncated: true };
      line = ch === ' ' ? '' : ch;
    } else {
      line = probe;
    }
  }
  if (line) lines.push(line);
  return { lines, truncated: false };
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
  const { lines, truncated } = breakLines(title || '제목', 1300, t => ctx.measureText(t).width);
  if (truncated) lines[lines.length - 1] += '…';
  let y = 850;
  for (const ln of lines) {
    ctx.fillText(ln, 800, y);
    y += 170;
  }
  ctx.fillRect(700, y + 60, 200, 4);
  ctx.font = '64px sans-serif';
  ctx.fillText(author || '', 800, y + 220);
}

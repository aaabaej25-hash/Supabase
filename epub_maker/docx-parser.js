function stripTags(s) {
  return s.replace(/<[^>]*>/g, '');
}

export function splitChapters(html) {
  const re = /<h1[^>]*>([\s\S]*?)<\/h1>/g;
  const marks = [];
  let m;
  while ((m = re.exec(html)) !== null) {
    marks.push({ start: m.index, title: stripTags(m[1]).trim() });
  }
  if (marks.length === 0) return [{ title: null, html }];
  const chapters = [];
  const lead = html.slice(0, marks[0].start);
  if (stripTags(lead).trim()) chapters.push({ title: null, html: lead });
  marks.forEach((mark, i) => {
    const end = i + 1 < marks.length ? marks[i + 1].start : html.length;
    chapters.push({ title: mark.title || null, html: html.slice(mark.start, end) });
  });
  return chapters;
}

const EXT = { 'image/jpeg': 'jpeg', 'image/png': 'png', 'image/gif': 'gif' };

export function extractImages(html) {
  const images = [];
  const out = html.replace(
    /(<img[^>]*?src=")data:([^;"]+);base64,([^"]*)(")/g,
    (all, pre, mediaType, base64, post) => {
      const href = `images/img${images.length + 1}.${EXT[mediaType] || 'bin'}`;
      images.push({ href, mediaType, base64 });
      return pre + href + post;
    },
  );
  return { html: out, images };
}

const MESSAGE_RULES = [
  [/\btext\s+box\b/i, '텍스트 상자는 본문 흐름으로 단순화되었습니다.'],
  [/column/i, '다단 배치는 한 단으로 합쳐졌습니다.'],
  [/style/i, '일부 문단 스타일이 기본 서식으로 바뀌었습니다.'],
];

export function summarizeMessages(messages) {
  const out = new Set();
  for (const msg of messages || []) {
    const hit = MESSAGE_RULES.find(([re]) => re.test(msg.message));
    out.add(hit ? hit[1] : '일부 요소가 지원되지 않아 단순화되었습니다.');
  }
  return [...out];
}

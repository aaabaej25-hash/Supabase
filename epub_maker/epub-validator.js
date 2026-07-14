export function validateEpub(files) {
  const errors = [];
  if (files.get('mimetype') !== 'application/epub+zip') {
    errors.push('mimetype 파일이 없거나 내용이 잘못되었습니다.');
  }
  const container = files.get('META-INF/container.xml') || '';
  const pathMatch = /full-path="([^"]+)"/.exec(container);
  if (!pathMatch) {
    errors.push('META-INF/container.xml이 없거나 OPF 경로를 찾을 수 없습니다.');
    return { ok: false, errors };
  }
  const opfPath = pathMatch[1];
  const opf = files.get(opfPath);
  if (!opf) {
    errors.push(`패키지 문서(${opfPath})가 없습니다.`);
    return { ok: false, errors };
  }
  for (const tag of ['dc:title', 'dc:identifier', 'dc:language']) {
    if (!opf.includes(`<${tag}`)) errors.push(`필수 정보 <${tag}>가 없습니다.`);
  }
  if (!opf.includes('dcterms:modified')) errors.push('수정 시각(dcterms:modified)이 없습니다.');

  const base = opfPath.replace(/[^/]+$/, '');
  const ids = new Set();
  let hasNav = false;
  for (const [tag] of opf.matchAll(/<item\s[^>]*\/>/g)) {
    const href = /href="([^"]+)"/.exec(tag)?.[1];
    const id = /\bid="([^"]+)"/.exec(tag)?.[1];
    if (id) ids.add(id);
    if (/properties="[^"]*\bnav\b[^"]*"/.test(tag)) hasNav = true;
    if (href && !files.has(base + href)) errors.push(`목록에 있는 파일이 실제로 없습니다: ${href}`);
  }
  if (!hasNav) errors.push('목차(nav) 문서가 지정되지 않았습니다.');
  for (const m of opf.matchAll(/<itemref\s[^>]*idref="([^"]+)"/g)) {
    if (!ids.has(m[1])) errors.push(`읽기 순서(spine)가 존재하지 않는 항목을 가리킵니다: ${m[1]}`);
  }
  for (const [path, content] of files) {
    if (path.endsWith('.xhtml') && !String(content).startsWith('<?xml')) {
      errors.push(`${path.replace(base, '')}: XML 선언이 없습니다.`);
    }
  }
  return { ok: errors.length === 0, errors };
}

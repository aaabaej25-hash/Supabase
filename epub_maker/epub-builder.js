export function escapeXml(s) {
  return String(s).replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]));
}

export function toXhtml(fragment) {
  return fragment
    .replace(/<(img|br|hr)([^>]*?)\s*\/?>/g, '<$1$2/>')
    .replace(/&nbsp;/g, '&#160;');
}

function xhtmlDoc(title, bodyFragment) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ko">
<head><title>${escapeXml(title || '')}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>${toXhtml(bodyFragment)}</body>
</html>`;
}

function navDoc(chapters, hasCover) {
  const cover = hasCover ? '<li><a href="cover.xhtml">표지</a></li>' : '';
  const items = chapters.map(ch => `<li><a href="${ch.href}">${escapeXml(ch.title || '본문')}</a></li>`).join('');
  return xhtmlDoc('목차', `<nav epub:type="toc"><h1>목차</h1><ol>${cover}${items}</ol></nav>`);
}

function opfDoc(book, chapters) {
  const m = book.meta;
  const uuid = m.uuid || crypto.randomUUID();
  const modified = (m.modified || new Date().toISOString()).replace(/\.\d+Z$/, 'Z');
  const items = [
    '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
    '<item id="css" href="style.css" media-type="text/css"/>',
    ...chapters.map(ch => `<item id="${ch.id}" href="${ch.href}" media-type="application/xhtml+xml"/>`),
    ...(book.images || []).map((img, i) => `<item id="img${i + 1}" href="${img.href}" media-type="${img.mediaType}"/>`),
    ...(book.fonts || []).map((f, i) => `<item id="font${i + 1}" href="fonts/${f.file}" media-type="font/ttf"/>`),
  ];
  if (book.fonts && book.fonts.length) items.push('<item id="font-license" href="fonts/LICENSE.txt" media-type="text/plain"/>');
  if (book.cover) {
    items.push(`<item id="cover-image" href="${book.cover.href}" media-type="${book.cover.mediaType}" properties="cover-image"/>`);
    items.push('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>');
  }
  const spine = [
    ...(book.cover ? ['<itemref idref="cover"/>'] : []),
    ...chapters.map(ch => `<itemref idref="${ch.id}"/>`),
  ];
  const opt = [];
  if (m.isbn) opt.push(`<dc:identifier>urn:isbn:${escapeXml(m.isbn)}</dc:identifier>`);
  if (m.publisher) opt.push(`<dc:publisher>${escapeXml(m.publisher)}</dc:publisher>`);
  if (m.pubDate) opt.push(`<dc:date>${escapeXml(m.pubDate)}</dc:date>`);
  if (m.description) opt.push(`<dc:description>${escapeXml(m.description)}</dc:description>`);
  return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="${escapeXml(m.language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:${escapeXml(uuid)}</dc:identifier>
    <dc:title>${escapeXml(m.title)}</dc:title>
    <dc:creator>${escapeXml(m.author)}</dc:creator>
    <dc:language>${escapeXml(m.language)}</dc:language>
    <meta property="dcterms:modified">${escapeXml(modified)}</meta>
    ${opt.join('\n    ')}
  </metadata>
  <manifest>
    ${items.join('\n    ')}
  </manifest>
  <spine>
    ${spine.join('\n    ')}
  </spine>
</package>`;
}

export function buildEpubFiles(book) {
  const files = new Map();
  files.set('mimetype', 'application/epub+zip');
  files.set('META-INF/container.xml', `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>`);
  const chapters = book.chapters.map((ch, i) => ({ ...ch, id: `ch${i + 1}`, href: `chapter${i + 1}.xhtml` }));
  chapters.forEach(ch => files.set(`OEBPS/${ch.href}`, xhtmlDoc(ch.title || book.meta.title, ch.html)));
  files.set('OEBPS/style.css', book.css);
  (book.images || []).forEach(img => files.set(`OEBPS/${img.href}`, img.data));
  (book.fonts || []).forEach(f => files.set(`OEBPS/fonts/${f.file}`, f.data));
  if (book.fonts && book.fonts.length) {
    files.set('OEBPS/fonts/LICENSE.txt', book.licenseNote || 'KoPubWorld 서체: (사)한국출판인회의 배포, 전자책 내장 허용 라이선스.');
  }
  if (book.cover) {
    files.set(`OEBPS/${book.cover.href}`, book.cover.data);
    files.set('OEBPS/cover.xhtml', xhtmlDoc(book.meta.title, `<figure class="cover"><img src="${book.cover.href}" alt="표지"/></figure>`));
  }
  files.set('OEBPS/nav.xhtml', navDoc(chapters, !!book.cover));
  files.set('OEBPS/content.opf', opfDoc(book, chapters));
  return files;
}

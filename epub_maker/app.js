import { THEMES, themeDefaults, buildThemeCss } from './themes.js';
import { splitChapters, extractImages, summarizeMessages } from './docx-parser.js';
import { buildEpubFiles } from './epub-builder.js';
import { validateEpub } from './epub-validator.js';
import { checkCoverSpec, drawCover } from './cover.js';
import { planImageOutput, base64ToBytes, compressImage } from './images.js';
import { createSettingsStore } from './storage.js';

const $ = id => document.getElementById(id);
const store = createSettingsStore(window.localStorage);

const FONT_FILES = [
  { file: 'KoPubBatang-Light.ttf', family: 'KoPub Batang', weight: 400 },
  { file: 'KoPubBatang-Bold.ttf', family: 'KoPub Batang', weight: 700 },
  { file: 'KoPubDotum-Light.ttf', family: 'KoPub Dotum', weight: 400 },
  { file: 'KoPubDotum-Bold.ttf', family: 'KoPub Dotum', weight: 700 },
];

const state = {
  meta: { title: '', author: '', language: 'ko', isbn: '', publisher: '', pubDate: '', description: '' },
  themeId: 'novel',
  options: themeDefaults('novel'),
  coverMode: 'auto',
  keepOriginalImages: false,
  chapters: [],
  images: [],
  messages: [],
  uploadedCover: null,
  currentChapter: 0,
  availableFonts: [],
};

// ---------- 초기화 ----------

async function init() {
  const saved = store.load();
  if (saved) {
    Object.assign(state.meta, saved.meta || {});
    state.themeId = saved.themeId || 'novel';
    state.options = { ...themeDefaults(state.themeId), ...(saved.options || {}) };
    state.coverMode = saved.coverMode || 'auto';
    state.keepOriginalImages = !!saved.keepOriginalImages;
  }
  state.availableFonts = await detectFonts();
  renderThemeList();
  bindMetaForm();
  bindOptions();
  bindUpload();
  bindCover();
  bindDownload();
  syncOptionInputs();
  renderCover();
  renderPreview();
  updateDownloadEnabled();
}

async function detectFonts() {
  const out = [];
  for (const f of FONT_FILES) {
    try {
      const res = await fetch(`fonts/${f.file}`, { method: 'HEAD' });
      if (res.ok) out.push(f);
    } catch { /* 폰트 없음: 기기 기본 글꼴로 동작 */ }
  }
  return out;
}

function persist() {
  store.save({
    meta: state.meta,
    themeId: state.themeId,
    options: state.options,
    coverMode: state.coverMode,
    keepOriginalImages: state.keepOriginalImages,
  });
}

// ---------- 문서 업로드 ----------

function bindUpload() {
  const zone = $('drop-zone');
  const input = $('file-input');
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') input.click(); });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files[0]) handleFile(input.files[0]); });
}

async function handleFile(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.doc') && !name.endsWith('.docx')) {
    showMessages(['구형 .doc 형식은 지원하지 않습니다. 워드에서 "다른 이름으로 저장 → Word 문서(.docx)"로 저장한 뒤 다시 올려주세요.']);
    return;
  }
  if (!name.endsWith('.docx')) {
    showMessages(['.docx 파일만 올릴 수 있습니다.']);
    return;
  }
  showMessages(['변환 중...']);
  try {
    const arrayBuffer = await file.arrayBuffer();
    const result = await window.mammoth.convertToHtml({ arrayBuffer });
    const extracted = extractImages(result.value);
    let html = extracted.html;
    const images = [];
    for (const img of extracted.images) {
      const bytes = base64ToBytes(img.base64);
      const size = await imageSize(img.base64, img.mediaType);
      const plan = planImageOutput({ width: size.width, byteLength: bytes.length, keepOriginal: state.keepOriginalImages });
      const out = await compressImage(img.base64, img.mediaType, plan);
      let href = img.href;
      if (out.mediaType !== img.mediaType) {
        const newHref = href.replace(/\.\w+$/, '.jpeg');
        html = html.split(href).join(newHref);
        href = newHref;
      }
      images.push({ href, mediaType: out.mediaType, data: out.data, base64ForPreview: img.base64, originalType: img.mediaType });
    }
    state.images = images;
    state.chapters = splitChapters(html);
    state.messages = summarizeMessages(result.messages);
    if (state.chapters.length === 1 && state.chapters[0].title === null) {
      state.messages.push('제목 스타일을 찾지 못해 책 전체가 한 챕터가 되었습니다. 워드에서 챕터 제목에 "제목 1" 스타일을 적용하면 자동으로 나뉩니다.');
    }
    state.currentChapter = 0;
    setStep(2);
    showMessages(state.messages);
    renderChapterList();
    renderPreview();
    updateDownloadEnabled();
  } catch (err) {
    showMessages([`문서를 읽지 못했습니다: ${err.message}`]);
  }
}

function imageSize(base64, mediaType) {
  return new Promise(resolve => {
    const el = new Image();
    el.onload = () => resolve({ width: el.naturalWidth, height: el.naturalHeight });
    el.onerror = () => resolve({ width: 0, height: 0 });
    el.src = `data:${mediaType};base64,${base64}`;
  });
}

// ---------- 책 정보 ----------

const META_FIELDS = [
  ['meta-title', 'title'], ['meta-author', 'author'], ['meta-isbn', 'isbn'],
  ['meta-publisher', 'publisher'], ['meta-pubdate', 'pubDate'], ['meta-description', 'description'],
];

function bindMetaForm() {
  for (const [id, key] of META_FIELDS) {
    const el = $(id);
    el.value = state.meta[key] || '';
    el.addEventListener('input', () => {
      state.meta[key] = el.value.trim();
      persist();
      updateDownloadEnabled();
      if (state.coverMode === 'auto' && (key === 'title' || key === 'author')) renderCover();
    });
  }
}

// ---------- 테마·옵션 ----------

function renderThemeList() {
  const box = $('theme-list');
  box.innerHTML = '';
  for (const [id, theme] of Object.entries(THEMES)) {
    const label = document.createElement('label');
    label.className = id === state.themeId ? 'selected' : '';
    label.innerHTML = `<input type="radio" name="theme" value="${id}" ${id === state.themeId ? 'checked' : ''}> ${theme.name}`;
    label.querySelector('input').addEventListener('change', () => {
      state.themeId = id;
      state.options = themeDefaults(id);
      persist();
      renderThemeList();
      syncOptionInputs();
      renderCover();
      renderPreview();
    });
    box.appendChild(label);
  }
}

const OPTION_INPUTS = [
  ['opt-font', 'fontFamily', 'select'], ['opt-fontsize', 'fontSize', 'number'],
  ['opt-lineheight', 'lineHeight', 'number'], ['opt-paraspacing', 'paragraphSpacing', 'number'],
  ['opt-indent', 'textIndent', 'number'], ['opt-margin', 'sideMargin', 'number'],
  ['opt-headingalign', 'headingAlign', 'select'], ['opt-divider', 'headingDivider', 'checkbox'],
  ['opt-pagebreak', 'pageBreak', 'checkbox'],
];

function bindOptions() {
  for (const [id, key, kind] of OPTION_INPUTS) {
    $(id).addEventListener('input', () => {
      const el = $(id);
      state.options[key] = kind === 'checkbox' ? el.checked : kind === 'number' ? Number(el.value) : el.value;
      persist();
      syncOutputs();
      renderPreview();
    });
  }
  $('opt-keeporiginal').addEventListener('change', () => {
    state.keepOriginalImages = $('opt-keeporiginal').checked;
    persist();
    if (state.chapters.length) showMessages([...state.messages, '이미지 압축 설정이 바뀌었습니다. 문서를 다시 올리면 적용됩니다.']);
  });
}

function syncOptionInputs() {
  for (const [id, key, kind] of OPTION_INPUTS) {
    const el = $(id);
    if (kind === 'checkbox') el.checked = !!state.options[key];
    else el.value = state.options[key];
  }
  $('opt-keeporiginal').checked = state.keepOriginalImages;
  if (state.availableFonts.length === 0) {
    for (const opt of $('opt-font').options) {
      if (opt.value !== 'device') { opt.disabled = true; opt.text += ' (fonts 폴더에 파일 없음)'; }
    }
    state.options.fontFamily = 'device';
    $('opt-font').value = 'device';
  }
  syncOutputs();
}

function syncOutputs() {
  for (const out of document.querySelectorAll('output')) {
    out.textContent = $(out.getAttribute('for')).value;
  }
}

// ---------- 표지 ----------

function bindCover() {
  $('cover-mode').value = state.coverMode;
  $('cover-mode').addEventListener('change', () => {
    state.coverMode = $('cover-mode').value;
    persist();
    if (state.coverMode === 'upload') $('cover-file').click();
    renderCover();
  });
  $('cover-file').addEventListener('change', async () => {
    const file = $('cover-file').files[0];
    if (!file) return;
    const bitmap = await createImageBitmap(file);
    const check = checkCoverSpec({ width: bitmap.width, height: bitmap.height });
    renderList($('cover-warnings'), check.warnings);
    state.uploadedCover = { data: new Uint8Array(await file.arrayBuffer()), mediaType: file.type, bitmap };
    renderCover();
  });
}

function renderCover() {
  const canvas = $('cover-preview');
  const ctx = canvas.getContext('2d');
  canvas.width = 160; canvas.height = 240;
  ctx.clearRect(0, 0, 160, 240);
  if (state.coverMode === 'none') return;
  if (state.coverMode === 'upload' && state.uploadedCover) {
    ctx.drawImage(state.uploadedCover.bitmap, 0, 0, 160, 240);
  } else if (state.coverMode === 'auto') {
    const big = document.createElement('canvas');
    drawCover(big, { title: state.meta.title, author: state.meta.author, themeId: state.themeId });
    ctx.drawImage(big, 0, 0, 160, 240);
  }
}

async function buildCoverForEpub() {
  if (state.coverMode === 'none') return null;
  if (state.coverMode === 'upload' && state.uploadedCover) {
    const ext = state.uploadedCover.mediaType === 'image/png' ? 'png' : 'jpg';
    return { href: `images/cover.${ext}`, mediaType: state.uploadedCover.mediaType, data: state.uploadedCover.data };
  }
  const canvas = document.createElement('canvas');
  drawCover(canvas, { title: state.meta.title, author: state.meta.author, themeId: state.themeId });
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  return { href: 'images/cover.jpg', mediaType: 'image/jpeg', data: new Uint8Array(await blob.arrayBuffer()) };
}

// ---------- 미리보기 ----------

function embeddedFontsForCss() {
  const want = state.options.fontFamily === 'kopub-batang' ? 'KoPub Batang' : state.options.fontFamily === 'kopub-dotum' ? 'KoPub Dotum' : null;
  return want ? state.availableFonts.filter(f => f.family === want) : [];
}

function renderChapterList() {
  const list = $('chapter-list');
  list.innerHTML = '';
  state.chapters.forEach((ch, i) => {
    const li = document.createElement('li');
    li.textContent = ch.title || '(제목 없는 본문)';
    li.className = i === state.currentChapter ? 'current' : '';
    li.addEventListener('click', () => { state.currentChapter = i; renderChapterList(); renderPreview(); });
    list.appendChild(li);
  });
}

function renderPreview() {
  const css = buildThemeCss(state.options, embeddedFontsForCss());
  const ch = state.chapters[state.currentChapter];
  let html = ch ? ch.html : '<p style="color:#888">문서를 올리면 미리보기가 여기 표시됩니다.</p>';
  for (const img of state.images) {
    html = html.split(`src="${img.href}"`).join(`src="data:${img.originalType};base64,${img.base64ForPreview}"`);
  }
  $('preview-frame').srcdoc = `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>${css}</style></head><body>${html}</body></html>`;
}

// ---------- 생성·다운로드 ----------

function updateDownloadEnabled() {
  const ready = state.chapters.length > 0 && state.meta.title && state.meta.author;
  $('btn-download').disabled = !ready;
  $('btn-download').title = ready ? '' : '문서를 올리고 제목·저자를 입력하면 활성화됩니다.';
}

function bindDownload() {
  $('btn-download').addEventListener('click', async () => {
    const fonts = [];
    for (const f of embeddedFontsForCss()) {
      const res = await fetch(`fonts/${f.file}`);
      fonts.push({ ...f, data: new Uint8Array(await res.arrayBuffer()) });
    }
    const book = {
      meta: state.meta,
      chapters: state.chapters,
      images: state.images.map(({ href, mediaType, data }) => ({ href, mediaType, data })),
      cover: await buildCoverForEpub(),
      css: buildThemeCss(state.options, fonts),
      fonts,
    };
    const files = buildEpubFiles(book);
    const check = validateEpub(files);
    const box = $('validation');
    box.innerHTML = '';
    if (!check.ok) {
      for (const e of check.errors) {
        const li = document.createElement('li');
        li.className = 'error';
        li.textContent = e;
        box.appendChild(li);
      }
      return;
    }
    const zip = new window.JSZip();
    zip.file('mimetype', files.get('mimetype'), { compression: 'STORE' });
    for (const [path, content] of files) {
      if (path !== 'mimetype') zip.file(path, content);
    }
    const blob = await zip.generateAsync({ type: 'blob', mimeType: 'application/epub+zip', compression: 'DEFLATE' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${state.meta.title || 'book'}.epub`;
    a.click();
    URL.revokeObjectURL(a.href);
    const li = document.createElement('li');
    li.className = 'ok';
    li.textContent = '표준 검사를 통과했습니다. EPUB이 다운로드되었습니다.';
    box.appendChild(li);
    setStep(3);
  });
}

// ---------- 공용 UI ----------

function setStep(n) {
  document.querySelectorAll('#step-indicator li').forEach((li, i) => {
    li.classList.toggle('active', i === n - 1);
  });
}

function showMessages(list) {
  renderList($('messages'), list);
}

function renderList(el, items) {
  el.innerHTML = '';
  for (const text of items) {
    const li = document.createElement('li');
    li.textContent = text;
    el.appendChild(li);
  }
}

init();

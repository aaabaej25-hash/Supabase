import { STYLE_GUIDES, PLATFORM_GUIDES } from './prompts.js';
import { buildPrompt } from './prompt-builder.js';
import { loadHistory, saveEntry, deleteEntry } from './history.js';

const $ = (id) => document.getElementById(id);

const els = {
  original: $('original-input'),
  charCount: $('char-count'),
  styleOptions: $('style-options'),
  situation: $('situation-input'),
  platformOptions: $('platform-options'),
  generateBtn: $('generate-btn'),
  promptWrap: $('prompt-output-wrap'),
  promptOutput: $('prompt-output'),
  copyBtn: $('copy-btn'),
  copyStatus: $('copy-status'),
  resultInput: $('result-input'),
  compareGrid: $('compare-grid'),
  compareOriginal: $('compare-original'),
  compareResult: $('compare-result'),
  saveBtn: $('save-btn'),
  saveStatus: $('save-status'),
  historyList: $('history-list'),
  historyEmpty: $('history-empty'),
};

// ── 체크박스 렌더링 ──────────────────────────────────────────

function renderCheckboxes(container, guides, name, checkedByDefault) {
  for (const [id, guide] of Object.entries(guides)) {
    const label = document.createElement('label');
    label.className = 'check-item';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = name;
    input.value = id;
    input.checked = checkedByDefault;
    label.append(input, document.createTextNode(guide.label));
    container.appendChild(label);
  }
}

renderCheckboxes(els.styleOptions, STYLE_GUIDES, 'style', true);
renderCheckboxes(els.platformOptions, PLATFORM_GUIDES, 'platform', false);

function checkedValues(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
}

function readOptions() {
  return {
    styles: checkedValues('style'),
    situation: els.situation.value,
    platforms: checkedValues('platform'),
  };
}

// ── 초안 입력 ────────────────────────────────────────────────

function refreshInputState() {
  const text = els.original.value;
  els.charCount.textContent = String(text.length);
  els.generateBtn.disabled = text.trim() === '';
  refreshCompare();
}

els.original.addEventListener('input', refreshInputState);

// ── 프롬프트 생성 + 복사 ─────────────────────────────────────

els.generateBtn.addEventListener('click', () => {
  const prompt = buildPrompt({ original: els.original.value, ...readOptions() });
  els.promptOutput.value = prompt;
  els.promptWrap.hidden = false;
  els.copyStatus.textContent = '';
});

els.copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(els.promptOutput.value);
    els.copyStatus.textContent = '복사되었습니다!';
  } catch {
    els.promptOutput.select();
    els.copyStatus.textContent = '자동 복사가 안 되어 전체 선택했어요. Ctrl+C를 눌러주세요.';
  }
  setTimeout(() => { els.copyStatus.textContent = ''; }, 4000);
});

// ── 결과 비교 ────────────────────────────────────────────────

function refreshCompare() {
  const original = els.original.value.trim();
  const result = els.resultInput.value.trim();
  const showCompare = original !== '' && result !== '';
  els.compareGrid.hidden = !showCompare;
  if (showCompare) {
    els.compareOriginal.textContent = els.original.value;
    els.compareResult.textContent = els.resultInput.value;
  }
  els.saveBtn.disabled = !showCompare;
}

els.resultInput.addEventListener('input', refreshCompare);

// ── 히스토리 ─────────────────────────────────────────────────

function formatDate(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

function renderHistory() {
  const entries = loadHistory(localStorage);
  els.historyList.replaceChildren();
  els.historyEmpty.hidden = entries.length > 0;

  for (const entry of entries) {
    const li = document.createElement('li');
    li.className = 'history-item';

    const loadBtn = document.createElement('button');
    loadBtn.className = 'history-load';
    loadBtn.textContent = entry.title;
    const date = document.createElement('span');
    date.className = 'history-date';
    date.textContent = formatDate(entry.date);
    loadBtn.appendChild(date);
    loadBtn.addEventListener('click', () => restoreEntry(entry));

    const delBtn = document.createElement('button');
    delBtn.className = 'history-delete';
    delBtn.textContent = '삭제';
    delBtn.addEventListener('click', () => {
      deleteEntry(localStorage, entry.id);
      renderHistory();
    });

    li.append(loadBtn, delBtn);
    els.historyList.appendChild(li);
  }
}

function restoreEntry(entry) {
  els.original.value = entry.original;
  els.resultInput.value = entry.result;
  els.situation.value = entry.options.situation ?? '';
  for (const input of document.querySelectorAll('input[name="style"]')) {
    input.checked = (entry.options.styles ?? []).includes(input.value);
  }
  for (const input of document.querySelectorAll('input[name="platform"]')) {
    input.checked = (entry.options.platforms ?? []).includes(input.value);
  }
  els.promptWrap.hidden = true;
  refreshInputState();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

els.saveBtn.addEventListener('click', () => {
  try {
    saveEntry(localStorage, {
      original: els.original.value,
      result: els.resultInput.value,
      options: readOptions(),
    });
    els.saveStatus.textContent = '저장되었습니다!';
    renderHistory();
  } catch {
    els.saveStatus.textContent = '저장 공간이 부족합니다. 오래된 기록을 삭제해 주세요.';
  }
  setTimeout(() => { els.saveStatus.textContent = ''; }, 4000);
});

// ── 초기화 ───────────────────────────────────────────────────

refreshInputState();
renderHistory();

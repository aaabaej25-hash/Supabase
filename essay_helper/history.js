export const HISTORY_KEY = 'essay_helper_history';

const MAX_TITLE_LENGTH = 30;

export function makeTitle(original) {
  const firstLine = original.trim().split('\n')[0].trim();
  return firstLine.slice(0, MAX_TITLE_LENGTH) || '(제목 없음)';
}

export function loadHistory(storage) {
  try {
    const raw = storage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveEntry(storage, { original, result, options }) {
  const entries = loadHistory(storage);
  const entry = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    date: new Date().toISOString(),
    title: makeTitle(original),
    original,
    result,
    options,
  };
  entries.unshift(entry);
  storage.setItem(HISTORY_KEY, JSON.stringify(entries));
  return entry;
}

export function deleteEntry(storage, id) {
  const entries = loadHistory(storage).filter((e) => e.id !== id);
  storage.setItem(HISTORY_KEY, JSON.stringify(entries));
  return entries;
}

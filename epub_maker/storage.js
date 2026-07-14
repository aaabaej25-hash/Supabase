const KEY = 'epub_maker_state_v1';

export function createSettingsStore(backing) {
  return {
    save(state) {
      try { backing.setItem(KEY, JSON.stringify(state)); } catch { /* 저장 실패는 치명적이지 않음 */ }
    },
    load() {
      try {
        const raw = backing.getItem(KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    },
  };
}

import { renderProfileWidgetCode, renderMenuWidgetCode } from './widget-templates.js';
import { ICON_KEYS } from './icons.js';
import { createCropController, TARGETS } from './cropper.js';

const MAX_MENUS = 5;

function createDefaultState() {
  return {
    blogName: '',
    slogan: '',
    hours: '',
    profileImageUrl: '',
    bgColor: '#ffffff',
    quickLinks: { home: '', blogMap: '', reserve: '', phone: '' },
    menus: [],
  };
}

const state = createDefaultState();

const el = (id) => document.getElementById(id);

function renderAll() {
  const profileCode = renderProfileWidgetCode(state);
  const menuCode = renderMenuWidgetCode(state);
  el('profileWidgetCode').textContent = profileCode;
  el('menuWidgetCode').textContent = menuCode;
  el('profilePreviewFrame').srcdoc = `<style>body{margin:0;font-family:sans-serif;}</style>${profileCode}`;
  el('menuPreviewFrame').srcdoc = `<style>body{margin:0;font-family:sans-serif;}</style>${menuCode}`;
}

function bindTextField(id, stateKey) {
  el(id).addEventListener('input', (e) => {
    state[stateKey] = e.target.value;
    renderAll();
  });
}

function bindQuickLink(id, key) {
  el(id).addEventListener('input', (e) => {
    state.quickLinks[key] = e.target.value;
    renderAll();
  });
}

bindTextField('blogName', 'blogName');
bindTextField('slogan', 'slogan');
bindTextField('hours', 'hours');
bindTextField('profileImageUrl', 'profileImageUrl');
bindQuickLink('qlHome', 'home');
bindQuickLink('qlBlogMap', 'blogMap');
bindQuickLink('qlReserve', 'reserve');
bindQuickLink('qlPhone', 'phone');

document.querySelectorAll('.bwm-color-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.bgColor = btn.dataset.color;
    el('customBgColor').value = btn.dataset.color;
    renderAll();
  });
});
el('customBgColor').addEventListener('input', (e) => {
  state.bgColor = e.target.value;
  renderAll();
});

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
  } finally {
    document.body.removeChild(ta);
  }
  done();
}

function copyToClipboard(text, button) {
  const done = () => {
    const original = button.textContent;
    button.textContent = '복사됨!';
    setTimeout(() => {
      button.textContent = original;
    }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

el('copyProfileBtn').addEventListener('click', () => {
  copyToClipboard(el('profileWidgetCode').textContent, el('copyProfileBtn'));
});
el('copyMenuBtn').addEventListener('click', () => {
  copyToClipboard(el('menuWidgetCode').textContent, el('copyMenuBtn'));
});

function menuItemTemplate(index) {
  const wrap = document.createElement('div');
  wrap.className = 'bwm-menu-item-row';
  wrap.innerHTML = `
    <select class="bwm-menu-icon">
      ${ICON_KEYS.map((k) => `<option value="${k}">${k}</option>`).join('')}
    </select>
    <input type="text" class="bwm-menu-text" placeholder="예. 소개" />
    <input type="url" class="bwm-menu-url" placeholder="https://..." />
    <button type="button" class="bwm-menu-remove">삭제</button>
  `;
  const iconSel = wrap.querySelector('.bwm-menu-icon');
  const textInput = wrap.querySelector('.bwm-menu-text');
  const urlInput = wrap.querySelector('.bwm-menu-url');
  const removeBtn = wrap.querySelector('.bwm-menu-remove');

  const sync = () => {
    state.menus[index] = {
      icon: iconSel.value,
      text: textInput.value,
      url: urlInput.value,
    };
    renderAll();
  };
  iconSel.addEventListener('change', sync);
  textInput.addEventListener('input', sync);
  urlInput.addEventListener('input', sync);
  removeBtn.addEventListener('click', () => {
    state.menus.splice(index, 1);
    renderMenuList();
    renderAll();
  });
  return wrap;
}

function renderMenuList() {
  const container = el('menuList');
  container.innerHTML = '';
  state.menus.forEach((menu, index) => {
    const row = menuItemTemplate(index);
    row.querySelector('.bwm-menu-icon').value = menu.icon;
    row.querySelector('.bwm-menu-text').value = menu.text;
    row.querySelector('.bwm-menu-url').value = menu.url;
    container.appendChild(row);
  });
  el('addMenuBtn').disabled = state.menus.length >= MAX_MENUS;
  el('menuLimitWarning').hidden = state.menus.length < MAX_MENUS;
}

el('addMenuBtn').addEventListener('click', () => {
  if (state.menus.length >= MAX_MENUS) return;
  state.menus.push({ icon: ICON_KEYS[0], text: '', url: '' });
  renderMenuList();
  renderAll();
});

renderMenuList();
renderAll();

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

let pcController = null;
let mobileController = null;

el('bgImageInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const warning = el('bgImageWarning');
  warning.hidden = true;
  if (!file) return;
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    warning.textContent = 'JPG, PNG, WEBP 파일만 업로드할 수 있습니다.';
    warning.hidden = false;
    e.target.value = '';
    return;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    warning.textContent = '파일 크기는 10MB를 넘을 수 없습니다.';
    warning.hidden = false;
    e.target.value = '';
    return;
  }
  const img = new Image();
  img.onload = () => {
    pcController = createCropController({ canvas: el('cropCanvasPC'), image: img, target: TARGETS.pc });
    mobileController = createCropController({ canvas: el('cropCanvasMobile'), image: img, target: TARGETS.mobile });
    el('downloadPCBtn').disabled = false;
    el('downloadMobileBtn').disabled = false;
  };
  img.src = URL.createObjectURL(file);
});

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

el('downloadPCBtn').addEventListener('click', () => {
  if (!pcController) return;
  pcController.toBlob((blob) => downloadBlob(blob, 'bg-pc-1920x700.png'));
});
el('downloadMobileBtn').addEventListener('click', () => {
  if (!mobileController) return;
  mobileController.toBlob((blob) => downloadBlob(blob, 'bg-mobile-700x700.png'));
});

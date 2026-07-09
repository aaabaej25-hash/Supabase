import { getIconSvg } from './icons.js';

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function renderProfileWidgetCode(state) {
  const name = state.blogName && state.blogName.trim()
    ? escapeHtml(state.blogName.trim())
    : '블로그명을 입력하세요';
  const slogan = state.slogan && state.slogan.trim() ? escapeHtml(state.slogan.trim()) : '';
  const hours = state.hours && state.hours.trim() ? escapeHtml(state.hours.trim()) : '';
  const imgUrl = state.profileImageUrl && state.profileImageUrl.trim()
    ? escapeHtml(state.profileImageUrl.trim())
    : '';
  const bg = state.bgColor || '#ffffff';
  const menus = Array.isArray(state.menus) ? state.menus.slice(0, 5) : [];

  const linkItems = menus.map((m) => {
    const url = m.url && m.url.trim() ? escapeHtml(m.url.trim()) : '#';
    const label = m.text && m.text.trim() ? escapeHtml(m.text.trim()) : '';
    return `<a href="${url}" target="_blank" rel="noopener" class="bwm-quicklink" title="${label}">${getIconSvg(m.icon)}</a>`;
  }).join('');

  return [
    `<div class="bwm-profile-widget" style="background:${bg}">`,
    imgUrl ? `  <img src="${imgUrl}" alt="${name}" class="bwm-profile-img" />` : '',
    `  <div class="bwm-profile-name">${name}</div>`,
    slogan ? `  <div class="bwm-profile-slogan">${slogan}</div>` : '',
    hours ? `  <div class="bwm-profile-hours">${hours}</div>` : '',
    `  <div class="bwm-quicklinks">${linkItems}</div>`,
    `</div>`,
  ].filter(Boolean).join('\n');
}

export function renderMenuWidgetCode(state) {
  const menus = Array.isArray(state.menus) ? state.menus.slice(0, 5) : [];
  if (menus.length === 0) {
    return `<div class="bwm-menu-widget">\n  <div class="bwm-menu-empty">메뉴를 추가하세요</div>\n</div>`;
  }
  const items = menus.map((m) => {
    const text = m.text && m.text.trim() ? escapeHtml(m.text.trim()) : '메뉴';
    const url = m.url && m.url.trim() ? escapeHtml(m.url.trim()) : '#';
    return `  <a href="${url}" target="_blank" rel="noopener" class="bwm-menu-item">${getIconSvg(m.icon)}<span>${text}</span></a>`;
  }).join('\n');
  return `<div class="bwm-menu-widget">\n${items}\n</div>`;
}

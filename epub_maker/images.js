const MAX_WIDTH = 1600;
const MAX_BYTES = 500 * 1024;

export function planImageOutput({ width, byteLength, keepOriginal = false }) {
  if (keepOriginal) return { resize: false };
  if (width > MAX_WIDTH || byteLength > MAX_BYTES) {
    return { resize: true, targetWidth: Math.min(width, MAX_WIDTH), quality: 0.8 };
  }
  return { resize: false };
}

export function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export async function compressImage(base64, mediaType, plan) {
  if (!plan.resize) return { data: base64ToBytes(base64), mediaType };
  const img = await new Promise((resolve, reject) => {
    const el = new Image();
    el.onload = () => resolve(el);
    el.onerror = reject;
    el.src = `data:${mediaType};base64,${base64}`;
  });
  const scale = plan.targetWidth / img.naturalWidth;
  const canvas = document.createElement('canvas');
  canvas.width = plan.targetWidth;
  canvas.height = Math.round(img.naturalHeight * scale);
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', plan.quality));
  return { data: new Uint8Array(await blob.arrayBuffer()), mediaType: 'image/jpeg' };
}

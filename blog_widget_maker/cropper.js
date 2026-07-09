export function computeInitialCropRect(imgWidth, imgHeight, targetRatio) {
  const imgRatio = imgWidth / imgHeight;
  let width, height;
  if (imgRatio > targetRatio) {
    height = imgHeight;
    width = height * targetRatio;
  } else {
    width = imgWidth;
    height = width / targetRatio;
  }
  return {
    x: (imgWidth - width) / 2,
    y: (imgHeight - height) / 2,
    width,
    height,
  };
}

export function clampCropRect(rect, imgWidth, imgHeight) {
  const width = Math.min(rect.width, imgWidth);
  const height = Math.min(rect.height, imgHeight);
  const x = Math.max(0, Math.min(rect.x, imgWidth - width));
  const y = Math.max(0, Math.min(rect.y, imgHeight - height));
  return { x, y, width, height };
}

export const TARGETS = {
  pc: { width: 1920, height: 700 },
  mobile: { width: 700, height: 700 },
};

export function createCropController({ canvas, image, target }) {
  const { width: targetWidth, height: targetHeight } = target;
  const targetRatio = targetWidth / targetHeight;
  let rect = computeInitialCropRect(image.naturalWidth, image.naturalHeight, targetRatio);
  const ctx = canvas.getContext('2d');
  const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const offsetX = (canvas.width - image.naturalWidth * scale) / 2;
  const offsetY = (canvas.height - image.naturalHeight * scale) / 2;

  function toCanvasRect(r) {
    return {
      x: offsetX + r.x * scale,
      y: offsetY + r.y * scale,
      width: r.width * scale,
      height: r.height * scale,
    };
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, offsetX, offsetY, image.naturalWidth * scale, image.naturalHeight * scale);
    const c = toCanvasRect(rect);
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(offsetX, offsetY, image.naturalWidth * scale, c.y - offsetY);
    ctx.fillRect(
      offsetX,
      c.y + c.height,
      image.naturalWidth * scale,
      offsetY + image.naturalHeight * scale - (c.y + c.height)
    );
    ctx.fillRect(offsetX, c.y, c.x - offsetX, c.height);
    ctx.fillRect(c.x + c.width, c.y, offsetX + image.naturalWidth * scale - (c.x + c.width), c.height);
    ctx.strokeStyle = '#00a3ff';
    ctx.lineWidth = 2;
    ctx.strokeRect(c.x, c.y, c.width, c.height);
    ctx.restore();
  }

  let dragStart = null;
  canvas.addEventListener('pointerdown', (e) => {
    const r = canvas.getBoundingClientRect();
    dragStart = {
      x: e.clientX - r.left,
      y: e.clientY - r.top,
      rectX: rect.x,
      rectY: rect.y,
    };
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragStart) return;
    const r = canvas.getBoundingClientRect();
    const dx = (e.clientX - r.left - dragStart.x) / scale;
    const dy = (e.clientY - r.top - dragStart.y) / scale;
    rect = clampCropRect(
      { ...rect, x: dragStart.rectX + dx, y: dragStart.rectY + dy },
      image.naturalWidth,
      image.naturalHeight
    );
    draw();
  });
  window.addEventListener('pointerup', () => {
    dragStart = null;
  });

  draw();

  return {
    toBlob(callback) {
      const out = document.createElement('canvas');
      out.width = targetWidth;
      out.height = targetHeight;
      const octx = out.getContext('2d');
      octx.drawImage(image, rect.x, rect.y, rect.width, rect.height, 0, 0, targetWidth, targetHeight);
      out.toBlob(callback, 'image/png');
    },
  };
}

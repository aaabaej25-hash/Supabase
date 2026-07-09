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

// Makes web-sized WebP copies of the landing hero photos in public/hero/. The originals are left untouched.
// The page serves these copies as-is (`unoptimized`): resizing multi-megabyte originals per request took
// 8-85 s on a small hosting instance, and that cache is lost on every restart.
// Run after changing a hero photo:  node scripts/optimize-hero-images.mjs
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const PUBLIC = path.join(import.meta.dirname, "..", "public");
// [source in public/, width in px]. Carousel spans up to 1248 CSS px; the hero card is at most 384.
const IMAGES = [
  ["hero.png", 1920],
  ["hero-03-side-show.jpg", 1920],
  ["hero-05.jpg", 1920],
  ["hero-2-cropped.png", 800],
];

await mkdir(path.join(PUBLIC, "hero"), { recursive: true });
for (const [source, width] of IMAGES) {
  const target = path.join("hero", `${path.parse(source).name}.webp`);
  await sharp(path.join(PUBLIC, source))
    .resize({ width, withoutEnlargement: true })
    .webp({ quality: 78 })
    .toFile(path.join(PUBLIC, target));
  const kb = (bytes) => `${Math.round(bytes / 1024)} KB`;
  console.log(`${source} (${kb((await stat(path.join(PUBLIC, source))).size)}) -> ${target} (${kb((await stat(path.join(PUBLIC, target))).size)})`);
}

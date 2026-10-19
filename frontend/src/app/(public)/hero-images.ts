// Landing hero carousel slides, in display order. Paths are web-sized copies in public/hero/,
// made from the originals in public/ by scripts/optimize-hero-images.mjs.
// The first slide is the default shown on load and the only preloaded image.
export type HeroImage = { src: string; alt: string };

export const HERO_IMAGES: HeroImage[] = [
  {
    src: "/hero/hero.webp",
    alt: "Bright open-plan living room with a grey sofa, opening onto a kitchen and balcony",
  },
  {
    src: "/hero/hero-03-side-show.webp",
    alt: "Bright high-rise apartment living and dining room with floor-to-ceiling windows over the city",
  },
  {
    src: "/hero/hero-05.webp",
    alt: "Modern open-plan living room with a green sofa and a marble kitchen island",
  },
];

// Landing hero carousel slides, in display order. Paths are files in public/.
// The first slide is the default shown on load and the only preloaded image.
export type HeroImage = { src: string; alt: string };

export const HERO_IMAGES: HeroImage[] = [
  {
    src: "/hero.png",
    alt: "Bright open-plan living room with a grey sofa, opening onto a kitchen and balcony",
  },
  {
    src: "/hero-03-side-show.jpg",
    alt: "Bright high-rise apartment living and dining room with floor-to-ceiling windows over the city",
  },
  {
    src: "/hero-05.jpg",
    alt: "Modern open-plan living room with a green sofa and a marble kitchen island",
  },
];

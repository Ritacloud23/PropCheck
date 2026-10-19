"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Image from "next/image";
import { useEffect, useState, useSyncExternalStore, type FocusEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

import type { HeroImage } from "./hero-images";

export const HERO_AUTOPLAY_MS = 2000;

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void) {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function usePrefersReducedMotion() {
  return useSyncExternalStore(
    subscribeReducedMotion,
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}

// Background photo carousel for the landing hero. Children (overlay and hero content) sit above the
// photos and never move; only the photos crossfade. Autoplay pauses while the pointer is over the hero,
// while focus is inside it, and entirely when the user prefers reduced motion.
export function HeroCarousel({
  images,
  sizes,
  className,
  children,
}: {
  images: HeroImage[];
  sizes: string;
  className?: string;
  children: ReactNode;
}) {
  const [failed, setFailed] = useState<ReadonlySet<string>>(() => new Set());
  const [current, setCurrent] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  // A slide whose file fails to load is dropped instead of showing a broken image.
  const slides = images.filter((image) => !failed.has(image.src));
  const count = slides.length;
  const active = count ? current % count : 0;
  const autoplay = count > 1 && !reducedMotion && !hovered && !focused;

  // Depends on `active`, so every slide change (automatic or manual) restarts the full interval.
  useEffect(() => {
    if (!autoplay) return;
    const timer = window.setTimeout(() => setCurrent((active + 1) % count), HERO_AUTOPLAY_MS);
    return () => window.clearTimeout(timer);
  }, [autoplay, active, count]);

  function onImageError(src: string) {
    if (process.env.NODE_ENV === "development") console.warn(`Hero image failed to load: ${src}`);
    setFailed((prev) => new Set(prev).add(src));
  }

  function onBlur(event: FocusEvent<HTMLDivElement>) {
    if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
  }

  const show = (index: number) => setCurrent((index + count) % count);

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label="PropCheck property images"
      className={className}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={onBlur}
    >
      <div aria-live={autoplay ? "off" : "polite"}>
        {slides.map((image, i) => (
          <div
            key={image.src}
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} of ${count}`}
            aria-hidden={i !== active}
            className={cn(
              "absolute inset-0 transition-opacity duration-900 ease-in-out motion-reduce:transition-none",
              i === active ? "opacity-100" : "opacity-0",
            )}
          >
            <Image
              src={image.src}
              alt={image.alt}
              fill
              // Already web-sized; server-side resizing of hero photos was far too slow on small hosts.
              unoptimized
              preload={image.src === images[0].src}
              sizes={sizes}
              className="object-cover"
              onError={() => onImageError(image.src)}
            />
          </div>
        ))}
      </div>
      {children}
      {count > 1 && (
        // Sits in the strip between the hero content and the overlapping search panel.
        <div className="absolute bottom-21 right-5 flex items-center gap-2 sm:right-10 lg:bottom-24 lg:right-14">
          <button
            type="button"
            aria-label="Previous hero image"
            onClick={() => show(active - 1)}
            className="flex size-7 items-center justify-center rounded-full bg-forest/70 text-white ring-1 ring-white/40 backdrop-blur-sm transition-colors hover:bg-forest"
          >
            <ChevronLeft className="size-4" aria-hidden />
          </button>
          <div className="flex items-center">
            {slides.map((image, i) => (
              <button
                key={image.src}
                type="button"
                aria-label={`Show hero image ${i + 1}`}
                aria-current={i === active ? "true" : undefined}
                onClick={() => show(i)}
                className="group flex size-6 items-center justify-center"
              >
                <span
                  className={cn(
                    "block h-2 rounded-full ring-1 ring-black/10 transition-all motion-reduce:transition-none",
                    i === active ? "w-5 bg-highlight" : "w-2 bg-white/60 group-hover:bg-white",
                  )}
                />
              </button>
            ))}
          </div>
          <button
            type="button"
            aria-label="Next hero image"
            onClick={() => show(active + 1)}
            className="flex size-7 items-center justify-center rounded-full bg-forest/70 text-white ring-1 ring-white/40 backdrop-blur-sm transition-colors hover:bg-forest"
          >
            <ChevronRight className="size-4" aria-hidden />
          </button>
        </div>
      )}
    </div>
  );
}

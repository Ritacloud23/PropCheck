import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HERO_AUTOPLAY_MS, HeroCarousel } from "@/app/(public)/hero-carousel";
import { HERO_IMAGES } from "@/app/(public)/hero-images";

// next/image needs the Next runtime; a plain img keeps src, alt and onError.
vi.mock("next/image", async () => {
  const React = await import("react");
  return {
    default: ({ src, alt, onError }: { src: string; alt: string; onError?: () => void }) =>
      React.createElement("img", { src, alt, onError }),
  };
});

let reducedMotion = false;

beforeEach(() => {
  reducedMotion = false;
  vi.useFakeTimers();
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: reducedMotion && query.includes("reduce"),
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function renderCarousel(images = HERO_IMAGES) {
  return render(
    <HeroCarousel images={images} sizes="100vw">
      <h1>Find a home</h1>
      <button type="button">Browse properties</button>
    </HeroCarousel>,
  );
}

// The visible slide is the one not hidden from assistive tech.
function activeSrc() {
  const slide = screen.getAllByRole("group", { hidden: true }).find((el) => el.getAttribute("aria-hidden") === "false");
  return slide?.querySelector("img")?.getAttribute("src");
}

function activeDot() {
  return screen.getAllByRole("button", { name: /Show hero image/ }).find((b) => b.getAttribute("aria-current") === "true");
}

describe("HeroCarousel", () => {
  it("keeps the original hero first and the new images in order", () => {
    expect(HERO_IMAGES.map((i) => i.src)).toEqual(["/hero/hero.webp", "/hero/hero-03-side-show.webp", "/hero/hero-05.webp"]);
  });

  it("starts on the original hero image with carousel semantics", () => {
    renderCarousel();
    const region = screen.getByRole("region", { name: "PropCheck property images" });
    expect(region).toHaveAttribute("aria-roledescription", "carousel");
    expect(activeSrc()).toBe("/hero/hero.webp");
    expect(activeDot()).toHaveAccessibleName("Show hero image 1");
    expect(screen.getByRole("heading", { name: "Find a home" })).toBeInTheDocument();
  });

  it("advances every 2 seconds and loops", () => {
    renderCarousel();
    const seen = [activeSrc()];
    for (let i = 0; i < 3; i++) {
      act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS));
      seen.push(activeSrc());
    }
    expect(seen).toEqual(["/hero/hero.webp", "/hero/hero-03-side-show.webp", "/hero/hero-05.webp", "/hero/hero.webp"]);
  });

  it("does not advance before 2 seconds", () => {
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 1));
    expect(activeSrc()).toBe("/hero/hero.webp");
  });

  it("previous, next and dots navigate and wrap", () => {
    renderCarousel();
    fireEvent.click(screen.getByRole("button", { name: "Previous hero image" }));
    expect(activeSrc()).toBe("/hero/hero-05.webp");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero/hero.webp");
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 2" }));
    expect(activeSrc()).toBe("/hero/hero-03-side-show.webp");
    expect(activeDot()).toHaveAccessibleName("Show hero image 2");
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 3" }));
    expect(activeSrc()).toBe("/hero/hero-05.webp");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero/hero.webp");
  });

  it("manual navigation restarts the autoplay timer", () => {
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 500));
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 2" }));
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 500));
    expect(activeSrc()).toBe("/hero/hero-03-side-show.webp");
    act(() => vi.advanceTimersByTime(500));
    expect(activeSrc()).toBe("/hero/hero-05.webp");
  });

  it("pauses while hovered and resumes on leave", () => {
    renderCarousel();
    const region = screen.getByRole("region");
    fireEvent.mouseEnter(region);
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero/hero.webp");
    fireEvent.mouseLeave(region);
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS));
    expect(activeSrc()).toBe("/hero/hero-03-side-show.webp");
  });

  it("pauses while a control has keyboard focus and resumes on blur", () => {
    renderCarousel();
    const next = screen.getByRole("button", { name: "Next hero image" });
    act(() => next.focus());
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero/hero.webp");
    act(() => next.blur());
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS));
    expect(activeSrc()).toBe("/hero/hero-03-side-show.webp");
  });

  it("does not autoplay with reduced motion but manual controls still work", () => {
    reducedMotion = true;
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero/hero.webp");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero/hero-03-side-show.webp");
  });

  it("drops an image that fails to load instead of showing it broken", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    renderCarousel();
    fireEvent.error(screen.getByAltText(HERO_IMAGES[1].alt));
    expect(screen.queryByAltText(HERO_IMAGES[1].alt)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Show hero image/ })).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero/hero-05.webp");
    warn.mockRestore();
  });

  it("hides controls when only one image is available", () => {
    renderCarousel(HERO_IMAGES.slice(0, 1));
    expect(activeSrc()).toBe("/hero/hero.webp");
    expect(screen.queryByRole("button", { name: "Next hero image" })).not.toBeInTheDocument();
  });
});

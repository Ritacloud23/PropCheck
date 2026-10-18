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
    expect(HERO_IMAGES.map((i) => i.src)).toEqual(["/hero.png", "/hero-03-side-show.jpg", "/hero-05.jpg"]);
  });

  it("starts on the original hero image with carousel semantics", () => {
    renderCarousel();
    const region = screen.getByRole("region", { name: "PropCheck property images" });
    expect(region).toHaveAttribute("aria-roledescription", "carousel");
    expect(activeSrc()).toBe("/hero.png");
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
    expect(seen).toEqual(["/hero.png", "/hero-03-side-show.jpg", "/hero-05.jpg", "/hero.png"]);
  });

  it("does not advance before 2 seconds", () => {
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 1));
    expect(activeSrc()).toBe("/hero.png");
  });

  it("previous, next and dots navigate and wrap", () => {
    renderCarousel();
    fireEvent.click(screen.getByRole("button", { name: "Previous hero image" }));
    expect(activeSrc()).toBe("/hero-05.jpg");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero.png");
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 2" }));
    expect(activeSrc()).toBe("/hero-03-side-show.jpg");
    expect(activeDot()).toHaveAccessibleName("Show hero image 2");
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 3" }));
    expect(activeSrc()).toBe("/hero-05.jpg");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero.png");
  });

  it("manual navigation restarts the autoplay timer", () => {
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 500));
    fireEvent.click(screen.getByRole("button", { name: "Show hero image 2" }));
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS - 500));
    expect(activeSrc()).toBe("/hero-03-side-show.jpg");
    act(() => vi.advanceTimersByTime(500));
    expect(activeSrc()).toBe("/hero-05.jpg");
  });

  it("pauses while hovered and resumes on leave", () => {
    renderCarousel();
    const region = screen.getByRole("region");
    fireEvent.mouseEnter(region);
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero.png");
    fireEvent.mouseLeave(region);
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS));
    expect(activeSrc()).toBe("/hero-03-side-show.jpg");
  });

  it("pauses while a control has keyboard focus and resumes on blur", () => {
    renderCarousel();
    const next = screen.getByRole("button", { name: "Next hero image" });
    act(() => next.focus());
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero.png");
    act(() => next.blur());
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS));
    expect(activeSrc()).toBe("/hero-03-side-show.jpg");
  });

  it("does not autoplay with reduced motion but manual controls still work", () => {
    reducedMotion = true;
    renderCarousel();
    act(() => vi.advanceTimersByTime(HERO_AUTOPLAY_MS * 3));
    expect(activeSrc()).toBe("/hero.png");
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero-03-side-show.jpg");
  });

  it("drops an image that fails to load instead of showing it broken", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    renderCarousel();
    fireEvent.error(screen.getByAltText(HERO_IMAGES[1].alt));
    expect(screen.queryByAltText(HERO_IMAGES[1].alt)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Show hero image/ })).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Next hero image" }));
    expect(activeSrc()).toBe("/hero-05.jpg");
    warn.mockRestore();
  });

  it("hides controls when only one image is available", () => {
    renderCarousel(HERO_IMAGES.slice(0, 1));
    expect(activeSrc()).toBe("/hero.png");
    expect(screen.queryByRole("button", { name: "Next hero image" })).not.toBeInTheDocument();
  });
});

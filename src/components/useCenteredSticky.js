"use client";

import { useLayoutEffect } from "react";

/**
 * Pins a sticky element in the middle of the screen below the PolicyEngine
 * shell's sticky bar: sets its `top` from its height, again whenever its
 * height (a new chart) or the window changes. An element too tall to center
 * sits 24px under the bar.
 */
export default function useCenteredSticky(ref, enabled = true) {
  useLayoutEffect(() => {
    const element = ref.current;
    if (!enabled || !element) return undefined;
    const place = () => {
      const bar = parseFloat(getComputedStyle(element).getPropertyValue("--spacing-header")) || 58;
      const room = window.innerHeight - bar;
      element.style.top = `${bar + Math.max(24, (room - element.offsetHeight) / 2)}px`;
    };
    place();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(place);
    observer?.observe(element);
    window.addEventListener("resize", place);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", place);
    };
  }, [ref, enabled]);
}

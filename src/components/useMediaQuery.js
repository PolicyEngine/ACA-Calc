"use client";

import { useEffect, useState } from "react";

/**
 * Whether a CSS media query matches, kept up to date as the window changes.
 * False on the server and on the first render, so the markup matches before
 * hydration.
 */
export default function useMediaQuery(query) {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const list = window.matchMedia(query);
    const update = () => setMatches(list.matches);
    update();
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [query]);

  return matches;
}

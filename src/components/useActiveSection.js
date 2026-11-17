"use client";

import { useEffect, useState } from "react";

/**
 * The id of the section being read: the one crossing a line 40% down the
 * screen. Null until a section reaches that line. The section rail
 * highlights it.
 */
export default function useActiveSection(sections, enabled = true) {
  const [active, setActive] = useState(null);

  useEffect(() => {
    if (!enabled) return undefined;
    const elements = sections.map((section) => document.getElementById(section.id)).filter(Boolean);
    if (!elements.length || typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (visible.length) setActive(visible[0].target.id);
      },
      { rootMargin: "-40% 0px -59% 0px" }
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [sections, enabled]);

  return active;
}

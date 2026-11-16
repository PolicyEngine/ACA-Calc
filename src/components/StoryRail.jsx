"use client";

import { useEffect, useState } from "react";
import "./StoryRail.css";

/**
 * A "you are here" rail beside the Overview on wide screens: the story's
 * parts and sections, the one being read highlighted. Choosing one scrolls to
 * it without changing the address, which the app uses for its pages.
 */
function StoryRail({ sections, parts }) {
  const [active, setActive] = useState(sections[0]?.id);

  useEffect(() => {
    const elements = sections.map((section) => document.getElementById(section.id)).filter(Boolean);
    if (!elements.length || typeof IntersectionObserver === "undefined") return undefined;
    // The section crossing a line 40% down the screen is the one being read.
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting);
        if (visible.length) setActive(visible[0].target.id);
      },
      { rootMargin: "-40% 0px -59% 0px" }
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [sections]);

  const goTo = (id) => {
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };

  return (
    <nav className="story-rail" aria-label="Sections of the Overview">
      <ol>
        {sections.map((section) => (
          <li key={section.id}>
            {parts[section.id] && <p className="story-rail-part">{parts[section.id]}</p>}
            <button
              type="button"
              className={section.id === active ? "active" : ""}
              aria-current={section.id === active ? "location" : undefined}
              onClick={() => goTo(section.id)}
            >
              {section.title}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export default StoryRail;

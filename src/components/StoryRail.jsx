"use client";

import "./StoryRail.css";

/**
 * A "you are here" rail beside the Overview on wide screens: the story's
 * parts and sections, the one being read (`active`, from useActiveSection)
 * highlighted. Choosing one scrolls to it without changing the address, which
 * the app uses for its pages.
 */
function StoryRail({ sections, parts, active }) {
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

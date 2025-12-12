import { useState, useEffect, useRef, useCallback } from "react";
import HealthBenefitsChart from "./HealthBenefitsChart";
import "./AIExplanation.css";

// Parse markdown-style bold text
const parseContent = (text) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

// Individual scroll section
function AIScrollSection({ section, index, isActive, sectionRef }) {
  return (
    <div
      ref={sectionRef}
      className={`ai-scroll-section ${isActive ? "active" : ""}`}
      data-index={index}
    >
      <h3 className="ai-section-title">{section.title}</h3>
      <div className="ai-section-content">
        {section.content.split("\n\n").map((paragraph, i) => (
          <p key={i}>{parseContent(paragraph)}</p>
        ))}
      </div>
    </div>
  );
}

function AIExplanation({ sections, chartData, householdDescription, onClose }) {
  const [activeSection, setActiveSection] = useState(0);
  const textColumnRef = useRef(null);
  const sectionRefs = useRef([]);

  const currentSection = sections[activeSection] || sections[0];

  // Handle scroll to detect which section is in view
  const handleScroll = useCallback(() => {
    if (!textColumnRef.current) return;

    const container = textColumnRef.current;
    const containerRect = container.getBoundingClientRect();
    const containerMiddle = containerRect.top + containerRect.height / 3;

    let closestIndex = 0;
    let closestDistance = Infinity;

    sectionRefs.current.forEach((ref, index) => {
      if (ref) {
        const rect = ref.getBoundingClientRect();
        const sectionMiddle = rect.top + rect.height / 2;
        const distance = Math.abs(sectionMiddle - containerMiddle);

        if (distance < closestDistance) {
          closestDistance = distance;
          closestIndex = index;
        }
      }
    });

    if (closestIndex !== activeSection) {
      setActiveSection(closestIndex);
    }
  }, [activeSection]);

  useEffect(() => {
    const container = textColumnRef.current;
    if (container) {
      container.addEventListener("scroll", handleScroll);
      return () => container.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll]);

  // Click on indicator to scroll to section
  const scrollToSection = (index) => {
    const section = sectionRefs.current[index];
    if (section && textColumnRef.current) {
      section.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div className="ai-explanation-overlay">
      <div className="ai-explanation-container">
        <div className="ai-explanation-header">
          <div className="ai-header-content">
            <div className="ai-badge">AI Generated</div>
            <h2>{householdDescription}</h2>
          </div>
          <button className="ai-close-button" onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Section indicators */}
        <div className="ai-section-indicators">
          {sections.map((section, index) => (
            <button
              key={section.id}
              className={`ai-indicator ${activeSection === index ? "active" : ""} ${index < activeSection ? "completed" : ""}`}
              onClick={() => scrollToSection(index)}
              title={section.title}
            >
              <span className="indicator-number">{index + 1}</span>
              <span className="indicator-label">{section.title}</span>
            </button>
          ))}
        </div>

        <div className="ai-scrolly-container">
          <div className="ai-chart-column">
            <div className="ai-chart-sticky">
              <HealthBenefitsChart
                data={chartData}
                chartState={currentSection.chartState}
                householdInfo={{}}
              />
            </div>
          </div>

          <div className="ai-text-column" ref={textColumnRef}>
            {sections.map((section, index) => (
              <AIScrollSection
                key={section.id}
                section={section}
                index={index}
                isActive={activeSection === index}
                sectionRef={(el) => (sectionRefs.current[index] = el)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIExplanation;

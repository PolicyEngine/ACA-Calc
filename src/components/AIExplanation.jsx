import { useState, useEffect } from "react";
import { useInView } from "react-intersection-observer";
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
function AIScrollSection({ section, index, isActive, onInView }) {
  const { ref, inView } = useInView({
    threshold: 0.5,
    rootMargin: "-20% 0px -40% 0px",
  });

  useEffect(() => {
    if (inView) {
      onInView(index);
    }
  }, [inView, index, onInView]);

  return (
    <div
      ref={ref}
      className={`ai-scroll-section ${isActive ? "active" : ""}`}
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

  const currentSection = sections[activeSection] || sections[0];

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

          <div className="ai-text-column">
            {sections.map((section, index) => (
              <AIScrollSection
                key={section.id}
                section={section}
                index={index}
                isActive={activeSection === index}
                onInView={setActiveSection}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIExplanation;

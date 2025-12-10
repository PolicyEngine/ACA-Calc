import { useInView } from "react-intersection-observer";
import { useEffect } from "react";
import "./ScrollSection.css";

// Calculator URL - uses environment variable or defaults to localhost for development
const CALCULATOR_URL = import.meta.env.VITE_CALCULATOR_URL || "http://localhost:8501";

function ScrollSection({ section, index, isActive, onInView }) {
  const { ref, inView } = useInView({
    threshold: 0.5,
    rootMargin: "-20% 0px -40% 0px",
  });

  useEffect(() => {
    if (inView) {
      onInView(index);
    }
  }, [inView, index, onInView]);

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

  return (
    <div
      ref={ref}
      className={`scroll-section ${isActive ? "active" : ""}`}
      id={section.id}
    >
      <h2 className="section-title">{section.title}</h2>
      <div className="section-content">
        {section.content.split("\n\n").map((paragraph, i) => (
          <p key={i}>{parseContent(paragraph)}</p>
        ))}
      </div>
      {section.showCalculatorLink && (
        <a href={CALCULATOR_URL} target="_blank" rel="noopener noreferrer" className="calculator-button">
          Enter Custom Household
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </a>
      )}
    </div>
  );
}

export default ScrollSection;

import { useState, useEffect, useRef } from "react";
import CalculatorForm, { buildShareableUrl, shouldAutoLoadAi } from "./CalculatorForm";
import CalculatorResults from "./CalculatorResults";
import AIExplanation from "./AIExplanation";
import "./Calculator.css";

// API URL - uses environment variable or defaults to localhost for development
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

// Medicaid expansion states
const EXPANSION_STATES = [
  "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "HI", "IL", "IN", "IA",
  "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MO", "MT", "NE", "NV", "NH",
  "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SD", "UT",
  "VT", "VA", "WA", "WV"
];

// Medicaid adult thresholds by state (% FPL) - expansion states are 138%, non-expansion varies
const getMedicaidAdultThreshold = (state) => {
  if (EXPANSION_STATES.includes(state)) return 138;
  // Non-expansion states have very low or no coverage for adults
  const nonExpansionThresholds = {
    "AL": 18, "FL": 19, "GA": 33, "KS": 38, "MS": 27,
    "SC": 67, "TN": 96, "TX": 17, "WI": 100, "WY": 53
  };
  return nonExpansionThresholds[state] || 0;
};

// Medicaid child thresholds by state (% FPL)
const getMedicaidChildThreshold = (state) => {
  const thresholds = {
    "AL": 146, "AK": 208, "AZ": 147, "AR": 216, "CA": 269, "CO": 147,
    "CT": 201, "DE": 217, "DC": 324, "FL": 215, "GA": 252, "HI": 313,
    "ID": 190, "IL": 147, "IN": 218, "IA": 375, "KS": 174, "KY": 218,
    "LA": 217, "ME": 213, "MD": 322, "MA": 205, "MI": 217, "MN": 288,
    "MS": 215, "MO": 196, "MT": 266, "NE": 218, "NV": 205, "NH": 323,
    "NJ": 355, "NM": 303, "NY": 405, "NC": 216, "ND": 175, "OH": 211,
    "OK": 210, "OR": 305, "PA": 319, "RI": 266, "SC": 213, "SD": 209,
    "TN": 213, "TX": 206, "UT": 147, "VT": 317, "VA": 148, "WA": 317,
    "WV": 305, "WI": 306, "WY": 159
  };
  return thresholds[state] || 200;
};

// CHIP thresholds by state (% FPL) - upper limit for children
const getChipThreshold = (state) => {
  const thresholds = {
    "AL": 317, "AK": 208, "AZ": 209, "AR": 216, "CA": 269, "CO": 265,
    "CT": 323, "DE": 217, "DC": 324, "FL": 215, "GA": 252, "HI": 313,
    "ID": 190, "IL": 318, "IN": 262, "IA": 375, "KS": 250, "KY": 218,
    "LA": 255, "ME": 213, "MD": 322, "MA": 305, "MI": 217, "MN": 288,
    "MS": 215, "MO": 305, "MT": 266, "NE": 218, "NV": 205, "NH": 323,
    "NJ": 355, "NM": 303, "NY": 405, "NC": 216, "ND": 181, "OH": 211,
    "OK": 210, "OR": 305, "PA": 319, "RI": 266, "SC": 213, "SD": 209,
    "TN": 255, "TX": 206, "UT": 209, "VT": 317, "VA": 205, "WA": 317,
    "WV": 305, "WI": 306, "WY": 209
  };
  return thresholds[state] || 200;
};

// Cache TTL: 24 hours in milliseconds
const CACHE_TTL = 24 * 60 * 60 * 1000;

function getCacheKey(data) {
  const keyData = {
    age_head: data.age_head,
    age_spouse: data.age_spouse,
    dependent_ages: data.dependent_ages || [],
    state: data.state,
    county: data.county,
    zip_code: data.zip_code,
  };
  return `aca-calc-${JSON.stringify(keyData)}`;
}

function getFromCache(key) {
  try {
    const cached = localStorage.getItem(key);
    if (!cached) return null;
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp > CACHE_TTL) {
      localStorage.removeItem(key);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

function setInCache(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify({ data, timestamp: Date.now() }));
  } catch {
    // localStorage might be full or disabled
  }
}

function Calculator() {
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ percent: 0, message: "" });
  const [error, setError] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [pendingAiLoad, setPendingAiLoad] = useState(shouldAutoLoadAi());
  const aiTriggeredRef = useRef(false);

  const handleCalculate = async (data) => {
    setLoading(true);
    setError(null);
    setResults(null);
    setFormData(data);
    setAiExplanation(null);
    setProgress({ percent: 0, message: "Starting calculation..." });

    // Check client-side cache first
    const cacheKey = getCacheKey(data);
    const cached = getFromCache(cacheKey);
    if (cached) {
      setProgress({ percent: 100, message: "Using cached results" });
      setResults(cached);
      setLoading(false);
      return;
    }

    try {
      // Use streaming endpoint for progress updates
      const response = await fetch(`${API_URL}/api/calculate-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Calculation failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));

              if (event.step === "error") {
                throw new Error(event.error);
              }

              if (event.progress !== undefined) {
                setProgress({ percent: event.progress, message: event.message || "" });
              }

              if (event.step === "complete" && event.result) {
                setResults(event.result);
                setInCache(cacheKey, event.result);
              }
            } catch (parseErr) {
              if (parseErr.message !== "Unexpected end of JSON input") {
                console.error("SSE parse error:", parseErr);
              }
            }
          }
        }
      }
    } catch (err) {
      // Fallback to regular endpoint if streaming fails
      try {
        const response = await fetch(`${API_URL}/api/calculate`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Calculation failed");
        }

        const result = await response.json();
        setResults(result);
        setInCache(cacheKey, result);
      } catch (fallbackErr) {
        setError(fallbackErr.message || "An error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
      setProgress({ percent: 0, message: "" });
    }
  };

  // Find value at a specific income level
  const findValueAtIncome = (targetIncome, incomeArray, valueArray) => {
    if (!incomeArray || !valueArray) return 0;
    let closest = 0;
    let minDiff = Infinity;
    for (let i = 0; i < incomeArray.length; i++) {
      const diff = Math.abs(incomeArray[i] - targetIncome);
      if (diff < minDiff) {
        minDiff = diff;
        closest = i;
      }
    }
    return valueArray[closest] || 0;
  };

  const handleExplainWithAI = async (updateUrl = true) => {
    if (!results || !formData) return;

    setAiLoading(true);

    // Calculate sample income at 300% FPL (a typical middle-income point)
    const sampleIncome = results.fpl * 3;

    const hasChildren = (formData.dependent_ages || []).length > 0;

    const explainRequest = {
      age_head: formData.age_head,
      age_spouse: formData.age_spouse,
      dependent_ages: formData.dependent_ages || [],
      state: formData.state,
      county: formData.county,
      is_expansion_state: EXPANSION_STATES.includes(formData.state),
      fpl: results.fpl,
      slcsp: results.slcsp,
      fpl_400_income: results.fpl * 4,
      fpl_700_income: results.fpl * 7,
      medicaid_adult_threshold_pct: getMedicaidAdultThreshold(formData.state),
      medicaid_child_threshold_pct: getMedicaidChildThreshold(formData.state),
      chip_threshold_pct: hasChildren ? getChipThreshold(formData.state) : 0,
      sample_income: sampleIncome,
      ptc_baseline_at_sample: findValueAtIncome(sampleIncome, results.income, results.ptc_baseline),
      ptc_ira_at_sample: findValueAtIncome(sampleIncome, results.income, results.ptc_ira),
      ptc_700fpl_at_sample: findValueAtIncome(sampleIncome, results.income, results.ptc_700fpl),
    };

    try {
      const response = await fetch(`${API_URL}/api/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(explainRequest),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate explanation");
      }

      const data = await response.json();
      setAiExplanation(data);

      // Update URL to include ai=1 so it can be shared
      if (updateUrl) {
        const url = buildShareableUrl(formData, true);
        const hashPart = url.split("#")[1] || "";
        window.history.replaceState(null, "", `#${hashPart}`);
      }
    } catch (err) {
      setError(err.message || "Failed to generate AI explanation");
    } finally {
      setAiLoading(false);
      setPendingAiLoad(false);
    }
  };

  // Auto-trigger AI explanation if URL has ai=1 and results are available
  useEffect(() => {
    if (pendingAiLoad && results && formData && !aiExplanation && !aiLoading && !aiTriggeredRef.current) {
      aiTriggeredRef.current = true;
      handleExplainWithAI(false); // Don't update URL again since it already has ai=1
    }
  }, [pendingAiLoad, results, formData, aiExplanation, aiLoading]);

  return (
    <div className="calculator">
      <div className="calculator-layout">
        <div className="calculator-form-container">
          <h2 className="calculator-title">Calculate Your Premium Tax Credits</h2>
          <p className="calculator-subtitle">
            Enter your household information to see how ACA policy changes would affect your health insurance costs.
          </p>
          <CalculatorForm onCalculate={handleCalculate} loading={loading} />

          {error && (
            <div className="calculator-error">
              <p>{error}</p>
              <button onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}
        </div>

        <div className="calculator-results-container">
          {loading && (
            <div className="calculator-loading">
              <div className="progress-container">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${progress.percent}%` }}
                  />
                </div>
                <div className="progress-text">
                  <span className="progress-message">{progress.message || "Calculating..."}</span>
                  <span className="progress-percent">{progress.percent}%</span>
                </div>
              </div>
              <p className="loading-note">Running simulations for your household</p>
            </div>
          )}

          {results && !loading && (
            <>
              <div className="explain-ai-section">
                <button
                  className="explain-ai-button"
                  onClick={handleExplainWithAI}
                  disabled={aiLoading}
                >
                  {aiLoading ? (
                    <>
                      <span className="ai-spinner"></span>
                      Generating...
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      Explain with AI
                    </>
                  )}
                </button>
                <p className="explain-ai-hint">
                  Get a personalized walkthrough of how these policies affect your household
                </p>
              </div>
              <CalculatorResults data={results} />
            </>
          )}

          {!results && !loading && (
            <div className="calculator-placeholder">
              <div className="placeholder-icon">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M9 7h6m-6 4h6m-6 4h4m-7 5h10a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3>Enter Your Household Details</h3>
              <p>Fill out the form and click "Calculate" to see your projected premium tax credits under different policy scenarios.</p>
            </div>
          )}
        </div>
      </div>

      {/* AI Explanation Modal */}
      {aiExplanation && (
        <AIExplanation
          sections={aiExplanation.sections}
          chartData={{
            income: results.income,
            ptc_baseline: results.ptc_baseline,
            ptc_ira: results.ptc_ira,
            ptc_700fpl: results.ptc_700fpl,
            medicaid: results.medicaid,
            chip: results.chip,
            fpl: results.fpl,
          }}
          householdDescription={aiExplanation.household_description}
          onClose={() => setAiExplanation(null)}
        />
      )}
    </div>
  );
}

export default Calculator;

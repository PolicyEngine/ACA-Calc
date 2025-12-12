import { useState } from "react";
import CalculatorForm from "./CalculatorForm";
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

function Calculator() {
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const handleCalculate = async (data) => {
    setLoading(true);
    setError(null);
    setResults(null);
    setFormData(data);
    setAiExplanation(null);

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
    } catch (err) {
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setLoading(false);
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

  const handleExplainWithAI = async () => {
    if (!results || !formData) return;

    setAiLoading(true);

    // Calculate sample income at 300% FPL (a typical middle-income point)
    const sampleIncome = results.fpl * 3;

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
    } catch (err) {
      setError(err.message || "Failed to generate AI explanation");
    } finally {
      setAiLoading(false);
    }
  };

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
              <div className="loading-spinner"></div>
              <p>Calculating premium tax credits...</p>
              <p className="loading-note">This may take 10-30 seconds</p>
            </div>
          )}

          {results && !loading && (
            <>
              <CalculatorResults data={results} />
              <div className="explain-ai-section">
                <button
                  className="explain-ai-button"
                  onClick={handleExplainWithAI}
                  disabled={aiLoading}
                >
                  {aiLoading ? (
                    <>
                      <span className="ai-spinner"></span>
                      Generating explanation...
                    </>
                  ) : (
                    <>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h-1a2 2 0 100 4h1a7 7 0 01-7 7h-4a7 7 0 01-7-7h1a2 2 0 100-4H2a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" />
                      </svg>
                      Explain with AI
                    </>
                  )}
                </button>
                <p className="explain-ai-hint">
                  Get a personalized, interactive explanation of how these policies affect your household
                </p>
              </div>
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

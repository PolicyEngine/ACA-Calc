import { useState } from "react";
import CalculatorForm from "./CalculatorForm";
import CalculatorResults from "./CalculatorResults";
import "./Calculator.css";

// API URL - uses environment variable or defaults to localhost for development
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

function Calculator() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCalculate = async (formData) => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(`${API_URL}/api/calculate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Calculation failed");
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setLoading(false);
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
            <CalculatorResults data={results} />
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
    </div>
  );
}

export default Calculator;

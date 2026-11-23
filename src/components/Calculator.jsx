import { useState, useEffect, useRef } from "react";
import CalculatorForm, { buildShareableUrl, getLinkFromUrl, toRequest } from "./CalculatorForm";
import CalculatorResults from "./CalculatorResults";
import ExampleHouseholds from "./ExampleHouseholds";
import { API_URL } from "./api";
import { EXPANSION_STATES } from "./medicaidExpansion";
import "./Calculator.css";

// Cache TTL: 24 hours in milliseconds
const CACHE_TTL = 24 * 60 * 60 * 1000;

// Part of every browser cache key: change it when the API's answers change for
// the same request (a new policyengine-us pin), so no one sees the old ones.
// The suffix marks answers with the credit's income (magi) and the credit at
// exactly 400% FPL.
const CACHE_VERSION = "policyengine-us-2.138.2-magi";

function getCacheKey(data) {
  const keyData = {
    version: CACHE_VERSION,
    year: data.year,
    show_prior_year: data.show_prior_year,
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

// Store an answer only if it is for the year asked. Right after a relaunch,
// Vercel serves this page before the new API is deployed, and the previous
// API answers every request for 2026 without naming a year; caching that
// would show the 2026 answer for a day.
function cacheIfForYear(key, request, result) {
  if (result?.year === request.year) setInCache(key, result);
}

function setInCache(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify({ data, timestamp: Date.now() }));
  } catch {
    // localStorage might be full or disabled
  }
}

// The results tab and income when no link chose them.
const NO_LINK_VIEW = { tab: "net", income: null };

function Calculator() {
  // What the page's link (#calculator?...) asks for, read when it opens.
  const [link] = useState(() => getLinkFromUrl());
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(false);
  // The step the server reports, shown under the spinner.
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState(null);
  // Current law in 2026 and 2027 by default; the form's checkbox adds 2027
  // under H.R. 1834, which the API returns with every calculation.
  const [compareEnhanced, setCompareEnhanced] = useState(link.compare);
  // The results tab and income a link opens on, until another household is
  // calculated or chosen; and the ones on screen, for the page's link.
  const [linkView, setLinkView] = useState({ tab: link.view, income: link.income });
  const [view, setView] = useState(NO_LINK_VIEW);
  const [shareMessage, setShareMessage] = useState("");
  // The Overview's four households with their stored results
  // (precompute_calculator_examples.py), loaded with the page.
  const [examples, setExamples] = useState([]);
  const [selectedExample, setSelectedExample] = useState(null);
  // The form remounts with new values only when an example is chosen, so
  // editing an example and calculating keeps the edits.
  const [formPreset, setFormPreset] = useState({ key: "initial", values: null });
  const resultsRef = useRef(null);
  const linkRunRef = useRef(false);

  useEffect(() => {
    import("../data/households/calculator_examples.json")
      .then((module) => setExamples((module.default || module).examples || []))
      .catch(() => setExamples([]));
  }, []);

  const scrollToResults = () => {
    requestAnimationFrame(() =>
      resultsRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" })
    );
  };

  // Fill the form with an example and show its stored result, without a request.
  const handleSelectExample = (example) => {
    const request = example.request;
    const values = {
      age_head: request.age_head,
      age_spouse: request.age_spouse ?? request.age_head,
      married: request.age_spouse != null,
      num_dependents: request.dependent_ages.length,
      dependent_ages: request.dependent_ages,
      state: request.state,
      county: request.county,
      zip_code: request.zip_code || "",
    };
    setFormPreset({ key: `${example.key}-${Date.now()}`, values });
    setSelectedExample(example);
    setFormData(request);
    setResults(example.response);
    setError(null);
    setLoading(false);
    setLinkView(NO_LINK_VIEW);
    scrollToResults();
  };

  const handleCalculate = async (data, { fromLink = false } = {}) => {
    setSelectedExample(null);
    if (!fromLink) setLinkView(NO_LINK_VIEW);
    scrollToResults();
    setLoading(true);
    setError(null);
    setResults(null);
    setFormData(data);
    setProgressMessage("");

    // Check client-side cache first
    const cacheKey = getCacheKey(data);
    const cached = getFromCache(cacheKey);
    if (cached) {
      setResults(cached);
      setLoading(false);
      return;
    }

    try {
      // The streaming endpoint reports each step as it runs
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
      let gotResult = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let event;
          try {
            event = JSON.parse(line.slice(6));
          } catch (parseErr) {
            if (parseErr.message !== "Unexpected end of JSON input") {
              console.error("SSE parse error:", parseErr);
            }
            continue;
          }

          // The server reports a failure as an event inside an HTTP 200:
          // stop reading, so the regular endpoint is tried and its error shown
          if (event.step === "error") {
            reader.cancel().catch(() => {});
            throw new Error(event.error || "Calculation failed");
          }

          if (event.message) setProgressMessage(event.message);

          if (event.step === "complete" && event.result) {
            gotResult = true;
            setResults(event.result);
            cacheIfForYear(cacheKey, data, event.result);
          }
        }
      }

      // A stream that closes without a result falls back too, rather than
      // leaving the page blank
      if (!gotResult) {
        throw new Error("The calculation ended without a result");
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
        cacheIfForYear(cacheKey, data, result);
      } catch (fallbackErr) {
        setError(fallbackErr.message || "An error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
      setProgressMessage("");
    }
  };

  // A link with a household calculates it when the page opens, so the link
  // lands on its results.
  useEffect(() => {
    if (linkRunRef.current || !link.form) return;
    linkRunRef.current = true;
    handleCalculate(toRequest(link.form), { fromLink: true });
  }, []);

  // The page's link follows what it shows, so the address and the share
  // button both reopen these results.
  const pageLink = formData
    ? buildShareableUrl(formData, {
        compare: compareEnhanced,
        view: view.tab,
        income: view.income,
      })
    : null;
  useEffect(() => {
    if (pageLink) window.history.replaceState(null, "", `#${pageLink.split("#")[1]}`);
  }, [pageLink]);

  const handleShare = () => {
    const say = (message) => {
      setShareMessage(message);
      setTimeout(() => setShareMessage(""), 2000);
    };
    if (!navigator.clipboard) return say("Failed to copy");
    navigator.clipboard.writeText(pageLink).then(
      () => say("Link copied!"),
      () => say("Failed to copy")
    );
  };

  return (
    <div className="calculator">
      <div className="calculator-layout">
        <div className="calculator-intro">
          <h2 className="calculator-title">Calculate your premium tax credits</h2>
          <p className="calculator-subtitle">
            See what a household would pay for the benchmark plan in 2026 and 2027 under current
            law. Check the comparison box to add 2027 under H.R. 1834, which would revive the
            enhanced credits.
          </p>
        </div>

        <ExampleHouseholds
          examples={examples}
          selectedKey={selectedExample?.key}
          onSelect={handleSelectExample}
          compareEnhanced={compareEnhanced}
          expansionStates={EXPANSION_STATES}
        />

        <div className="calculator-form-container">
          <h3 className="calculator-form-heading">Your household</h3>
          <CalculatorForm
            key={formPreset.key}
            initialValues={formPreset.values}
            onCalculate={handleCalculate}
            loading={loading}
            compareEnhanced={compareEnhanced}
            onCompareChange={setCompareEnhanced}
          />

          {error && (
            <div className="calculator-error">
              <p>{error}</p>
              <button onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}
        </div>

        <div className="calculator-results-container" ref={resultsRef}>
          {loading && (
            <div className="calculator-loading" role="status">
              <span className="loading-spinner" aria-hidden="true" />
              <p className="loading-message">{progressMessage || "Calculating..."}</p>
              <p className="loading-note">Running simulations for your household</p>
            </div>
          )}

          {results && !loading && (
            <>
              {selectedExample && (
                <p className="example-result-note">
                  Results for the example household: {selectedExample.name.toLowerCase()},{" "}
                  {selectedExample.description}.
                </p>
              )}
              <CalculatorResults
                key={selectedExample ? `example-${selectedExample.key}` : "custom"}
                data={results}
                formData={formData}
                compareEnhanced={compareEnhanced}
                initialTab={selectedExample ? "net" : linkView.tab}
                initialIncome={selectedExample?.income ?? linkView.income}
                storedAtIncome={
                  selectedExample?.at_income
                    ? { income: selectedExample.income, answer: selectedExample.at_income }
                    : null
                }
                onViewChange={setView}
              />
              <div className="results-share">
                <button
                  type="button"
                  className="share-button"
                  onClick={handleShare}
                  title="Copy a link to these results"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13" />
                  </svg>
                  Share results
                </button>
                {shareMessage && <span className="share-message" role="status">{shareMessage}</span>}
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
              <h3>Choose an example or enter your household</h3>
              <p>Results appear here: benchmark premiums and premium tax credits for 2026 and 2027.</p>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

export default Calculator;

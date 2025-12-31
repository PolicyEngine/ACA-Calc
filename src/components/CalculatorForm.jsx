import { useState, useEffect, useCallback } from "react";
import counties from "../../counties.json";
import "./Calculator.css";

const STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
];

const STATE_NAMES = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California",
  CO: "Colorado", CT: "Connecticut", DE: "Delaware", FL: "Florida", GA: "Georgia",
  HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa",
  KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland",
  MA: "Massachusetts", MI: "Michigan", MN: "Minnesota", MS: "Mississippi", MO: "Missouri",
  MT: "Montana", NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey",
  NM: "New Mexico", NY: "New York", NC: "North Carolina", ND: "North Dakota", OH: "Ohio",
  OK: "Oklahoma", OR: "Oregon", PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina",
  SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont",
  VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
  DC: "District of Columbia",
};

// Parse URL query parameters from hash
const getUrlParams = () => {
  const hash = window.location.hash.slice(1);
  const queryIndex = hash.indexOf("?");
  if (queryIndex === -1) return new URLSearchParams();
  return new URLSearchParams(hash.slice(queryIndex + 1));
};

// Build a shareable URL with household configuration
const buildShareableUrl = (formData, includeAi = false) => {
  const params = new URLSearchParams();
  // Use defaults for empty values in URL
  const ageHead = formData.age_head === "" ? 40 : formData.age_head;
  const ageSpouse = formData.age_spouse === "" ? 40 : formData.age_spouse;
  const depAges = formData.dependent_ages.map(age => age === "" ? 10 : age);

  params.set("age", ageHead);
  if (formData.married) {
    params.set("spouse", ageSpouse);
  }
  if (depAges.length > 0) {
    params.set("deps", depAges.join(","));
  }
  params.set("state", formData.state);
  params.set("county", formData.county);
  if (formData.zip_code) {
    params.set("zip", formData.zip_code);
  }
  if (!formData.show_ira) params.set("ira", "0");
  if (!formData.show_700fpl) params.set("700fpl", "0");
  if (formData.show_additional_bracket) params.set("additional", "1");
  if (formData.show_simplified_bracket) params.set("simplified", "1");
  if (includeAi) params.set("ai", "1");

  const baseUrl = window.location.origin + window.location.pathname;
  return `${baseUrl}#calculator?${params.toString()}`;
};

// Check if AI explanation should auto-load from URL
const shouldAutoLoadAi = () => {
  const params = getUrlParams();
  return params.get("ai") === "1";
};

// Export for use in Calculator component
export { buildShareableUrl, shouldAutoLoadAi };

// Parse form data from URL parameters
const getFormDataFromUrl = () => {
  const params = getUrlParams();
  if (!params.has("state") && !params.has("age")) return null;

  const state = params.get("state") || "";
  const county = params.get("county") || "";
  const depsStr = params.get("deps");
  const dependentAges = depsStr ? depsStr.split(",").map(a => parseInt(a, 10)).filter(a => !isNaN(a)) : [];

  return {
    age_head: parseInt(params.get("age"), 10) || 40,
    age_spouse: parseInt(params.get("spouse"), 10) || 40,
    married: params.has("spouse"),
    num_dependents: dependentAges.length,
    dependent_ages: dependentAges,
    state: STATES.includes(state) ? state : "",
    county: county,
    zip_code: params.get("zip") || "",
    show_ira: params.get("ira") !== "0",
    show_700fpl: params.get("700fpl") !== "0",
    show_additional_bracket: params.get("additional") === "1",
    show_simplified_bracket: params.get("simplified") === "1",
  };
};

// Generate random initial values
const getRandomDefaults = () => {
  const randomAge = Math.floor(Math.random() * (64 - 18 + 1)) + 18; // 18-64
  const randomState = STATES[Math.floor(Math.random() * STATES.length)];
  const stateCounties = counties[randomState] || [];
  const randomCounty = stateCounties[Math.floor(Math.random() * stateCounties.length)] || "";

  return { age: randomAge, state: randomState, county: randomCounty };
};

// Get initial form data - prefer URL params, fall back to random
const getInitialFormData = () => {
  const urlData = getFormDataFromUrl();
  if (urlData && urlData.state) {
    return urlData;
  }
  const defaults = getRandomDefaults();
  return {
    age_head: defaults.age,
    age_spouse: defaults.age,
    married: false,
    num_dependents: 0,
    dependent_ages: [],
    state: defaults.state,
    county: defaults.county,
    zip_code: "",
    show_ira: true,
    show_700fpl: true,
    show_additional_bracket: false,
    show_simplified_bracket: false,
  };
};

function CalculatorForm({ onCalculate, loading }) {
  const [formData, setFormData] = useState(getInitialFormData);
  const [availableCounties, setAvailableCounties] = useState([]);
  const [shareMessage, setShareMessage] = useState("");

  // Update URL when form is submitted
  const updateUrl = useCallback((data) => {
    const url = buildShareableUrl(data);
    const hashPart = url.split("#")[1] || "";
    window.history.replaceState(null, "", `#${hashPart}`);
  }, []);

  // Copy shareable URL to clipboard
  const handleShare = useCallback(() => {
    const url = buildShareableUrl(formData);
    navigator.clipboard.writeText(url).then(() => {
      setShareMessage("Link copied!");
      setTimeout(() => setShareMessage(""), 2000);
    }).catch(() => {
      setShareMessage("Failed to copy");
      setTimeout(() => setShareMessage(""), 2000);
    });
  }, [formData]);

  // Update available counties when state changes
  useEffect(() => {
    if (formData.state && counties[formData.state]) {
      const stateCounties = counties[formData.state].sort();
      setAvailableCounties(stateCounties);
      // Set first county as default if current county not in list
      if (!stateCounties.includes(formData.county)) {
        setFormData(prev => ({ ...prev, county: stateCounties[0] || "" }));
      }
    } else {
      setAvailableCounties([]);
    }
  }, [formData.state]);

  // Update dependent ages array when num_dependents changes
  useEffect(() => {
    const numDeps = formData.num_dependents === "" ? 0 : formData.num_dependents;
    const newAges = [...formData.dependent_ages];
    while (newAges.length < numDeps) {
      newAges.push(10); // Default age for new dependents
    }
    while (newAges.length > numDeps) {
      newAges.pop();
    }
    if (JSON.stringify(newAges) !== JSON.stringify(formData.dependent_ages)) {
      setFormData(prev => ({ ...prev, dependent_ages: newAges }));
    }
  }, [formData.num_dependents]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => {
      const newData = {
        ...prev,
        [name]: type === "checkbox" ? checked : value,
      };
      // When married is checked, default spouse age to head's age
      if (name === "married" && checked) {
        newData.age_spouse = prev.age_head;
      }
      return newData;
    });
  };

  const handleNumberChange = (e) => {
    const { name, value } = e.target;
    // Allow empty string while typing, store as string temporarily
    setFormData(prev => ({
      ...prev,
      [name]: value === "" ? "" : parseInt(value, 10),
    }));
  };

  const handleDependentAgeChange = (index, value) => {
    const newAges = [...formData.dependent_ages];
    // Allow empty string while typing
    newAges[index] = value === "" ? "" : parseInt(value, 10);
    setFormData(prev => ({ ...prev, dependent_ages: newAges }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Convert any empty strings to default values for submission
    const ageHead = formData.age_head === "" ? 40 : formData.age_head;
    const ageSpouse = formData.age_spouse === "" ? 40 : formData.age_spouse;
    const numDeps = formData.num_dependents === "" ? 0 : formData.num_dependents;
    const depAges = formData.dependent_ages.slice(0, numDeps).map(age => age === "" ? 10 : age);

    const submitData = {
      age_head: ageHead,
      age_spouse: formData.married ? ageSpouse : null,
      dependent_ages: depAges,
      state: formData.state,
      county: formData.county,
      zip_code: formData.zip_code || null,
      show_ira: formData.show_ira,
      show_700fpl: formData.show_700fpl,
      show_additional_bracket: formData.show_additional_bracket,
      show_simplified_bracket: formData.show_simplified_bracket,
    };

    // Update form with normalized values
    const normalizedFormData = {
      ...formData,
      age_head: ageHead,
      age_spouse: ageSpouse,
      dependent_ages: depAges,
    };

    // Update URL with form data for sharing
    updateUrl(normalizedFormData);

    onCalculate(submitData);
  };

  const needsZipCode = formData.state === "CA" && formData.county === "Los Angeles County";

  return (
    <form onSubmit={handleSubmit} className="calculator-form">
      {/* Household Composition */}
      <div className="form-section">
        <h3 className="form-section-title">Household Composition</h3>

        <div className="form-row">
          <label className="form-label">
            <input
              type="checkbox"
              name="married"
              checked={formData.married}
              onChange={handleChange}
              disabled={loading}
            />
            Married / Filing Jointly
          </label>
        </div>

        <div className="form-row form-row-inline">
          <div className="form-field">
            <label htmlFor="age_head">Your Age</label>
            <input
              type="number"
              id="age_head"
              name="age_head"
              min="18"
              max="64"
              value={formData.age_head}
              onChange={handleNumberChange}
              disabled={loading}
            />
            {formData.age_head > 64 && (
              <span className="form-hint form-hint-warning">Adults 65+ are typically eligible for Medicare, not marketplace coverage</span>
            )}
          </div>

          {formData.married && (
            <div className="form-field">
              <label htmlFor="age_spouse">Spouse Age</label>
              <input
                type="number"
                id="age_spouse"
                name="age_spouse"
                min="18"
                max="64"
                value={formData.age_spouse}
                onChange={handleNumberChange}
                disabled={loading}
              />
              {formData.age_spouse > 64 && (
                <span className="form-hint form-hint-warning">Adults 65+ are typically eligible for Medicare, not marketplace coverage</span>
              )}
            </div>
          )}
        </div>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="num_dependents">Number of Dependents</label>
            <input
              type="number"
              id="num_dependents"
              name="num_dependents"
              min="0"
              max="10"
              value={formData.num_dependents}
              onChange={handleNumberChange}
              disabled={loading}
            />
          </div>
        </div>

        {formData.num_dependents > 0 && (
          <div className="form-row dependent-ages">
            <label>Dependent Ages</label>
            <div className="dependent-ages-grid">
              {formData.dependent_ages.map((age, index) => (
                <input
                  key={index}
                  type="number"
                  min="0"
                  max="25"
                  value={age}
                  onChange={(e) => handleDependentAgeChange(index, e.target.value)}
                  disabled={loading}
                  placeholder={`Child ${index + 1}`}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Location */}
      <div className="form-section">
        <h3 className="form-section-title">Location</h3>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="state">State</label>
            <select
              id="state"
              name="state"
              value={formData.state}
              onChange={handleChange}
              disabled={loading}
            >
              {STATES.map(state => (
                <option key={state} value={state}>
                  {STATE_NAMES[state]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="county">County</label>
            <select
              id="county"
              name="county"
              value={formData.county}
              onChange={handleChange}
              disabled={loading}
            >
              {availableCounties.map(county => (
                <option key={county} value={county}>
                  {county}
                </option>
              ))}
            </select>
          </div>
        </div>

        {needsZipCode && (
          <div className="form-row">
            <div className="form-field">
              <label htmlFor="zip_code">ZIP Code</label>
              <input
                type="text"
                id="zip_code"
                name="zip_code"
                maxLength="5"
                value={formData.zip_code}
                onChange={handleChange}
                disabled={loading}
                placeholder="Required for LA County"
              />
              <span className="form-hint">Los Angeles County has multiple rating areas</span>
            </div>
          </div>
        )}
      </div>

      {/* Policy Scenarios */}
      <div className="form-section">
        <h3 className="form-section-title">Policy Scenarios</h3>

        <div className="form-row">
          <label className="form-label checkbox-label">
            <input
              type="checkbox"
              name="show_ira"
              checked={formData.show_ira}
              onChange={handleChange}
              disabled={loading}
            />
            <span>
              <strong>IRA Extension</strong>
              <span className="checkbox-description">8.5% cap, no income limit above 400% FPL</span>
            </span>
          </label>
        </div>

        <div className="form-row">
          <label className="form-label checkbox-label">
            <input
              type="checkbox"
              name="show_700fpl"
              checked={formData.show_700fpl}
              onChange={handleChange}
              disabled={loading}
            />
            <span>
              <strong>700% FPL Bill</strong>
              <span className="checkbox-description">Bipartisan bill extending to 700% FPL with 9.25% cap</span>
            </span>
          </label>
        </div>

        <div className="form-row">
          <label className="form-label checkbox-label">
            <input
              type="checkbox"
              name="show_additional_bracket"
              checked={formData.show_additional_bracket}
              onChange={handleChange}
              disabled={loading}
            />
            <span>
              <strong>Additional Bracket</strong>
              <span className="checkbox-description">Linear extension beyond 400% FPL with gradual phase-out</span>
            </span>
          </label>
        </div>

        <div className="form-row">
          <label className="form-label checkbox-label">
            <input
              type="checkbox"
              name="show_simplified_bracket"
              checked={formData.show_simplified_bracket}
              onChange={handleChange}
              disabled={loading}
            />
            <span>
              <strong>Simplified Bracket</strong>
              <span className="checkbox-description">Single linear phase-out starting at 100% FPL</span>
            </span>
          </label>
        </div>
      </div>

      <div className="form-actions">
        <button
          type="submit"
          className="calculate-button"
          disabled={loading || (!formData.show_ira && !formData.show_700fpl && !formData.show_additional_bracket && !formData.show_simplified_bracket)}
        >
          {loading ? "Calculating..." : "Calculate Premium Tax Credits"}
        </button>

        <button
          type="button"
          className="share-button"
          onClick={handleShare}
          disabled={loading}
          title="Copy shareable link to clipboard"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M16 6l-4-4-4 4M12 2v13" />
          </svg>
          Share
        </button>
        {shareMessage && <span className="share-message">{shareMessage}</span>}
      </div>

      {!formData.show_ira && !formData.show_700fpl && !formData.show_additional_bracket && !formData.show_simplified_bracket && (
        <p className="form-warning">Please select at least one policy scenario</p>
      )}
    </form>
  );
}

export default CalculatorForm;

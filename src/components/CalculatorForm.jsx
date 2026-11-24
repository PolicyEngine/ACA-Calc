import { useState, useEffect } from "react";
import counties from "../../counties.json";
import "./Calculator.css";

const STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
];

// Every calculation is for 2027 coverage under current law and under H.R.
// 1834, with 2026 current law alongside.
export const YEAR = 2027;

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

// The calculator's links (#calculator?...) carry the household and what the
// results show: the comparison, the results tab and the income entered.
const VIEWS = ["net", "credit", "impact"];

// A link to a calculation, from the request the API was sent.
const buildShareableUrl = (request, { compare = false, view = "net", income = null } = {}) => {
  const params = new URLSearchParams();
  params.set("age", request.age_head);
  if (request.age_spouse != null) params.set("spouse", request.age_spouse);
  if (request.dependent_ages?.length) params.set("deps", request.dependent_ages.join(","));
  params.set("state", request.state);
  params.set("county", request.county);
  if (request.zip_code) params.set("zip", request.zip_code);
  if (compare) params.set("compare", "1");
  if (view !== "net" && VIEWS.includes(view)) params.set("view", view);
  if (income > 0) params.set("income", String(income));

  const baseUrl = window.location.origin + window.location.pathname;
  return `${baseUrl}#calculator?${params.toString()}`;
};

// The request the API takes, from the form's values (empty fields take their
// defaults).
const toRequest = (form) => {
  const ageHead = form.age_head === "" ? 40 : form.age_head;
  const ageSpouse = form.age_spouse === "" ? 40 : form.age_spouse;
  const numDeps = form.num_dependents === "" ? 0 : form.num_dependents;
  return {
    year: YEAR,
    age_head: ageHead,
    age_spouse: form.married ? ageSpouse : null,
    dependent_ages: form.dependent_ages.slice(0, numDeps).map((age) => (age === "" ? 10 : age)),
    state: form.state,
    county: form.county,
    zip_code: form.zip_code || null,
    show_ira: true,
    show_prior_year: true,
  };
};

// The form's values from a link, or null without a valid state. A county
// that isn't in the state's list becomes its first county, as the form does.
const getFormDataFromUrl = () => {
  const params = getUrlParams();
  const state = params.get("state") || "";
  if (!STATES.includes(state)) return null;

  const stateCounties = [...(counties[state] || [])].sort();
  const county = params.get("county") || "";
  const depsStr = params.get("deps");
  const dependentAges = depsStr ? depsStr.split(",").map(a => parseInt(a, 10)).filter(a => !isNaN(a)) : [];

  // Links from before the calculator compared fixed scenarios also carry a
  // year and scenario choices; only the household is read.
  return {
    age_head: parseInt(params.get("age"), 10) || 40,
    age_spouse: parseInt(params.get("spouse"), 10) || 40,
    married: params.has("spouse"),
    num_dependents: dependentAges.length,
    dependent_ages: dependentAges,
    state,
    county: stateCounties.includes(county) ? county : stateCounties[0] || "",
    zip_code: params.get("zip") || "",
  };
};

// Everything a link asks for: the household (null without one) and what the
// results show.
const getLinkFromUrl = () => {
  const params = getUrlParams();
  const income = parseFloat(params.get("income"));
  const view = params.get("view");
  return {
    form: getFormDataFromUrl(),
    compare: params.get("compare") === "1",
    view: VIEWS.includes(view) ? view : "net",
    income: income > 0 ? income : null,
  };
};

export { buildShareableUrl, getLinkFromUrl, toRequest };

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
  };
};

function CalculatorForm({ onCalculate, loading, compareEnhanced = false, onCompareChange, initialValues = null }) {
  // An example household's values when one was chosen (the parent remounts
  // the form then); otherwise the link's household or random defaults.
  const [formData, setFormData] = useState(() => initialValues || getInitialFormData());
  const [availableCounties, setAvailableCounties] = useState([]);
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

  // The calculator keeps the page's link in step with the results.
  const handleSubmit = (e) => {
    e.preventDefault();
    onCalculate(toRequest(formData));
  };

  const needsZipCode = formData.state === "CA" && formData.county === "Los Angeles County";

  return (
    <form onSubmit={handleSubmit} className="calculator-form">
      {/* Household Composition */}
      <div className="form-section">
        <h3 className="form-section-title">Household composition</h3>

        <div className="form-row">
          <label className="form-label">
            <input
              type="checkbox"
              name="married"
              checked={formData.married}
              onChange={handleChange}
              disabled={loading}
            />
            Married, filing jointly
          </label>
        </div>

        <div className="form-row form-row-inline">
          <div className="form-field">
            <label htmlFor="age_head">Your age</label>
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
              <label htmlFor="age_spouse">Spouse age</label>
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
            <label htmlFor="num_dependents">Number of dependents</label>
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
            <label>Dependent ages</label>
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
              <label htmlFor="zip_code">ZIP code</label>
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

      {/* Comparison: changes what the results show, not the calculation */}
      <div className="form-section">
        <h3 className="form-section-title">Comparison</h3>
        <label className="compare-toggle">
          <input
            type="checkbox"
            checked={compareEnhanced}
            onChange={(event) => onCompareChange?.(event.target.checked)}
          />
          <span>
            <strong>Compare with the enhanced credits</strong>
            <span className="compare-toggle-detail">
              Add 2027 under H.R. 1834, which would revive the 2021–2025 enhanced subsidies
            </span>
          </span>
        </label>
      </div>

      <div className="form-actions">
        <button
          type="submit"
          className="calculate-button"
          disabled={loading}
        >
          {loading ? "Calculating…" : "Calculate premium tax credits"}
        </button>
      </div>
    </form>
  );
}

export default CalculatorForm;

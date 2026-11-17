import "./ExampleHouseholds.css";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

// The stored result at the example's income: what the household pays for the
// benchmark plan after the credit, per month.
function monthlyPayments(example) {
  const r = example.response;
  let i = 0;
  for (let k = 1; k < r.income.length; k++) {
    if (Math.abs(r.income[k] - example.income) < Math.abs(r.income[i] - example.income)) i = k;
  }
  const net = (benchmark, credit) => Math.max(0, (benchmark || 0) - (credit || 0)) / 12;
  return {
    current: net(r.slcsp_by_income?.[i], r.ptc_baseline?.[i]),
    revived: net(r.slcsp_by_income?.[i], r.ptc_ira?.[i]),
  };
}

/**
 * The Overview's four households as cards. Choosing one fills the form and
 * shows its stored result (precompute_calculator_examples.py) without a
 * request.
 */
function ExampleHouseholds({ examples, selectedKey, onSelect, compareEnhanced, expansionStates = [] }) {
  if (!examples?.length) return null;
  return (
    <section className="example-households" aria-labelledby="example-households-heading">
      <h3 id="example-households-heading">Example households</h3>
      <p className="example-households-intro">
        The four households from the Overview. Select one to see its results, or enter your own
        household below.
      </p>
      <div className="example-households-grid">
        {examples.map((example) => {
          const pays = monthlyPayments(example);
          const selected = selectedKey === example.key;
          const expansion = expansionStates.includes(example.request?.state);
          return (
            <button
              key={example.key}
              type="button"
              className={`example-card${selected ? " selected" : ""}`}
              aria-pressed={selected}
              onClick={() => onSelect(example)}
            >
              <span className="example-card-name">{example.name}</span>
              <span className="example-card-detail">
                {example.description} · {formatCurrency(example.income)}
              </span>
              {example.request?.state && (
                <span className={`example-card-badge${expansion ? " expansion" : ""}`}>
                  {expansion ? "Medicaid expansion state" : "No Medicaid expansion"}
                </span>
              )}
              <span className="example-card-value">
                {formatCurrency(pays.current)}
                <span className="example-card-unit">/month in 2027</span>
              </span>
              {compareEnhanced && (
                <span className="example-card-reform">
                  {formatCurrency(pays.revived)}/month under H.R. 1834
                </span>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default ExampleHouseholds;

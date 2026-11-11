import "./ExampleHouseholdsTable.css";

// Four households at one income each, from precompute_households.py.
import examples from "../data/households/examples.json";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
const monthly = (annual) => formatCurrency(annual / 12);
const percentChange = (from, to) => {
  const change = (100 * (to - from)) / from;
  return `${change >= 0 ? "+" : "−"}${Math.abs(change).toFixed(1)}%`;
};

/**
 * The example households' monthly benchmark premiums in 2026 and 2027 (view
 * "benchmark"), or what each pays for its benchmark plan after the credit in
 * 2026 and 2027 under current law and in 2027 under H.R. 1834 (view "net").
 */
function ExampleHouseholdsTable({ view = "net" }) {
  const { year, prior_year: priorYear } = examples;
  const benchmark = view === "benchmark";

  return (
    <div className="examples-table">
      <div className="examples-table-header">
        <h3>
          {benchmark
            ? "Benchmark premiums, per month"
            : "What each household pays for its benchmark plan, per month"}
        </h3>
        <p>
          {benchmark
            ? "The second-lowest-cost silver plan in each household's county, before any credit"
            : "The benchmark premium minus the premium tax credit"}
        </p>
      </div>
      <table>
        <thead>
          <tr>
            <th>Household</th>
            <th>{priorYear}</th>
            <th>{year}</th>
            <th>{benchmark ? "Change" : `${year}, H.R. 1834`}</th>
          </tr>
        </thead>
        <tbody>
          {examples.examples.map((example) => {
            const prior = example.scenarios[`current_${priorYear}`];
            const current = example.scenarios[`current_${year}`];
            const revived = example.scenarios[`hr1834_${year}`];
            return (
              <tr key={example.key}>
                <td>
                  <div className="example-name">
                    {example.name}, {formatCurrency(example.income)}
                  </div>
                  <div className="example-detail">
                    {example.description} · {current.fpl_percent}% FPL
                  </div>
                </td>
                {benchmark ? (
                  <>
                    <td>{monthly(prior.slcsp)}</td>
                    <td>{monthly(current.slcsp)}</td>
                    <td className="example-change">{percentChange(prior.slcsp, current.slcsp)}</td>
                  </>
                ) : (
                  <>
                    <td>{monthly(prior.net_premium)}</td>
                    <td>{monthly(current.net_premium)}</td>
                    <td className="example-revived">{monthly(revived.net_premium)}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="examples-table-note">
        Current law in {priorYear} and {year}. Each household has the same income in both years.
      </p>
    </div>
  );
}

export default ExampleHouseholdsTable;

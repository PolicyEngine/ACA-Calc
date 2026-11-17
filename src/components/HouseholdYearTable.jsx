import "./ExampleHouseholdsTable.css";
// The example households at one income each, from precompute_households.py.
import examples from "../data/households/examples.json";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
const monthly = (annual) => formatCurrency(annual / 12);

/**
 * Example households, one below and one above 400% FPL: each one's monthly
 * benchmark premium, credit and payment for the benchmark plan, one column per
 * scenario: "prior" (current law in the prior year), "current" (current law)
 * and "revived" (H.R. 1834). The Overview adds a column as the story moves on,
 * as the earlier version of the app did.
 */
function HouseholdYearTable({ householdKeys = ["texas_single", "pennsylvania_single"], columns = ["prior", "current"] }) {
  const { year, prior_year: priorYear } = examples;
  const labels = {
    prior: `${priorYear}, current law`,
    current: `${year}, current law`,
    revived: `${year}, H.R. 1834`,
  };
  const scenarioKey = {
    prior: `current_${priorYear}`,
    current: `current_${year}`,
    revived: `hr1834_${year}`,
  };
  const rows = [
    { label: "Benchmark premium", value: (v) => v.slcsp },
    { label: "Premium tax credit", value: (v) => v.ptc },
    { label: "Paid for the benchmark plan", value: (v) => v.net_premium, total: true },
  ];
  return (
    <div className="examples-table">
      <h3 className="chart-title">Two single adults, per month</h3>
      <p className="chart-subtitle">The benchmark premium, the credit, and what each pays for the benchmark plan</p>
      <div className="examples-table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col"></th>
              {columns.map((key) => (
                <th key={key} scope="col">
                  {labels[key]}
                </th>
              ))}
            </tr>
          </thead>
          {householdKeys.map((key) => {
            const household = examples.examples.find((example) => example.key === key);
            const fplPercent = household.scenarios[scenarioKey.current].fpl_percent;
            return (
              <tbody key={key}>
                <tr className="household-group">
                  <th scope="rowgroup" colSpan={columns.length + 1}>
                    {household.description}, {formatCurrency(household.income)}: {fplPercent > 400 ? "above" : "below"}{" "}
                    400% FPL
                  </th>
                </tr>
                {rows.map((row) => (
                  <tr key={row.label} className={row.total ? "household-total" : undefined}>
                    <th scope="row">{row.label}</th>
                    {columns.map((column) => (
                      <td key={column} className={column === "revived" ? "example-revived" : undefined}>
                        {monthly(row.value(household.scenarios[scenarioKey[column]]))}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            );
          })}
        </table>
      </div>
      <p className="chart-note">Each household has the same income in each year.</p>
    </div>
  );
}

export default HouseholdYearTable;

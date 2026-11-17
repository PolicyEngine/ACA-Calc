import "./ExampleHouseholdsTable.css";
// One example household's results, from precompute_households.py.
import examples from "../data/households/examples.json";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
const monthly = (annual) => formatCurrency(annual / 12);

/**
 * One household's monthly benchmark premium, credit and payment for the
 * benchmark plan, one column per scenario: "prior" (current law in the prior
 * year), "current" (current law) and "revived" (H.R. 1834). The Overview adds a
 * column as the story moves on, as the earlier version of the app did.
 */
function HouseholdYearTable({ householdKey = "pennsylvania_single", columns = ["prior", "current"] }) {
  const { year, prior_year: priorYear } = examples;
  const household = examples.examples.find((example) => example.key === householdKey);
  const scenarios = {
    prior: { label: `${priorYear}, current law`, values: household.scenarios[`current_${priorYear}`] },
    current: { label: `${year}, current law`, values: household.scenarios[`current_${year}`] },
    revived: { label: `${year}, H.R. 1834`, values: household.scenarios[`hr1834_${year}`] },
  };
  const shown = columns.map((key) => ({ key, ...scenarios[key] }));
  const rows = [
    { label: "Benchmark premium", value: (v) => v.slcsp },
    { label: "Premium tax credit", value: (v) => v.ptc },
    { label: "Paid for the benchmark plan", value: (v) => v.net_premium, total: true },
  ];
  return (
    <div className="examples-table">
      <h3 className="chart-title">
        {household.name}, {formatCurrency(household.income)}: per month
      </h3>
      <p className="chart-subtitle">{household.description}</p>
      <div className="examples-table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col"></th>
              {shown.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className={row.total ? "household-total" : undefined}>
                <th scope="row">{row.label}</th>
                {shown.map((column) => (
                  <td key={column.key} className={column.key === "revived" ? "example-revived" : undefined}>
                    {monthly(row.value(column.values))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="chart-note">
        {scenarios.current.values.fpl_percent}% of the federal poverty line in {year}. The household has the same
        income in each year.
      </p>
    </div>
  );
}

export default HouseholdYearTable;

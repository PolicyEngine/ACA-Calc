import "./ExampleHouseholdsTable.css";
// The Pennsylvania example across incomes, from precompute_cliff_household.py.
import cliffDemoData from "../data/households/cliff_demo.json";

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
const monthly = (annual) => formatCurrency(annual / 12);

/**
 * The Pennsylvania example at one income: its annual benchmark premium, credit
 * and payment for the benchmark plan under current law in the prior year
 * ("prior") and the coverage year ("current"), and under H.R. 1834 ("revived").
 */
export function householdAt(income) {
  const i = cliffDemoData.income.indexOf(income);
  if (i < 0) throw new Error(`cliff_demo.json has no income of ${income}`);
  const scenario = (slcsp, ptc) => ({ slcsp, ptc, net: Math.max(0, slcsp - ptc) });
  return {
    income,
    prior: scenario(cliffDemoData.slcsp_by_income_prior_year[i], cliffDemoData.ptc_prior_year[i]),
    current: scenario(cliffDemoData.slcsp_by_income[i], cliffDemoData.ptc_baseline[i]),
    revived: scenario(cliffDemoData.slcsp_by_income[i], cliffDemoData.ptc_ira[i]),
  };
}

/**
 * The same adult at two incomes, one below and one above 400% FPL: monthly
 * benchmark premium, credit and payment, one column per scenario. The Overview
 * adds a column as the story moves on, as the earlier version of the app did.
 */
function HouseholdYearTable({ incomes = [50000, 104000], columns = ["prior", "current"] }) {
  const { year, prior_year: priorYear, household_info: info } = cliffDemoData;
  const labels = {
    prior: `${priorYear}, current law`,
    current: `${year}, current law`,
    revived: `${year}, H.R. 1834`,
  };
  const cliffIncome = 4 * cliffDemoData.fpl;
  const rows = [
    { label: "Benchmark premium", value: (v) => v.slcsp },
    { label: "Premium tax credit", value: (v) => v.ptc },
    { label: "Paid for the benchmark plan", value: (v) => v.net, total: true },
  ];
  return (
    <div className="examples-table">
      <h3 className="chart-title">
        A {info.age}-year-old in {info.location}: per month
      </h3>
      <p className="chart-subtitle">The same benchmark plan at two incomes</p>
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
          {incomes.map((income) => {
            const household = householdAt(income);
            return (
              <tbody key={income}>
                <tr className="household-group">
                  <th scope="rowgroup" colSpan={columns.length + 1}>
                    Earning {formatCurrency(income)}: {income > cliffIncome ? "above" : "below"} 400% FPL
                  </th>
                </tr>
                {rows.map((row) => (
                  <tr key={row.label} className={row.total ? "household-total" : undefined}>
                    <th scope="row">{row.label}</th>
                    {columns.map((key) => (
                      <td key={key} className={key === "revived" ? "example-revived" : undefined}>
                        {monthly(row.value(household[key]))}
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

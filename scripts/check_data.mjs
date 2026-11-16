// Checks that the precomputed data files agree before the app builds, so a
// figure on the page can't drift from the others. Runs before `next build`
// (package.json); exits 1 with a list of problems. No dependencies.
//
//   node scripts/check_data.mjs

import { readFileSync } from "node:fs";

const FILES = {
  cliff: "households/cliff_demo.json",
  examples: "households/examples.json",
  schedules: "contribution_schedules.json",
  national: "national_impacts.json",
  calculator: "households/calculator_examples.json",
};

const read = (path) =>
  JSON.parse(readFileSync(new URL(`../src/data/${path}`, import.meta.url), "utf8"));
const data = Object.fromEntries(Object.entries(FILES).map(([key, path]) => [key, read(path)]));

const problems = [];
const check = (ok, message) => {
  if (!ok) problems.push(message);
};

// 1. Every file comes from the same policyengine-us release.
const versions = Object.fromEntries(Object.entries(data).map(([key, d]) => [key, d.model_version]));
check(
  new Set(Object.values(versions)).size === 1,
  `the data files come from different policyengine-us versions: ${JSON.stringify(versions)}`
);

// 2. The same coverage year.
const year = data.national.year;
for (const key of ["cliff", "examples", "calculator"]) {
  check(data[key].year === year, `${FILES[key]} is for ${data[key].year}, national_impacts.json for ${year}`);
}

// 3. The national figures add up: H.R. 1834's credits less current law's are
// the cost, and every SPM unit is measured.
const national = data.national;
const law = national.current_law[String(year)];
const cost = national.enhanced.total_ptc - law.total_ptc;
check(
  Math.abs(cost - national.budget.federal_cost) < 1e7,
  `national cost ${national.budget.federal_cost} differs from H.R. 1834's credits less current law's (${cost})`
);
check(national.checks.spm_units_not_measured === 0, "some SPM units are not measured");

// 4. The calculator's stored examples match the Overview's table, at each
// household's income, to the dollar a month.
const overview = Object.fromEntries(data.examples.examples.map((e) => [e.key, e]));
const net = (benchmark, credit) => Math.max(0, benchmark - credit) / 12;
for (const example of data.calculator.examples) {
  const table = overview[example.key];
  if (!table) {
    problems.push(`calculator example ${example.key} is not in the Overview's table`);
    continue;
  }
  const r = example.response;
  let i = 0;
  r.income.forEach((income, k) => {
    if (Math.abs(income - example.income) < Math.abs(r.income[i] - example.income)) i = k;
  });
  const stored = {
    [`current_${year - 1}`]: net(r.slcsp_by_income_prior_year[i], r.ptc_prior_year[i]),
    [`current_${year}`]: net(r.slcsp_by_income[i], r.ptc_baseline[i]),
    [`hr1834_${year}`]: net(r.slcsp_by_income[i], r.ptc_ira[i]),
  };
  for (const [scenario, value] of Object.entries(stored)) {
    const expected = table.scenarios[scenario].net_premium / 12;
    check(
      Math.abs(value - expected) < 1,
      `${example.key}, ${scenario}: the calculator pays $${value.toFixed(2)}/month, the Overview $${expected.toFixed(2)}`
    );
  }
}

// 5. The Pennsylvania sweep's marginal rates cover every income.
const cliff = data.cliff;
for (const key of ["mtr_baseline", "mtr_ira", "net_income_baseline", "net_income_ira"]) {
  check(cliff[key]?.length === cliff.income.length, `cliff_demo.json's ${key} doesn't match its incomes`);
}

if (problems.length) {
  console.error(`Data check failed (${problems.length}):\n- ${problems.join("\n- ")}`);
  process.exit(1);
}
console.log(
  `Data check passed: policyengine-us ${versions.national}, ${year}, ${data.calculator.examples.length} calculator examples match the Overview.`
);

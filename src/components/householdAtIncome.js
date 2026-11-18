// Reads a scenario's results at an income between the API's $1,000 steps.
//
// Between most steps the credit changes smoothly, so a straight line is close.
// Where eligibility changes it jumps, and a straight line would blend a
// household that qualifies with one that doesn't. In those steps the answer
// comes from one side of the limit:
//   - the credit's limits at 100% and 400% FPL are known exactly;
//   - Medicaid and CHIP limits vary by state and aren't in the API's answer, so
//     the closest income calculated stands in, and the result says so (`edge`).

// A smooth change in the credit over one $1,000 step stays below this (annual):
// the most a household's required contribution rises over a step.
const LARGEST_SMOOTH_CHANGE = 300;

export const closestIndex = (income, incomes) => {
  let closest = 0;
  for (let i = 0; i < incomes.length; i++) {
    if (Math.abs(incomes[i] - income) < Math.abs(incomes[closest] - income)) {
      closest = i;
    }
  }
  return closest;
};

// Whether eligibility changes between incomes[i] and incomes[i + 1].
const eligibilityChanges = (i, { benchmark, credit, upperLimit }, incomes) => {
  // The benchmark covers the members who can use the credit, so it moves only
  // when someone joins or leaves the marketplace.
  if (Math.abs(benchmark[i + 1] - benchmark[i]) > 1) return true;
  const falls = credit[i] > 0 && credit[i + 1] === 0;
  if (falls && upperLimit > incomes[i] && upperLimit <= incomes[i + 1]) return true;
  const rises = credit[i] === 0 && credit[i + 1] > 0;
  return (falls || rises) && Math.abs(credit[i + 1] - credit[i]) > LARGEST_SMOOTH_CHANGE;
};

// Which end of the step applies, or null when the limit's position is unknown.
const knownSide = (income, i, { credit, lowerLimit, upperLimit }, incomes) => {
  const inStep = (limit) => limit > incomes[i] && limit <= incomes[i + 1];
  if (credit[i] > 0 && credit[i + 1] === 0 && inStep(upperLimit)) {
    // 26 U.S.C. 36B(c)(1)(A): income that "does not exceed 400 percent" qualifies.
    return income <= upperLimit ? i : i + 1;
  }
  if (credit[i] === 0 && credit[i + 1] > 0 && inStep(lowerLimit)) {
    return income >= lowerLimit ? i + 1 : i;
  }
  return null;
};

// A value carried from a step's end toward the income, along the neighboring
// step on the same side of the limit.
const carried = (values, end, income, incomes, scenario, stepBefore) => {
  const neighbor = end === stepBefore ? end - 1 : end + 1;
  const neighborStep = Math.min(end, neighbor);
  if (neighbor < 0 || neighbor >= incomes.length || eligibilityChanges(neighborStep, scenario, incomes)) {
    return values[end];
  }
  const slope = (values[end] - values[neighbor]) / (incomes[end] - incomes[neighbor]);
  return Math.max(0, values[end] + slope * (income - incomes[end]));
};

/**
 * A scenario's annual amounts at an income.
 *
 * @param {number} income - Annual household income.
 * @param {number[]} incomes - The API's incomes, ascending.
 * @param {object} scenario
 * @param {number[]} scenario.benchmark - Benchmark premium at each income.
 * @param {number[]} scenario.credit - Premium tax credit at each income.
 * @param {number} [scenario.lowerLimit] - Income where the credit starts (100% FPL).
 * @param {number} [scenario.upperLimit] - Income where the credit ends (400% FPL), if it does.
 * @returns {{benchmark: number, credit: number, net: number, edge: ?{from: number, to: number, shownAt: number}}}
 */
export function scenarioAtIncome(income, incomes, scenario) {
  const { benchmark, credit } = scenario;
  const result = (premium, amount, edge = null) => ({
    benchmark: premium,
    credit: amount,
    net: Math.max(0, premium - amount),
    edge,
  });

  const last = incomes.length - 1;
  if (income >= incomes[last]) return result(benchmark[last], credit[last]);
  if (income <= incomes[0]) return result(benchmark[0], credit[0]);

  let i = 0;
  while (incomes[i + 1] < income) i++;
  // policyengine-us 2.138.2 ends the credit at exactly 400% FPL, one dollar early,
  // so a calculated income on that limit is read from the side that qualifies.
  const onUpperLimit = income === scenario.upperLimit && credit[i] > 0 && credit[i + 1] === 0;
  if (incomes[i + 1] === income && !onUpperLimit) return result(benchmark[i + 1], credit[i + 1]);

  if (!eligibilityChanges(i, scenario, incomes)) {
    const share = (income - incomes[i]) / (incomes[i + 1] - incomes[i]);
    const between = (values) => values[i] + (values[i + 1] - values[i]) * share;
    return result(between(benchmark), between(credit));
  }

  const side = knownSide(income, i, scenario, incomes);
  const end = side ?? closestIndex(income, incomes);
  return result(
    carried(benchmark, end, income, incomes, scenario, i),
    carried(credit, end, income, incomes, scenario, i),
    side === null ? { from: incomes[i], to: incomes[i + 1], shownAt: incomes[end] } : null
  );
}

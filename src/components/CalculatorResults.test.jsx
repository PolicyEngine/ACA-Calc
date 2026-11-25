// The "Your household" tab's text, rendered from answers shaped as
// /api/calculate-at-income returns them. Each scenario's fpl is the guideline
// its credit uses, the year before's (policyengine-us 2.138.2, gov.hhs.fpg):
// $15,650 for one person in 2025 plus $5,500 for each other member, and
// $15,960 in 2026 plus $5,680.
import { describe, expect, test } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";
import { Explanation, NewYorkMidYearNote } from "./CalculatorResults";

// The members in the API's order and with its names: head, spouse, dependents.
function household(head, spouse, dependents = []) {
  const people = [{ name: "you", age: head, relationship: "head" }];
  if (spouse) people.push({ name: "your partner", age: spouse, relationship: "spouse" });
  const names = ["your first dependent", "your second dependent"];
  dependents.forEach((age, i) =>
    people.push({ name: names[i] ?? `dependent_${i + 1}`, age, relationship: "dependent" })
  );
  return people;
}

// What covers one member. Answers from an API that predates Basic Health
// Program coverage lack that field.
function covers(programs = {}, { reportsBasicHealth = true } = {}) {
  const member = { medicaid: false, chip: false, medicaid_work_requirement: false, ...programs };
  if (reportsBasicHealth) member.basic_health_program ??= false;
  return member;
}
const OLD_API = { reportsBasicHealth: false };

const scenario = (year, fields) => ({ year, benchmark: 0, credit: 0, full_premium: 0, ...fields });

const explain = (answer, state) =>
  renderToStaticMarkup(
    <Explanation answer={answer} state={state} year={answer.year} compareEnhanced={false} />
  );
const note = (answer, state) =>
  renderToStaticMarkup(<NewYorkMidYearNote answer={answer} state={state} year={answer.year} />);

describe("Explanation", () => {
  // A Minnesota couple aged 40 and 38 with children aged 8 and 5, earning
  // $50,000 in 2026: 155% of the 2025 guideline for four ($32,150). Medicaid
  // covers the children. The model has MinnesotaCare covering the adults, so
  // it prices no plan and gives no credit, and this answer predates the
  // program's field.
  test("names MinnesotaCare for the adults and not the benchmark plan", () => {
    const coverage = [
      covers({}, OLD_API),
      covers({}, OLD_API),
      covers({ medicaid: true }, OLD_API),
      covers({ medicaid: true }, OLD_API),
    ];
    const current = scenario(2026, { magi: 50_000, fpl: 32_150, full_premium: 11_400, coverage });
    const people = household(40, 38, [8, 5]);
    const answer = { income: 50_000, year: 2026, people, current, ira: current };
    const text = explain(answer, "MN");
    expect(text).toBe(
      "<p>Medicaid would cover your children. In 2026, at 155% FPL, MinnesotaCare would cover " +
        "you and your spouse, so the model gives no credit.</p>"
    );
    expect(text).not.toContain("benchmark plan");
  });

  // A Pennsylvania couple aged 67 and 66 with a child aged 16, earning $40,000
  // in 2026: 150% of the 2025 guideline for three ($26,650). CHIP covers the
  // child, and the model prices no plan for members aged 65 or older.
  test("names Medicare for adults aged 65 or older and not the benchmark plan", () => {
    const coverage = [covers(), covers(), covers({ chip: true })];
    const current = scenario(2026, { magi: 40_000, fpl: 26_650, full_premium: 21_600, coverage });
    const people = household(67, 66, [16]);
    const answer = { income: 40_000, year: 2026, people, current, ira: current };
    const text = explain(answer, "PA");
    expect(text).toStartWith(
      "<p>CHIP would cover your child. In 2026, you and your spouse would qualify for Medicare at " +
        "age 65 or older"
    );
    expect(text).not.toContain("benchmark plan");
  });

  // A Texas couple aged 35 and 33 with children aged 8 and 6, earning $50,000
  // in 2026 (155% FPL). CHIP covers the children, and the adults get a credit.
  test("still says the benchmark plan covers the others where they get a credit", () => {
    const coverage = [covers(), covers(), covers({ chip: true }), covers({ chip: true })];
    const current = scenario(2026, {
      magi: 50_000,
      fpl: 32_150,
      benchmark: 12_000,
      credit: 9_905,
      full_premium: 12_000,
      coverage,
    });
    const answer = { income: 50_000, year: 2026, people: household(35, 33, [8, 6]), current };
    expect(explain(answer, "TX")).toStartWith(
      "<p>CHIP would cover your children, so the benchmark plan covers you and your spouse. " +
        "At 155% FPL,"
    );
  });
});

describe("NewYorkMidYearNote", () => {
  // One adult aged 40 in New York, on the Essential Plan in 2026, when the
  // model's limit is 250% FPL. The 2027 credit uses the 2026 guideline
  // ($15,960), so the July 2026 limit of 200% FPL is $31,920. The model tests
  // 2027 coverage against its 2027 guideline (about $16,427), so it keeps
  // incomes up to about $32,854 on the program in 2027.
  function newYorker(income, { onPlanIn2027 }) {
    const onPlan = [covers({ basic_health_program: true })];
    const current = onPlanIn2027
      ? scenario(2027, { magi: income, fpl: 15_960, coverage: onPlan })
      : scenario(2027, {
          magi: income,
          fpl: 15_960,
          benchmark: 9_600,
          credit: 6_900,
          full_premium: 9_600,
          coverage: [covers()],
        });
    const priorYear = scenario(2026, { magi: income, fpl: 15_650, coverage: onPlan });
    return { income, year: 2027, people: household(40), current, prior_year: priorYear };
  }
  const SAYS_FALL =
    "so for the rest of 2026 you would no longer qualify and could enroll in a Marketplace plan.";

  test("names a member the program keeps in 2027 whose 2026 income exceeds 200% FPL", () => {
    expect(note(newYorker(32_400, { onPlanIn2027: true }), "NY")).toContain(SAYS_FALL);
  });

  test("names no one at or below 200% of the 2026 guideline", () => {
    // $31,800 exceeds 200% of the 2025 guideline ($31,300), which the 2026
    // credit uses, so this also checks the note compares with the 2026 one.
    expect(note(newYorker(31_800, { onPlanIn2027: true }), "NY")).toBe("");
    // The program covers income at its limit.
    expect(note(newYorker(31_920, { onPlanIn2027: true }), "NY")).toBe("");
  });

  test("names a member no program covers in 2027", () => {
    expect(note(newYorker(36_000, { onPlanIn2027: false }), "NY")).toContain(SAYS_FALL);
  });

  // The program compares Medicaid income with the Medicaid household's
  // guideline, which can differ from the credit's income and tax family. This
  // answer holds the credit's income under the limit while the program leaves
  // the member out in 2027.
  test("names a member no program covers in 2027 whatever the credit's income", () => {
    expect(note(newYorker(31_900, { onPlanIn2027: false }), "NY")).toContain(SAYS_FALL);
  });

  test("names no one outside New York", () => {
    expect(note(newYorker(32_400, { onPlanIn2027: true }), "MN")).toBe("");
    expect(note(newYorker(36_000, { onPlanIn2027: false }), "MN")).toBe("");
  });
});

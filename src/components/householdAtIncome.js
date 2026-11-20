// The household at the earnings entered on the "Your household" tab, which the
// API calculates (/api/calculate-at-income) instead of the page reading between
// the income axis's $1,000 steps: eligibility limits and the share of income
// jump between those steps.
import { useEffect, useState } from "react";
import { API_URL } from "./api";

// The API calculates earnings up to this, as the income axis does.
export const MAX_EARNINGS = 1_000_000;

// How long typing pauses before the page asks, in milliseconds.
const PAUSE = 500;

// Answers already received while the page is open, by request and earnings.
const answers = new Map();

const answerKey = (request, income) => JSON.stringify({ ...request, income });

/**
 * The API's answer for a household at some earnings: each scenario's annual
 * benchmark premium, credit and full premium, the credit's income and
 * guideline, and what covers each member.
 *
 * @param {object} request - The calculator's request for the household.
 * @param {number} income - Annual earnings; nothing is asked outside 0 to $1,000,000.
 * @param {?{income: number, answer: object}} stored - An answer stored with the
 *   page (an example household's), used without a request at its earnings.
 * @returns {{status: "idle"|"loading"|"ready"|"error", answer: ?object, error: ?string}}
 */
export function useHouseholdAtIncome(request, income, stored = null) {
  const [state, setState] = useState({ status: "idle", answer: null, error: null });
  const requestKey = request ? JSON.stringify(request) : null;
  // The stored answer's parts, which keep their identity across renders.
  const storedIncome = stored?.income;
  const storedAnswer = stored?.answer;

  useEffect(() => {
    if (!requestKey || !(income > 0) || income > MAX_EARNINGS) {
      setState({ status: "idle", answer: null, error: null });
      return undefined;
    }
    if (storedAnswer && storedIncome === income) {
      setState({ status: "ready", answer: storedAnswer, error: null });
      return undefined;
    }
    const key = answerKey(JSON.parse(requestKey), income);
    if (answers.has(key)) {
      setState({ status: "ready", answer: answers.get(key), error: null });
      return undefined;
    }

    setState({ status: "loading", answer: null, error: null });
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`${API_URL}/api/calculate-at-income`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...JSON.parse(requestKey), income }),
          signal: controller.signal,
        });
        // The API before this endpoint, briefly live after a relaunch.
        if (response.status === 404) {
          throw new Error("The calculator's server is being updated. Try again in a few minutes.");
        }
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(typeof detail.detail === "string" ? detail.detail : "Calculation failed");
        }
        const answer = await response.json();
        answers.set(key, answer);
        setState({ status: "ready", answer, error: null });
      } catch (err) {
        if (err.name === "AbortError") return;
        setState({ status: "error", answer: null, error: err.message || "Calculation failed" });
      }
    }, PAUSE);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [requestKey, income, storedIncome, storedAnswer]);

  return state;
}

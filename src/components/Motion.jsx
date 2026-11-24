"use client";

// Scroll motion for the Overview (after the story components in
// PolicyEngine/uk-growth-with-ai): a fade-in for figures and a number that
// counts up. Both leave content as it is on the server, without JavaScript,
// and under prefers-reduced-motion.

import { useEffect, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import "./Motion.css";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Fades and lifts its children in the first time they scroll into view.
 * Something already on screen when the page mounts just shows.
 */
export function Reveal({ as: Tag = "div", className = "", children, ...rest }) {
  const node = useRef(null);
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.12 });
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const box = node.current?.getBoundingClientRect();
    const onScreen = box && box.top < window.innerHeight && box.bottom > 0;
    if (!prefersReducedMotion() && !onScreen) setArmed(true);
  }, []);
  const setRefs = (element) => {
    node.current = element;
    ref(element);
  };
  const state = !armed ? "" : inView ? " is-in" : " is-waiting";
  return (
    <Tag ref={setRefs} className={`reveal${state} ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}

const NUMBER = /(\d[\d,]*)(\.\d+)?/;
const DURATION = 600;

// `text` with its first number at `fraction` of its value, keeping its
// decimals, thousands separators and units.
function partial(text, fraction) {
  const match = NUMBER.exec(text);
  if (!match) return text;
  const decimals = match[2] ? match[2].length - 1 : 0;
  const target = Number(`${match[1].replace(/,/g, "")}${match[2] ?? ""}`);
  let shown = (target * fraction).toFixed(decimals);
  if (match[1].includes(",")) {
    const [whole, fractional] = shown.split(".");
    shown = Number(whole).toLocaleString("en-US") + (fractional ? `.${fractional}` : "");
  }
  return text.slice(0, match.index) + shown + text.slice(match.index + match[0].length);
}

/**
 * A figure that counts up once, when it first comes fully into view. The
 * exact value is always in the page (visually hidden) for screen readers and
 * copying; the moving copy is aria-hidden and ends on the same text.
 */
export function CountUp({ value }) {
  const text = String(value);
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 1 });
  const [fraction, setFraction] = useState(1);
  const ran = useRef(false);
  useEffect(() => {
    if (!inView || ran.current || prefersReducedMotion() || !NUMBER.test(text)) return undefined;
    ran.current = true;
    let frame = 0;
    const start = performance.now();
    const tick = (now) => {
      const k = Math.min(1, (now - start) / DURATION);
      setFraction(1 - (1 - k) ** 3);
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    setFraction(0);
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, text]);
  return (
    <span ref={ref} className="count-up">
      <span className="visually-hidden">{text}</span>
      <span aria-hidden="true">{fraction >= 1 ? text : partial(text, fraction)}</span>
    </span>
  );
}

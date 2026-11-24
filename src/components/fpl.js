/**
 * The credit's income as a share of the poverty line, in whole percents
 * rounded down, as Form 8962 line 5 has it. Just over 400% FPL rounds down to
 * 400, which still qualifies, so it's worded. The calculator's cards and its
 * charts both use this.
 */
export function fplPercentText(magi, fpl) {
  const percent = (100 * magi) / fpl;
  if (percent > 400 && percent < 401) return "just over 400";
  return String(Math.floor(percent));
}

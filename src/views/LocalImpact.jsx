import { useMemo, useState } from "react";
import countiesByState from "../../counties.json";
import CongressionalDistrictPremiumMap from "../components/CongressionalDistrictPremiumMap";
import {
  formatCurrency,
  formatNumber,
  getEnrollmentContext,
  getMarketplacePlatform,
  getStateName,
  platformConfig2026,
} from "../enrollmentContext";
import "./LocalImpact.css";

const DEFAULT_STATE = "TX";
const DEFAULT_COUNTY = "Travis County";

const getCountyOptions = (state) => [...(countiesByState[state] || [])].sort();

const statusText = {
  county_context_available: "County context available",
  policyengine_modeled_county_backfill: "PE modeled backfill",
  state_based_marketplace_fallback: "State-level fallback",
  not_in_compact_dataset: "Available in full PUF",
  unknown_state: "Unknown state",
};

const sortStatesByName = (states) =>
  [...states].sort((a, b) => getStateName(a).localeCompare(getStateName(b)));

const getStateLabel = (state) => {
  const platform = getMarketplacePlatform(state);
  if (platform === "HealthCare.gov") {
    return `${getStateName(state)} (${state})`;
  }
  if (platform === "State-based marketplace") {
    return `${getStateName(state)} (${state})`;
  }
  return getStateName(state);
};

const getPlatformDetail = (state) => {
  const platform = getMarketplacePlatform(state);
  if (platform === "HealthCare.gov") {
    return "County and ZIP enrollment PUF detail available";
  }
  if (platform === "State-based marketplace") {
    return "CMS state totals + PolicyEngine local backfill";
  }
  return "Platform unknown";
};

const getPlanSelectionsLabel = (context) =>
  context.policyengineModeled
    ? "Modeled marketplace plan selections"
    : context.stateContextAvailable && !context.countyContextAvailable
      ? "State marketplace plan selections"
      : "Marketplace plan selections";

const getAptcLabel = (context) =>
  context.policyengineModeled
    ? "Modeled APTC consumers"
    : context.stateContextAvailable && !context.countyContextAvailable
      ? "State APTC consumers"
      : "APTC consumers";

function Metric({ label, value, detail }) {
  return (
    <div className="local-metric">
      <span className="local-metric-label">{label}</span>
      <strong>{value}</strong>
      {detail && <span className="local-metric-detail">{detail}</span>}
    </div>
  );
}

function LocalImpact() {
  const [state, setState] = useState(DEFAULT_STATE);
  const [county, setCounty] = useState(DEFAULT_COUNTY);

  const stateGroups = useMemo(
    () => ({
      healthcareGov: sortStatesByName(
        Object.keys(countiesByState).filter(
          (stateCode) => getMarketplacePlatform(stateCode) === "HealthCare.gov",
        ),
      ),
      stateBased: sortStatesByName(
        Object.keys(countiesByState).filter(
          (stateCode) =>
            getMarketplacePlatform(stateCode) === "State-based marketplace",
        ),
      ),
    }),
    [],
  );
  const countyOptions = useMemo(() => getCountyOptions(state), [state]);
  const selectedCounty = countyOptions.includes(county)
    ? county
    : countyOptions[0] || "";

  const context = useMemo(
    () => getEnrollmentContext(state, selectedCounty),
    [state, selectedCounty],
  );

  const location = `${selectedCounty}, ${getStateName(state)}`;

  const selectState = (nextState) => {
    setState(nextState);
    setCounty(getCountyOptions(nextState)[0] || "");
  };

  const handleStateChange = (event) => {
    selectState(event.target.value);
  };

  return (
    <main className="local-impact-page">
      <section className="local-impact-heading">
        <p className="eyebrow">Local impact</p>
        <h2>Explore Marketplace enrollment and premium context</h2>
        <p>
          Select a geography, then compare CMS Marketplace enrollment context,
          average paid premiums, and APTC uptake by congressional district.
        </p>
      </section>

      <section className="local-impact-grid">
        <div className="local-panel local-selector-panel">
          <div className="local-panel-header">
            <h3>Geography</h3>
            <span className="local-year">2026 OEP</span>
          </div>

          <label className="local-field">
            <span>State</span>
            <select value={state} onChange={handleStateChange}>
              <optgroup label="HealthCare.gov states">
                {stateGroups.healthcareGov.map((stateCode) => (
                  <option key={stateCode} value={stateCode}>
                    {getStateLabel(stateCode)}
                  </option>
                ))}
              </optgroup>
              <optgroup label="State-based marketplaces">
                {stateGroups.stateBased.map((stateCode) => (
                  <option key={stateCode} value={stateCode}>
                    {getStateLabel(stateCode)}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>

          <div className="local-state-caption">
            <strong>{getStateName(state)}</strong>
            <span>{getPlatformDetail(state)}</span>
          </div>

          <label className="local-field">
            <span>County</span>
            <select
              value={selectedCounty}
              onChange={(event) => setCounty(event.target.value)}
              disabled={countyOptions.length === 0}
            >
              {countyOptions.map((countyName) => (
                <option key={countyName} value={countyName}>
                  {countyName}
                </option>
              ))}
            </select>
          </label>

          <div className="local-platform-summary">
            <span className="local-platform-label">Marketplace platform</span>
            <strong>{context.marketplacePlatform}</strong>
            <p>{platformConfig2026.fine_grained_puf_note}</p>
          </div>
        </div>

        <div className="local-panel local-context-panel">
          <div className="local-panel-header">
            <h3>{location}</h3>
            <span className={`status-pill status-${context.status}`}>
              {statusText[context.status] || "Context"}
            </span>
          </div>

          <p className="local-message">{context.message}</p>

          {context.countyContextAvailable || context.stateContextAvailable ? (
            <>
              {context.policyengineModeled && (
                <div className="local-backfill-note">
                  <strong>PolicyEngine-modeled local backfill</strong>
                  <p>
                    These county counts allocate observed CMS state totals using
                    PolicyEngine geography weights. They are not observed CMS
                    county enrollment rows.
                  </p>
                </div>
              )}

              <div className="local-metric-grid">
                <Metric
                  label={getPlanSelectionsLabel(context)}
                  value={formatNumber(context.marketplace_plan_selections)}
                  detail={
                    context.countyContextAvailable
                      ? `County FIPS ${context.county_fips}`
                      : "Observed CMS state total"
                  }
                />
                <Metric
                  label={getAptcLabel(context)}
                  value={formatNumber(context.aptc_consumers)}
                  detail={
                    context.consumers_with_aptc_or_csr
                      ? `${formatNumber(context.consumers_with_aptc_or_csr)} with APTC or CSR`
                      : "Observed CMS state total"
                  }
                />
                <Metric
                  label="Average APTC"
                  value={`${formatCurrency(context.average_aptc)}/mo`}
                  detail="Among APTC consumers"
                />
                <Metric
                  label="Average paid premium"
                  value={`${formatCurrency(context.average_premium_after_aptc)}/mo`}
                  detail={`${formatNumber(context.consumers_premium_after_aptc_lte_10)} pay $10 or less`}
                />
                {context.policyengineModeled && (
                  <Metric
                    label="Observed state plan selections"
                    value={formatNumber(context.stateMarketplacePlanSelections)}
                    detail={`${formatNumber(context.stateAptcConsumers)} state APTC consumers`}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="local-fallback">
              <strong>
                {context.fineGrainedCmsAvailable
                  ? "Full-PUF ingestion needed"
                  : "State-level/fallback only"}
              </strong>
              <p>
                {context.fineGrainedCmsAvailable
                  ? "This HealthCare.gov state has CMS county/ZIP PUF detail, but this county is not matched in the compact dataset yet."
                  : "State-based marketplace enrollment detail is reported outside the CMS county/ZIP PUF structure used in this first slice."}
              </p>
            </div>
          )}
        </div>

        <CongressionalDistrictPremiumMap
          onSelectState={selectState}
          selectedState={state}
        />
      </section>
    </main>
  );
}

export default LocalImpact;

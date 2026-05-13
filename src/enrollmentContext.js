import enrollmentFixture from "../aca_calc/data/enrollment_context_2026_counties.json";
import districtFixture from "../aca_calc/data/enrollment_context_2026_districts.json";
import platformConfig from "../aca_calc/data/marketplace_platforms_2026.json";

export const STATE_NAMES = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  DC: "District of Columbia",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
};

const normalizeState = (state) => (state || "").trim().toUpperCase();

const normalizeCounty = (county) => {
  let normalized = (county || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  for (const suffix of [
    " city and borough",
    " census area",
    " municipality",
    " borough",
    " county",
    " parish",
  ]) {
    if (normalized.endsWith(suffix)) {
      normalized = normalized.slice(0, -suffix.length).trim();
      break;
    }
  }

  return normalized;
};

const countyKeys = (county) => {
  const normalized = normalizeCounty(county);
  return [normalized, normalized.replace(/\s+/g, "")];
};

export const getMarketplacePlatform = (state) => {
  const stateCode = normalizeState(state);

  if (platformConfig.healthcare_gov_states.includes(stateCode)) {
    return "HealthCare.gov";
  }
  if (platformConfig.state_based_marketplace_states.includes(stateCode)) {
    return "State-based marketplace";
  }
  return "Unknown";
};

export const getStateName = (state) => {
  const stateCode = normalizeState(state);
  return STATE_NAMES[stateCode] || stateCode || "Unknown state";
};

export const getEnrollmentContext = (state, county) => {
  const stateCode = normalizeState(state);
  const platform = getMarketplacePlatform(stateCode);
  const baseContext = {
    year: enrollmentFixture.year,
    state: stateCode,
    county,
    marketplacePlatform: platform,
    source: enrollmentFixture.source,
    sourceUrl: enrollmentFixture.source_url,
  };

  if (platform === "Unknown") {
    return {
      ...baseContext,
      status: "unknown_state",
      fineGrainedCmsAvailable: false,
      countyContextAvailable: false,
      message: `${stateCode || "This state"} is not recognized in the 2026 Marketplace platform configuration.`,
    };
  }

  if (platform === "State-based marketplace") {
    return {
      ...baseContext,
      status: "state_based_marketplace_fallback",
      fineGrainedCmsAvailable: false,
      countyContextAvailable: false,
      message: `${stateCode} runs a state-based marketplace. CMS county/ZIP Marketplace PUF detail is not available here, so this view falls back to state-level context only.`,
    };
  }

  const selectedCountyKeys = new Set(countyKeys(county));
  const record = enrollmentFixture.records.find(
    (item) =>
      normalizeState(item.state) === stateCode &&
      countyKeys(item.county).some((key) => selectedCountyKeys.has(key)),
  );

  if (!record) {
    const location = county ? `${county}, ${stateCode}` : stateCode;
    return {
      ...baseContext,
      status: "not_in_compact_dataset",
      fineGrainedCmsAvailable: true,
      countyContextAvailable: false,
      message: `CMS county/ZIP PUF detail is available for ${stateCode}, but ${location} is not included in the checked-in compact county dataset yet.`,
    };
  }

  return {
    ...baseContext,
    ...record,
    county: record.county,
    status: "county_context_available",
    fineGrainedCmsAvailable: true,
    countyContextAvailable: true,
    message: `Fine-grained CMS county enrollment context is available for ${record.county}, ${stateCode}.`,
  };
};

export const getCongressionalDistrictPremiumContexts = () =>
  districtFixture.records.map((record) => {
    const planSelections = Number(record.marketplace_plan_selections);
    const aptcConsumers = Number(record.aptc_consumers);
    const nonAptcConsumers =
      Number.isFinite(planSelections) && Number.isFinite(aptcConsumers)
        ? Math.max(0, planSelections - aptcConsumers)
        : null;

    return {
      ...record,
      marketplace_plan_selections: Number.isFinite(planSelections)
        ? planSelections
        : null,
      aptc_consumers: Number.isFinite(aptcConsumers) ? aptcConsumers : null,
      non_aptc_consumers: nonAptcConsumers,
      average_premium: Number.isFinite(Number(record.average_premium))
        ? Number(record.average_premium)
        : null,
      average_premium_after_aptc: Number.isFinite(
        Number(record.average_premium_after_aptc),
      )
        ? Number(record.average_premium_after_aptc)
        : null,
      average_aptc: Number.isFinite(Number(record.average_aptc))
        ? Number(record.average_aptc)
        : null,
      marketplacePlatform: getMarketplacePlatform(record.state),
      premiumContextAvailable: Number.isFinite(
        Number(record.average_premium_after_aptc),
      ),
    };
  });

export const formatNumber = (value) =>
  new Intl.NumberFormat("en-US").format(value || 0);

export const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value || 0);

export const platformConfig2026 = platformConfig;
export const enrollmentSample = enrollmentFixture;
export const congressionalDistrictContext2026 = districtFixture;

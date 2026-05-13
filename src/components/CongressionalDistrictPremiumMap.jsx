import { useMemo, useState } from "react";
import { geoAlbersUsa, geoPath } from "d3";
import districtGeography from "../../aca_calc/data/congressional_districts_119_20m.json";
import {
  congressionalDistrictContext2026,
  formatCurrency,
  formatNumber,
  getCongressionalDistrictPremiumContexts,
  getMarketplacePlatform,
  getStateName,
} from "../enrollmentContext";

const MAP_WIDTH = 1120;
const MAP_HEIGHT = 720;

const MAP_COLORS = [
  "cd-bucket-1",
  "cd-bucket-2",
  "cd-bucket-3",
  "cd-bucket-4",
  "cd-bucket-5",
];

const MAP_METRICS = {
  paidPremium: {
    label: "Avg paid premium",
    field: "average_premium_after_aptc",
    type: "currency",
    description: "Average monthly premium consumers actually pay after APTC",
    unavailable: "No paid premium data",
  },
  aptcConsumers: {
    label: "Receiving APTC",
    field: "aptc_consumers",
    type: "count",
    description:
      "Population-weighted estimate of consumers receiving advance premium tax credits",
    unavailable: "No APTC recipient data",
  },
  nonAptcConsumers: {
    label: "Not receiving APTC",
    field: "non_aptc_consumers",
    type: "count",
    description:
      "Population-weighted estimate of consumers not receiving advance premium tax credits",
    unavailable: "No non-APTC estimate",
  },
};

const formatMetricValue = (value, metric) => {
  if (!Number.isFinite(value)) {
    return metric.unavailable;
  }

  if (metric.type === "currency") {
    return `${formatCurrency(value)}/mo`;
  }

  return `${formatNumber(value)} allocated`;
};

const formatLegendValue = (value, metric) =>
  metric.type === "currency" ? formatCurrency(value) : formatNumber(value);

const getNiceCountStep = (range) => {
  if (range >= 250000) {
    return 50000;
  }
  if (range >= 100000) {
    return 25000;
  }
  if (range >= 50000) {
    return 10000;
  }
  if (range >= 10000) {
    return 5000;
  }
  return 1000;
};

const getDistrictMetric = (district, metric) => {
  const value = Number(district?.[metric.field]);
  return Number.isFinite(value) ? value : null;
};

const buildMetricScale = (districts, metric) => {
  const values = districts
    .map((district) => getDistrictMetric(district, metric))
    .filter((value) => Number.isFinite(value));

  if (!values.length) {
    return [];
  }

  const rawRange = Math.max(...values) - Math.min(...values);
  const niceStep =
    metric.type === "currency" ? 50 : getNiceCountStep(rawRange);
  const min = Math.floor(Math.min(...values) / niceStep) * niceStep;
  const max = Math.ceil(Math.max(...values) / niceStep) * niceStep;
  const step = Math.max(niceStep, (max - min) / MAP_COLORS.length);

  return MAP_COLORS.map((className, index) => {
    const start = Math.round(min + step * index);
    const end = Math.round(min + step * (index + 1));
    return {
      className,
      min: start,
      max: end,
      label:
        index === MAP_COLORS.length - 1
          ? `${formatLegendValue(start, metric)}+`
          : `${formatLegendValue(start, metric)}-${formatLegendValue(end, metric)}`,
    };
  });
};

const bucketFor = (value, scale) => {
  if (!Number.isFinite(value) || !scale.length) {
    return null;
  }

  return (
    scale.find(
      (bucket, index) =>
        value >= bucket.min &&
        (value < bucket.max || index === scale.length - 1),
    ) || scale[scale.length - 1]
  );
};

const unavailableMessage = (state) => {
  const platform = getMarketplacePlatform(state);
  const stateName = getStateName(state);
  if (platform === "State-based marketplace") {
    return (
      `${stateName} runs a state-based marketplace, so CMS county/ZIP premium ` +
      "context is unavailable for its congressional districts in this slice."
    );
  }
  return `${stateName} has no matched district premium context in the compact dataset.`;
};

const formatDistrictName = (feature, context) => {
  const state = context?.state || feature?.properties.state;
  const district = context?.district || feature?.properties.district;
  const stateName = getStateName(state);

  if (!district || district === "00") {
    return `${stateName} at-large`;
  }

  return `${stateName} District ${Number(district)}`;
};

const formatDistrictSummary = (context) =>
  [
    `Population-weighted county allocation: ${formatNumber(
      context.marketplace_plan_selections,
    )} plan selections;`,
    `${formatNumber(context.aptc_consumers)} receive APTC and ${formatNumber(
      context.non_aptc_consumers,
    )} do not.`,
    `Average paid premium is ${formatCurrency(
      context.average_premium_after_aptc,
    )}/mo.`,
  ].join(" ");

function CongressionalDistrictPremiumMap({ selectedState, onSelectState }) {
  const [selectedGeoid, setSelectedGeoid] = useState(null);
  const [activeMetricKey, setActiveMetricKey] = useState("paidPremium");
  const activeMetric = MAP_METRICS[activeMetricKey];
  const districtContexts = useMemo(
    () => getCongressionalDistrictPremiumContexts(),
    [],
  );
  const scale = useMemo(
    () => buildMetricScale(districtContexts, activeMetric),
    [districtContexts, activeMetric],
  );
  const contextByGeoid = useMemo(
    () =>
      Object.fromEntries(
        districtContexts.map((district) => [
          district.district_geoid,
          district,
        ]),
      ),
    [districtContexts],
  );
  const features = districtGeography.features;
  const featureByGeoid = useMemo(
    () =>
      Object.fromEntries(
        features.map((feature) => [feature.properties.geoid, feature]),
      ),
    [features],
  );
  const path = useMemo(() => {
    const projection = geoAlbersUsa().fitSize(
      [MAP_WIDTH, MAP_HEIGHT],
      districtGeography,
    );
    return geoPath(projection);
  }, []);
  const selectedFeature = featureByGeoid[selectedGeoid];
  const selectedFeatureMatchesState =
    selectedFeature?.properties.state === selectedState;
  const firstStateFeature = features.find(
    (feature) => feature.properties.state === selectedState,
  );
  const activeFeature = selectedFeatureMatchesState
    ? selectedFeature
    : firstStateFeature;
  const activeGeoid = activeFeature?.properties.geoid;
  const activeContext = contextByGeoid[activeGeoid];
  const activeState = activeFeature?.properties.state || selectedState;
  const activeDistrictLabel = formatDistrictName(activeFeature, activeContext);
  const activeMetricValue = getDistrictMetric(activeContext, activeMetric);
  const activeMetricAvailable = Number.isFinite(activeMetricValue);
  const availableDistrictCount = districtContexts.filter(
    (district) => district.premiumContextAvailable,
  ).length;

  const selectDistrict = (feature) => {
    setSelectedGeoid(feature.properties.geoid);
    onSelectState(feature.properties.state);
  };

  const handleDistrictKeyDown = (event, feature) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectDistrict(feature);
    }
  };

  return (
    <section className="local-panel cd-map-panel">
      <div className="local-panel-header">
        <div>
          <h3>Marketplace premium and APTC map</h3>
          <p>
            Population-weighted congressional district estimates from CMS county
            PUFs.
          </p>
        </div>
        <span className="local-year">2026 OEP</span>
      </div>

      <div className="cd-map-tabs" aria-label="Map metric">
        {Object.entries(MAP_METRICS).map(([metricKey, metric]) => (
          <button
            aria-pressed={metricKey === activeMetricKey}
            className={`cd-map-tab ${metricKey === activeMetricKey ? "active" : ""}`}
            key={metricKey}
            onClick={() => setActiveMetricKey(metricKey)}
            type="button"
          >
            <span>{metric.label}</span>
            <small>{metric.description}</small>
          </button>
        ))}
      </div>

      <div className="cd-map-shell">
        <svg
          aria-label={`${activeMetric.label} by 119th congressional district`}
          className="cd-map-svg"
          role="group"
          viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
        >
          {features.map((feature) => {
            const districtPath = path(feature);
            if (!districtPath) {
              return null;
            }

            const districtContext = contextByGeoid[feature.properties.geoid];
            const metricValue = getDistrictMetric(
              districtContext,
              activeMetric,
            );
            const bucket = bucketFor(metricValue, scale);
            const platform = getMarketplacePlatform(feature.properties.state);
            const isSelected = activeGeoid === feature.properties.geoid;
            const isSelectedState =
              selectedState === feature.properties.state && !isSelected;
            const districtLabel = formatDistrictName(feature, districtContext);
            const ariaLabel = districtContext
              ? `${districtLabel}, ${activeMetric.label.toLowerCase()} ${formatMetricValue(
                  metricValue,
                  activeMetric,
                )}`
              : `${districtLabel}, ${platform} district premium context unavailable`;

            return (
              <path
                aria-label={ariaLabel}
                className={[
                  "cd-district",
                  bucket?.className || "cd-unavailable",
                  isSelectedState ? "same-state" : "",
                  isSelected ? "selected" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                d={districtPath}
                key={feature.properties.geoid}
                onClick={() => selectDistrict(feature)}
                onKeyDown={(event) => handleDistrictKeyDown(event, feature)}
                role="button"
                tabIndex="0"
              >
                <title>{ariaLabel}</title>
              </path>
            );
          })}
        </svg>
      </div>

      <div className="cd-map-footer">
        <div className="cd-map-legend" aria-label={`${activeMetric.label} color scale`}>
          {scale.map((bucket) => (
            <span className="cd-legend-item" key={bucket.className}>
              <span className={`cd-legend-swatch ${bucket.className}`} />
              {bucket.label}
            </span>
          ))}
          <span className="cd-legend-item">
            <span className="cd-legend-swatch cd-unavailable" />
            Unavailable
          </span>
        </div>

        <div className="cd-map-summary">
          <span>{activeDistrictLabel || getStateName(activeState)}</span>
          <strong>
            {activeContext
              ? formatMetricValue(activeMetricValue, activeMetric)
              : "No CMS district data"}
          </strong>
          <p>
            {activeContext && activeMetricAvailable
              ? formatDistrictSummary(activeContext)
              : unavailableMessage(activeState)}
          </p>
          {activeContext && activeMetricAvailable && (
            <div className="cd-summary-stats">
              <span>
                <strong>{formatCurrency(activeContext.average_aptc)}/mo</strong>
                avg APTC
              </span>
              <span>
                <strong>{formatNumber(activeContext.source_county_count)}</strong>
                source counties
              </span>
              <span>
                <strong>{formatNumber(activeContext.county_part_count)}</strong>
                county parts
              </span>
            </div>
          )}
        </div>
      </div>

      <p className="cd-map-note">
        Rough estimates for {formatNumber(availableDistrictCount)}{" "}
        HealthCare.gov-platform districts.{" "}
        {congressionalDistrictContext2026.allocation_method} ZIP-level CMS PUFs
        would further improve split-county districts where Marketplace
        enrollment differs from the general population.
      </p>
    </section>
  );
}

export default CongressionalDistrictPremiumMap;

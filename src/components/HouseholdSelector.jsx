import "./HouseholdSelector.css";

function HouseholdSelector({ households, selected, onSelect }) {
  return (
    <div className="household-selector">
      <span className="selector-label">Select a household:</span>
      <div className="selector-pills">
        {Object.entries(households).map(([key, household]) => (
          <button
            key={key}
            className={`selector-pill ${selected === key ? "active" : ""}`}
            onClick={() => onSelect(key)}
            title={household.description}
          >
            {household.shortName}
          </button>
        ))}
      </div>
    </div>
  );
}

export default HouseholdSelector;

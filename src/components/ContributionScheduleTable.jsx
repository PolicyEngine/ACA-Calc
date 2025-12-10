import "./ContributionScheduleTable.css";

// ACA contribution schedules by law
const SCHEDULES = {
  aca_original: {
    name: "Original ACA (2014-2020)",
    description: "Capped at 400% FPL",
    rows: [
      { fpl: "100-133%", rate: "2.0%" },
      { fpl: "133-150%", rate: "3.0-4.0%" },
      { fpl: "150-200%", rate: "4.0-6.3%" },
      { fpl: "200-250%", rate: "6.3-8.05%" },
      { fpl: "250-300%", rate: "8.05-9.5%" },
      { fpl: "300-400%", rate: "9.5%" },
      { fpl: ">400%", rate: "No subsidy", noSubsidy: true },
    ],
  },
  arpa_ira: {
    name: "ARPA/IRA (2021-2025)",
    description: "No income ceiling",
    rows: [
      { fpl: "100-150%", rate: "0-2.0%" },
      { fpl: "150-200%", rate: "2.0-4.0%" },
      { fpl: "200-250%", rate: "4.0-6.0%" },
      { fpl: "250-300%", rate: "6.0-8.5%" },
      { fpl: "300-400%", rate: "8.5%" },
      { fpl: ">400%", rate: "8.5%" },
    ],
  },
  post_ira: {
    name: "Post-IRA (2026+)",
    description: "Returns to original ACA",
    rows: [
      { fpl: "100-133%", rate: "2.0%" },
      { fpl: "133-150%", rate: "3.0-4.0%" },
      { fpl: "150-200%", rate: "4.0-6.3%" },
      { fpl: "200-250%", rate: "6.3-8.05%" },
      { fpl: "250-300%", rate: "8.05-9.5%" },
      { fpl: "300-400%", rate: "9.5%" },
      { fpl: ">400%", rate: "No subsidy", noSubsidy: true },
    ],
  },
  bill_700fpl: {
    name: "700% FPL Proposal",
    description: "Extended ceiling, higher top rate",
    rows: [
      { fpl: "100-150%", rate: "0-2.0%" },
      { fpl: "150-200%", rate: "2.0-4.0%" },
      { fpl: "200-250%", rate: "4.0-6.0%" },
      { fpl: "250-300%", rate: "6.0-8.5%" },
      { fpl: "300-400%", rate: "8.5-9.0%" },
      { fpl: "400-500%", rate: "9.0-9.25%" },
      { fpl: "500-700%", rate: "9.25%" },
      { fpl: ">700%", rate: "No subsidy", noSubsidy: true },
    ],
  },
};

function ContributionScheduleTable({ showSchedules = ["arpa_ira", "post_ira"] }) {
  const schedulesToShow = showSchedules.map(key => ({ key, ...SCHEDULES[key] }));

  return (
    <div className="contribution-schedule">
      <div className="schedule-header">
        <h3>Required Contribution (% of Income)</h3>
        <p>Maximum percentage of household income required to pay for the benchmark plan</p>
      </div>

      <div className="schedules-container">
        {schedulesToShow.map(schedule => (
          <div key={schedule.key} className={`schedule-column ${schedule.key}`}>
            <div className="schedule-title">{schedule.name}</div>
            <div className="schedule-description">{schedule.description}</div>
            <table>
              <thead>
                <tr>
                  <th>Income (FPL)</th>
                  <th>Contribution</th>
                </tr>
              </thead>
              <tbody>
                {schedule.rows.map((row, idx) => (
                  <tr key={idx} className={row.noSubsidy ? "no-subsidy" : ""}>
                    <td>{row.fpl}</td>
                    <td className={row.noSubsidy ? "no-subsidy-cell" : ""}>{row.rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ContributionScheduleTable;

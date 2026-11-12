"""
Precompute the national effects of reviving the enhanced premium tax credits in
2027 (H.R. 1834), and current law's credits in 2026 and 2027.

Runs policyengine-us over its default microdata (the certified Populace build)
for 2027, under current law and with the enhanced schedule, and writes
src/data/national_impacts.json. The figures follow policyengine.py's
definitions (income deciles, winners and losers, SPM poverty, inequality).

PolicyEngine's household net income leaves out health coverage, including
the premium tax credit (gov.simulation.include_health_benefits_in_net_income is
off), so on its own the reform wouldn't change it. Here each household's change
in the credit is added to its net income, as a cut in the premium it pays. SPM
resources already count the credit that way: they subtract medical
out-of-pocket spending, which includes the marketplace premium net of the
credit (marketplace_net_premium), so poverty is the model's own. The baseline
figures are the model's own too.

Needs about 32 GB of memory: run it on Modal, not a laptop. Rerun after every
policyengine-us pin.
"""

import gc
import json
from datetime import date
from importlib.metadata import version
from pathlib import Path

import numpy as np
from microdf import MicroSeries
from policyengine_us import Microsimulation
from policyengine_us.system import DEFAULT_DATASET, DEFAULT_DATASET_SHA256

from aca_calc.calculations.reforms import create_enhanced_ptc_reform

OUTPUT = Path(__file__).parent / "src" / "data" / "national_impacts.json"
YEAR = 2027
PRIOR_YEAR = 2026
# policyengine.py's winners-and-losers bands: relative change in net income.
BOUNDS = [-np.inf, -0.05, -1e-3, 1e-3, 0.05, np.inf]
CATEGORIES = [
    "lose_more_than_5pct",
    "lose_less_than_5pct",
    "no_change",
    "gain_less_than_5pct",
    "gain_more_than_5pct",
]
AGE_GROUPS = {
    "all": (0, np.inf),
    "child": (0, 17),
    "adult": (18, 64),
    "senior": (65, np.inf),
}
# Income as a fraction of the poverty guideline the credit uses; upper bounds
# are inclusive, so 400% FPL sits with current law's eligible incomes.
FPL_BANDS = [
    ("Up to 150%", -np.inf, 1.5),
    ("150% to 250%", 1.5, 2.5),
    ("250% to 400%", 2.5, 4.0),
    ("400% to 600%", 4.0, 6.0),
    ("Above 600%", 6.0, np.inf),
]


def values(sim, variable, year):
    return np.asarray(sim.calculate(variable, year).values)


def person_share(sim, tax_unit_values):
    """Each person's equal share of their tax unit's value, so sums over SPM
    units and households keep the total."""
    tax_unit = sim.populations["tax_unit"]
    return tax_unit.project(tax_unit_values / tax_unit.nb_persons())


def credits(sim, year):
    """Credits, recipients and benchmark premiums in one year."""
    ptc = values(sim, "assigned_aca_ptc", year)
    weight = values(sim, "tax_unit_weight", year)
    slcsp = values(sim, "slcsp", year)
    receiving = ptc > 0
    covered = values(sim, "is_aca_ptc_eligible", year) & sim.populations[
        "tax_unit"
    ].project(receiving)
    person_weight = values(sim, "person_weight", year)
    return {
        "ptc": ptc,
        "summary": {
            "total_ptc": float(np.sum(ptc * weight)),
            "tax_units_receiving": float(np.sum(weight[receiving])),
            "people_receiving": float(np.sum(person_weight[covered])),
            # Among tax units receiving a credit.
            "mean_benchmark_premium": float(
                np.average(slcsp[receiving], weights=weight[receiving])
            ),
            "mean_credit": float(np.average(ptc[receiving], weights=weight[receiving])),
            "mean_net_benchmark_premium": float(
                np.average((slcsp - ptc)[receiving], weights=weight[receiving])
            ),
        },
        "covered": covered,
    }


def gini(income, weight):
    """policyengine.py's weighted Gini (area under the Lorenz curve)."""
    order = np.argsort(income)
    income, weight = income[order], weight[order]
    lorenz = np.cumsum(income * weight) / np.sum(income * weight)
    fractions = weight / np.sum(weight)
    return float(1 - 2 * np.sum(fractions * (lorenz - fractions / 2)))


def inequality(income, weight):
    """Gini and income shares of household net income, household-weighted, as
    policyengine.py's standard US preset."""
    order = np.argsort(income)
    sorted_income, sorted_weight = income[order], weight[order]
    position = np.cumsum(sorted_weight) / np.sum(sorted_weight)
    total = np.sum(sorted_income * sorted_weight)

    def share(mask):
        return float(np.sum(sorted_income[mask] * sorted_weight[mask]) / total)

    return {
        "gini": gini(income, weight),
        "top_10_share": share(position > 0.9),
        "top_1_share": share(position > 0.99),
        "bottom_50_share": share(position <= 0.5),
    }


def deciles(baseline, reform, household_weight, people):
    """Average household net income by decile, and the share of people in each
    winners-and-losers band, as policyengine.py computes them: households
    ranked by baseline net income with weights times household size, negative
    incomes left out of the deciles."""
    effective_weight = household_weight * people
    rank = np.asarray(MicroSeries(baseline, weights=effective_weight).rank(pct=True))
    group = np.clip(np.ceil(rank * 10), 1, 10).astype(int)
    group[baseline < 0] = -1
    change = (reform - baseline) / np.maximum(baseline, 1.0)

    def bands(selected):
        weight = effective_weight[selected]
        return {
            name: float(
                np.sum(weight[(change[selected] > low) & (change[selected] <= high)])
                / np.sum(weight)
            )
            for name, low, high in zip(CATEGORIES, BOUNDS[:-1], BOUNDS[1:])
        }

    rows, winners = [], []
    for decile in range(1, 11):
        selected = group == decile
        weight = household_weight[selected]
        baseline_mean = float(np.average(baseline[selected], weights=weight))
        reform_mean = float(np.average(reform[selected], weights=weight))
        rows.append({
            "decile": decile,
            "baseline_mean": baseline_mean,
            "reform_mean": reform_mean,
            "absolute_change": reform_mean - baseline_mean,
            "relative_change": 100 * (reform_mean - baseline_mean) / baseline_mean,
        })
        winners.append({"decile": decile, **bands(selected)})
    overall = bands(np.ones(len(baseline), dtype=bool))
    return rows, {"all": overall, "deciles": winners}


def poverty(groups, person_weight, baseline_poor, reform_poor):
    """Person-weighted poverty rates and headcounts for each group."""
    result = {}
    for name, mask in groups.items():
        weight = person_weight[mask]
        population = float(np.sum(weight))
        result[name] = {
            "baseline_rate": float(np.sum(weight[baseline_poor[mask]]) / population),
            "reform_rate": float(np.sum(weight[reform_poor[mask]]) / population),
            "baseline_headcount": float(np.sum(weight[baseline_poor[mask]])),
            "reform_headcount": float(np.sum(weight[reform_poor[mask]])),
        }
    return result


def main():
    print(f"Running policyengine-us {version('policyengine-us')} over {DEFAULT_DATASET}")

    # Current law: everything the comparison needs, then free the simulation.
    # Net income first in each simulation, since some results depend on the
    # order variables are calculated in (policyengine-us #9740).
    baseline = Microsimulation(dataset_end_year=YEAR)
    net_income = values(baseline, "household_net_income", YEAR)
    current = credits(baseline, YEAR)
    print(f"  current law {YEAR}: {current['summary']}")
    household_weight = values(baseline, "household_weight", YEAR)
    people = values(baseline, "household_count_people", YEAR)
    resources = values(baseline, "spm_unit_net_income", YEAR)
    threshold = values(baseline, "spm_unit_spm_threshold", YEAR)
    model_poor = values(baseline, "spm_unit_is_in_spm_poverty", YEAR)
    spm_unit_weight = values(baseline, "spm_unit_weight", YEAR)
    tax_unit_weight = values(baseline, "tax_unit_weight", YEAR)
    fpl_fraction = values(baseline, "aca_magi_fraction", YEAR)
    person_weight = values(baseline, "person_weight", YEAR)
    age = values(baseline, "age", YEAR)
    is_male = values(baseline, "is_male", YEAR)
    race = values(baseline, "race", YEAR).astype(str)
    person_spm_unit = baseline.populations["spm_unit"].members_entity_id
    prior = credits(baseline, PRIOR_YEAR)
    print(f"  current law {PRIOR_YEAR}: {prior['summary']}")
    del baseline
    gc.collect()

    reform = Microsimulation(reform=create_enhanced_ptc_reform(), dataset_end_year=YEAR)
    # Anything else the reform changes in net income (expected none: the
    # credit doesn't enter it).
    other_income_change = values(reform, "household_net_income", YEAR) - net_income
    # SPM resources count the credit through lower marketplace premiums.
    reform_resources = values(reform, "spm_unit_net_income", YEAR)
    revived = credits(reform, YEAR)
    print(f"  enhanced {YEAR}: {revived['summary']}")
    change = revived["ptc"] - current["ptc"]
    share = person_share(reform, change)
    household_change = reform.populations["household"].sum(share)
    del reform
    gc.collect()

    reform_net_income = net_income + other_income_change + household_change
    measured = np.isfinite(resources) & np.isfinite(threshold)
    assert np.array_equal(
        (resources < threshold)[measured], model_poor[measured]
    ), "SPM poverty doesn't match the model's"

    decile_rows, winners = deciles(net_income, reform_net_income, household_weight, people)

    person_measured = measured[person_spm_unit]
    groups = {
        name: (age >= low) & (age <= high) & person_measured
        for name, (low, high) in AGE_GROUPS.items()
    }
    groups.update({
        "male": is_male & person_measured,
        "female": ~is_male & person_measured,
        **{
            value.lower(): (race == value) & person_measured
            for value in ("WHITE", "BLACK", "HISPANIC", "OTHER")
        },
    })

    def poor(spm_resources, scale):
        return (spm_resources < scale * threshold)[person_spm_unit]

    poverty_rates = {
        "spm": poverty(groups, person_weight, poor(resources, 1), poor(reform_resources, 1)),
        "deep": poverty(
            groups, person_weight, poor(resources, 0.5), poor(reform_resources, 0.5)
        ),
    }

    by_fpl = []
    for label, low, high in FPL_BANDS:
        band = (fpl_fraction > low) & (fpl_fraction <= high)
        weight = tax_unit_weight[band]
        by_fpl.append({
            "band": label,
            "baseline_ptc": float(np.sum(current["ptc"][band] * weight)),
            "reform_ptc": float(np.sum(revived["ptc"][band] * weight)),
            "tax_units_baseline": float(np.sum(weight[current["ptc"][band] > 0])),
            "tax_units_reform": float(np.sum(weight[revived["ptc"][band] > 0])),
        })

    gaining = household_change > 0
    data = {
        "model_version": version("policyengine-us"),
        "dataset": DEFAULT_DATASET,
        "dataset_sha256": DEFAULT_DATASET_SHA256,
        "computed": date.today().isoformat(),
        "year": YEAR,
        "current_law": {
            str(PRIOR_YEAR): prior["summary"],
            str(YEAR): current["summary"],
        },
        "enhanced": revived["summary"],
        "budget": {
            # Positive: the federal government spends more.
            "federal_cost": float(np.sum(change * tax_unit_weight)),
        },
        "recipients": {
            "people_newly_receiving": float(
                np.sum(person_weight[revived["covered"] & ~current["covered"]])
            ),
        },
        "households": {
            "gaining": float(np.sum(household_weight[gaining])),
            "people_gaining": float(np.sum((household_weight * people)[gaining])),
            "total": float(np.sum(household_weight)),
            "people": float(np.sum(household_weight * people)),
            "mean_gain_among_gaining": float(
                np.average(household_change[gaining], weights=household_weight[gaining])
            ),
        },
        "by_fpl": by_fpl,
        "deciles": decile_rows,
        "winners_losers": winners,
        "poverty": poverty_rates,
        "inequality": {
            "baseline": inequality(net_income, household_weight),
            "reform": inequality(reform_net_income, household_weight),
        },
        "checks": {
            "max_other_net_income_change": float(np.max(np.abs(other_income_change))),
            # Against the federal cost: how much of the added credit reaches
            # SPM resources through lower premiums.
            "spm_resource_change": float(
                np.nansum((reform_resources - resources) * spm_unit_weight)
            ),
            "spm_units_not_measured": int(np.sum(~measured)),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"Saved {OUTPUT}")
    print(json.dumps({key: data[key] for key in ("budget", "recipients", "households", "checks")}, indent=1))


if __name__ == "__main__":
    main()

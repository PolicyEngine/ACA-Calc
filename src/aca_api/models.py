"""Pydantic models for ACA Calculator API."""

from pydantic import BaseModel, Field, field_validator, model_validator

# Coverage years the calculator models. Requests without a year get 2026, so
# a page that predates the year setting keeps its answers.
YEARS = (2026, 2027)
DEFAULT_YEAR = 2026


def check_year(year: int) -> int:
    if year not in YEARS:
        raise ValueError(f"year must be one of {', '.join(map(str, YEARS))}")
    return year


class CalculateRequest(BaseModel):
    """Request model for PTC calculation."""

    age_head: int = Field(ge=18, le=100, description="Age of head of household")
    age_spouse: int | None = Field(
        default=None, ge=18, le=100, description="Age of spouse (if married)"
    )
    dependent_ages: list[int] = Field(
        default_factory=list, description="Ages of dependents"
    )
    state: str = Field(description="Two-letter state code (e.g., 'PA')")
    county: str = Field(description="County name (e.g., 'Lebanon County')")
    zip_code: str | None = Field(
        default=None, description="ZIP code (required for LA County)"
    )
    year: int = Field(default=DEFAULT_YEAR, description="Coverage year (2026 or 2027)")
    show_ira: bool = Field(
        default=True,
        description="Calculate H.R. 1834, the enhanced credits extended (the IRA extension)",
    )
    show_700fpl: bool = Field(
        default=False,
        description="Calculate the Bipartisan Health Insurance Affordability Act (700% FPL bill)",
    )
    show_additional_bracket: bool = Field(
        default=False, description="Calculate additional bracket reform scenario"
    )
    show_simplified_bracket: bool = Field(
        default=False, description="Calculate simplified bracket reform scenario"
    )
    show_prior_year: bool = Field(
        default=False,
        description=(
            "Also calculate current law for the year before the coverage year, for "
            "the same household and incomes (2027 requests only)"
        ),
    )
    skip_cache: bool = Field(
        default=False,
        description="Compute a new answer without reading or writing the cache",
    )

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        return check_year(v)

    @model_validator(mode="after")
    def validate_prior_year(self):
        if self.show_prior_year and self.year - 1 not in YEARS:
            raise ValueError(
                f"show_prior_year needs a coverage year after {YEARS[0]}; "
                f"the calculator doesn't model {self.year - 1}"
            )
        return self

    @field_validator("dependent_ages")
    @classmethod
    def validate_dependent_ages(cls, v):
        """Validate dependent ages."""
        if len(v) > 10:
            raise ValueError("Maximum 10 dependents supported")
        for age in v:
            if age < 0 or age > 25:
                raise ValueError("Dependent ages must be between 0 and 25")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        """Validate state code."""
        valid_states = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
        ]
        if v not in valid_states:
            raise ValueError(f"Invalid state code: {v}")
        return v


class CalculateResponse(BaseModel):
    """Response model for PTC calculation."""

    income: list[float] = Field(description="Income values (1,001 points)")
    ptc_baseline: list[float] = Field(description="PTC under current law for the year")
    ptc_ira: list[float] = Field(description="PTC under H.R. 1834 (the IRA extension)")
    ptc_700fpl: list[float] = Field(description="PTC under 700% FPL bill")
    ptc_additional_bracket: list[float] = Field(
        default_factory=list, description="PTC under additional bracket reform"
    )
    ptc_simplified_bracket: list[float] = Field(
        default_factory=list, description="PTC under simplified bracket reform"
    )
    year: int = Field(default=DEFAULT_YEAR, description="Coverage year")
    fpl: float = Field(
        description=(
            "Poverty guideline for the household's size that the credit uses: "
            "the one for the year before the coverage year"
        )
    )
    fpl_year: int | None = Field(default=None, description="The guideline's year")
    model_version: str = Field(default="", description="policyengine-us version")
    slcsp: float = Field(description="Second-lowest cost silver plan (annual)")
    slcsp_by_income: list[float] = Field(
        default_factory=list,
        description=(
            "Annual benchmark premium for the members eligible for the credit at "
            "each income, zero where none is"
        ),
    )
    medicaid: list[float] = Field(description="Medicaid value by income")
    chip: list[float] = Field(description="CHIP value by income")
    # With show_prior_year: current law a year before the coverage year.
    ptc_prior_year: list[float] | None = Field(
        default=None, description="PTC under current law for the year before"
    )
    slcsp_by_income_prior_year: list[float] | None = Field(
        default=None, description="slcsp_by_income for the year before"
    )
    fpl_prior_year: float | None = Field(
        default=None, description="The guideline the year before's credit uses"
    )


class ScrollySection(BaseModel):
    """A single section in the scrollytelling narrative."""

    id: str = Field(description="Unique section identifier")
    title: str = Field(description="Section title")
    content: str = Field(description="Markdown content for section")
    chartState: str = Field(
        description=(
            "Chart state: all_programs, medicaid_focus, chip_focus, cliff_focus, "
            "ira_impact, fpl700_focus, additional_focus, simplified_focus or "
            "both_reforms"
        )
    )


class ExplainRequest(BaseModel):
    """Request model for AI explanation generation."""

    # Household info
    age_head: int = Field(description="Age of head of household")
    age_spouse: int | None = Field(default=None, description="Age of spouse")
    dependent_ages: list[int] = Field(default_factory=list, description="Ages of dependents")
    state: str = Field(description="Two-letter state code")
    county: str = Field(description="County name")
    year: int = Field(default=DEFAULT_YEAR, description="Coverage year (2026 or 2027)")
    is_expansion_state: bool = Field(description="Whether state expanded Medicaid")

    # Calculated values
    fpl: float = Field(description="Federal Poverty Level for household")
    slcsp: float = Field(description="Annual SLCSP cost")
    fpl_400_income: float = Field(description="Income at 400% FPL")
    fpl_700_income: float = Field(description="Income at 700% FPL")

    # Program eligibility thresholds (% of FPL)
    medicaid_adult_threshold_pct: int = Field(description="Medicaid eligibility for adults (% FPL)")
    medicaid_child_threshold_pct: int = Field(description="Medicaid eligibility for children (% FPL)")
    chip_threshold_pct: int = Field(default=0, description="CHIP eligibility (% FPL), 0 if no children")

    # Which reforms are selected
    show_ira: bool = Field(default=True, description="Whether IRA extension is selected")
    show_700fpl: bool = Field(default=True, description="Whether 700% FPL bill is selected")
    show_additional_bracket: bool = Field(default=False, description="Whether additional bracket is selected")
    show_simplified_bracket: bool = Field(default=False, description="Whether simplified bracket is selected")
    show_prior_year: bool = Field(default=False, description="Whether to compare with current law a year earlier")

    # Key data points for narrative
    sample_income: float = Field(description="Sample income to analyze")
    ptc_baseline_at_sample: float = Field(description="Baseline PTC at sample income")
    ptc_ira_at_sample: float = Field(default=0, description="IRA PTC at sample income")
    ptc_700fpl_at_sample: float = Field(default=0, description="700% FPL PTC at sample income")
    ptc_additional_bracket_at_sample: float = Field(default=0, description="Additional bracket PTC at sample income")
    ptc_simplified_bracket_at_sample: float = Field(default=0, description="Simplified bracket PTC at sample income")
    slcsp_prior_year: float = Field(default=0, description="Annual SLCSP cost a year earlier")
    ptc_prior_year_at_sample: float = Field(default=0, description="Current-law PTC a year earlier at sample income")

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        return check_year(v)


class ExplainResponse(BaseModel):
    """Response model for AI explanation."""

    sections: list[ScrollySection] = Field(description="Scrollytelling sections")
    household_description: str = Field(description="Short household description")

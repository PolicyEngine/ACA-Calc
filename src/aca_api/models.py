"""Pydantic models for ACA Calculator API."""

from pydantic import BaseModel, Field, field_validator


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
    show_ira: bool = Field(default=True, description="Calculate IRA extension scenario")
    show_700fpl: bool = Field(
        default=False, description="Calculate 700% FPL bill scenario"
    )

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

    income: list[float] = Field(description="Income values (10,001 points)")
    ptc_baseline: list[float] = Field(description="PTC under baseline (2026 law)")
    ptc_ira: list[float] = Field(description="PTC under IRA extension")
    ptc_700fpl: list[float] = Field(description="PTC under 700% FPL bill")
    fpl: float = Field(description="Federal Poverty Level for household size")
    slcsp: float = Field(description="Second-lowest cost silver plan (annual)")
    medicaid: list[float] = Field(description="Medicaid value by income")
    chip: list[float] = Field(description="CHIP value by income")


class ScrollySection(BaseModel):
    """A single section in the scrollytelling narrative."""

    id: str = Field(description="Unique section identifier")
    title: str = Field(description="Section title")
    content: str = Field(description="Markdown content for section")
    chartState: str = Field(description="Chart state: all_programs, medicaid_focus, chip_focus, cliff_focus, ira_impact, both_reforms")


class ExplainRequest(BaseModel):
    """Request model for AI explanation generation."""

    # Household info
    age_head: int = Field(description="Age of head of household")
    age_spouse: int | None = Field(default=None, description="Age of spouse")
    dependent_ages: list[int] = Field(default_factory=list, description="Ages of dependents")
    state: str = Field(description="Two-letter state code")
    county: str = Field(description="County name")
    is_expansion_state: bool = Field(description="Whether state expanded Medicaid")

    # Calculated values
    fpl: float = Field(description="Federal Poverty Level for household")
    slcsp: float = Field(description="Annual SLCSP cost")
    fpl_400_income: float = Field(description="Income at 400% FPL")
    fpl_700_income: float = Field(description="Income at 700% FPL")

    # Key data points for narrative
    sample_income: float = Field(description="Sample income to analyze")
    ptc_baseline_at_sample: float = Field(description="Baseline PTC at sample income")
    ptc_ira_at_sample: float = Field(description="IRA PTC at sample income")
    ptc_700fpl_at_sample: float = Field(description="700% FPL PTC at sample income")


class ExplainResponse(BaseModel):
    """Response model for AI explanation."""

    sections: list[ScrollySection] = Field(description="Scrollytelling sections")
    household_description: str = Field(description="Short household description")

"""
Time Generator Service for THAMES Hydration Simulations.

Provides utilities for:
- Unit conversions between minutes, hours, days
- Generating time sequences (linear, exponential)
- Merging model-generated times with user-specified exact times
- Smart formatting for display (auto-selecting appropriate units)

All internal calculations use days as the base unit for compatibility
with simparams.json.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
import logging


class TimeUnit(Enum):
    """Time units supported by the service."""
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "hr"
    DAYS = "d"
    MONTHS = "mo"
    YEARS = "yr"


class ExponentialBase(Enum):
    """Base options for exponential time generation."""
    E = "e"
    TEN = "10"


@dataclass
class TimeGenerationResult:
    """Result of time generation including metadata."""
    times_days: List[float]  # All times in days
    model_times_days: List[float]  # Times from model only
    exact_times_days: List[float]  # User-specified exact times
    exact_time_indices: List[int]  # Indices of exact times in merged list
    warnings: List[str]  # Any warnings generated
    error: Optional[str] = None  # Error message if generation failed


# Conversion factors TO days
UNIT_TO_DAYS = {
    TimeUnit.MILLISECONDS: 1.0 / (24 * 60 * 60 * 1000),
    TimeUnit.SECONDS: 1.0 / (24 * 60 * 60),
    TimeUnit.MINUTES: 1.0 / (24 * 60),
    TimeUnit.HOURS: 1.0 / 24,
    TimeUnit.DAYS: 1.0,
    TimeUnit.MONTHS: 30.0,  # Approximate
    TimeUnit.YEARS: 365.0,  # Approximate
}

# Conversion factors FROM days
DAYS_TO_UNIT = {unit: 1.0 / factor for unit, factor in UNIT_TO_DAYS.items()}


class TimeGeneratorService:
    """
    Service for generating and formatting simulation output times.

    Supports multiple time generation models:
    - Custom: User-specified comma-separated list
    - Linear: Evenly-spaced intervals (by count or by spacing)
    - Exponential: t = t0 * base^(a * i)

    All methods return times in days for simparams.json compatibility.
    """

    def __init__(self):
        self.logger = logging.getLogger('THAMES.TimeGeneratorService')

        # Deduplication tolerance (times within this fraction are considered equal)
        self.dedup_tolerance = 0.001  # 0.1%

        # Limits
        self.max_outputs_warning = 100
        self.max_outputs_error = 200
        self.max_linear_by_spacing = 100
        self.max_exponential_steps = 100
        self.max_strength_a = 1.0

    # =========================================================================
    # Unit Conversion
    # =========================================================================

    def convert_to_days(self, value: float, from_unit: TimeUnit) -> float:
        """
        Convert a time value to days.

        Args:
            value: Time value in the source unit
            from_unit: Source time unit

        Returns:
            Time value in days
        """
        return value * UNIT_TO_DAYS[from_unit]

    def convert_from_days(self, value_days: float, to_unit: TimeUnit) -> float:
        """
        Convert a time value from days to another unit.

        Args:
            value_days: Time value in days
            to_unit: Target time unit

        Returns:
            Time value in the target unit
        """
        return value_days * DAYS_TO_UNIT[to_unit]

    def convert_between_units(
        self,
        value: float,
        from_unit: TimeUnit,
        to_unit: TimeUnit
    ) -> float:
        """
        Convert a time value between any two units.

        Args:
            value: Time value in the source unit
            from_unit: Source time unit
            to_unit: Target time unit

        Returns:
            Time value in the target unit
        """
        days = self.convert_to_days(value, from_unit)
        return self.convert_from_days(days, to_unit)

    # =========================================================================
    # Smart Time Formatting
    # =========================================================================

    def format_time_smart(self, time_days: float) -> Tuple[float, str]:
        """
        Format a time value using the most appropriate unit.

        Rules:
        - t < 0.01 s (0.01/86400 days) → milliseconds
        - t < 60 s → seconds
        - t < 60 min → minutes
        - t < 24 hr → hours
        - t < 30 d → days
        - t < 365 d → months
        - else → years

        Args:
            time_days: Time value in days

        Returns:
            Tuple of (formatted_value, unit_string)
        """
        # Convert to seconds for easier threshold checking
        time_seconds = time_days * 24 * 60 * 60

        if time_seconds < 0.01:
            # Milliseconds
            value = time_seconds * 1000
            return (value, "ms")
        elif time_seconds < 60:
            # Seconds
            return (time_seconds, "s")
        elif time_seconds < 60 * 60:
            # Minutes
            value = time_seconds / 60
            return (value, "min")
        elif time_seconds < 24 * 60 * 60:
            # Hours
            value = time_seconds / (60 * 60)
            return (value, "hr")
        elif time_days < 30:
            # Days
            return (time_days, "d")
        elif time_days < 365:
            # Months (approximate)
            value = time_days / 30
            return (value, "mo")
        else:
            # Years
            value = time_days / 365
            return (value, "yr")

    def format_time_string(self, time_days: float, precision: int = 2) -> str:
        """
        Format a time value as a string with smart unit selection.

        Args:
            time_days: Time value in days
            precision: Number of decimal places

        Returns:
            Formatted string like "1.5 hr" or "28 d"
        """
        value, unit = self.format_time_smart(time_days)

        # Use integer format if value is close to an integer
        if abs(value - round(value)) < 0.01:
            return f"{int(round(value))} {unit}"
        else:
            return f"{value:.{precision}g} {unit}"

    def format_times_for_preview(
        self,
        times_days: List[float],
        exact_indices: Optional[List[int]] = None,
        max_display: int = 20
    ) -> str:
        """
        Format a list of times for preview display.

        Args:
            times_days: List of times in days
            exact_indices: Indices of user-specified exact times (will be marked)
            max_display: Maximum number of times to show before truncating

        Returns:
            Formatted preview string
        """
        if not times_days:
            return "(no output times)"

        exact_set = set(exact_indices or [])
        formatted_parts = []

        for i, t in enumerate(times_days):
            time_str = self.format_time_string(t)
            if i in exact_set:
                time_str = f"*{time_str}*"
            formatted_parts.append(time_str)

            if i >= max_display - 1 and len(times_days) > max_display:
                remaining = len(times_days) - max_display
                formatted_parts.append(f"... (+{remaining} more)")
                break

        return ", ".join(formatted_parts)

    # =========================================================================
    # Linear Time Generation
    # =========================================================================

    def generate_linear_by_count(
        self,
        final_time_days: float,
        num_outputs: int
    ) -> List[float]:
        """
        Generate evenly-spaced times from 0 to final_time.

        Args:
            final_time_days: Final simulation time in days
            num_outputs: Number of output times (including 0 and final_time)

        Returns:
            List of times in days
        """
        if num_outputs < 2:
            return [0.0, final_time_days]

        times = []
        for i in range(num_outputs):
            t = (i / (num_outputs - 1)) * final_time_days
            times.append(t)

        return times

    def generate_linear_by_spacing(
        self,
        spacing_days: float,
        final_time_days: float,
        max_points: Optional[int] = None
    ) -> List[float]:
        """
        Generate times with fixed spacing from 0 to final_time.

        Args:
            spacing_days: Time between outputs in days
            final_time_days: Final simulation time in days
            max_points: Maximum number of points (default: self.max_linear_by_spacing)

        Returns:
            List of times in days
        """
        if max_points is None:
            max_points = self.max_linear_by_spacing

        if spacing_days <= 0:
            return [0.0, final_time_days]

        times = [0.0]
        t = spacing_days

        while t <= final_time_days and len(times) < max_points:
            times.append(t)
            t += spacing_days

        # Ensure final time is included if not already
        if times[-1] < final_time_days:
            times.append(final_time_days)

        return times

    # =========================================================================
    # Exponential Time Generation
    # =========================================================================

    def generate_exponential(
        self,
        t0_days: float,
        strength_a: float,
        num_steps: int,
        base: ExponentialBase = ExponentialBase.E,
        final_time_days: Optional[float] = None
    ) -> List[float]:
        """
        Generate exponentially-spaced times: t = t0 * base^(a * i)

        Args:
            t0_days: Starting time in days (must be > 0)
            strength_a: Strength parameter (0 < a <= 1.0)
            num_steps: Number of time steps (starting from i=0)
            base: Exponential base (e or 10)
            final_time_days: Optional final time for truncation

        Returns:
            List of times in days
        """
        if t0_days <= 0:
            t0_days = 1e-6  # Very small positive value

        strength_a = min(strength_a, self.max_strength_a)
        num_steps = min(num_steps, self.max_exponential_steps)

        times = []
        base_value = math.e if base == ExponentialBase.E else 10.0

        for i in range(num_steps):
            t = t0_days * (base_value ** (strength_a * i))

            # Stop if we've exceeded final time
            if final_time_days is not None and t > final_time_days:
                break

            times.append(t)

        return times

    # =========================================================================
    # Merge and Deduplication
    # =========================================================================

    def merge_times(
        self,
        model_times: List[float],
        exact_times: List[float],
        final_time_days: float
    ) -> Tuple[List[float], List[int]]:
        """
        Merge model-generated times with user-specified exact times.

        Performs:
        1. Combines both lists
        2. Sorts in ascending order
        3. Removes duplicates (within tolerance)
        4. Truncates to final_time
        5. Tracks which indices are from exact_times

        Args:
            model_times: Times generated by the selected model
            exact_times: User-specified exact times
            final_time_days: Final simulation time for truncation

        Returns:
            Tuple of (merged_times, exact_time_indices)
        """
        # Tag each time with its source
        tagged = [(t, 'model') for t in model_times]
        tagged += [(t, 'exact') for t in exact_times]

        # Sort by time
        tagged.sort(key=lambda x: x[0])

        # Truncate to final time
        tagged = [(t, src) for t, src in tagged if t <= final_time_days]

        # Deduplicate, preferring exact times when there's a collision
        merged = []
        exact_indices = []

        for t, source in tagged:
            if not merged:
                merged.append(t)
                if source == 'exact':
                    exact_indices.append(0)
            else:
                last_t = merged[-1]
                # Check if this is a duplicate (within tolerance)
                if last_t > 0:
                    relative_diff = abs(t - last_t) / last_t
                else:
                    relative_diff = abs(t - last_t)

                if relative_diff > self.dedup_tolerance:
                    # Not a duplicate, add it
                    merged.append(t)
                    if source == 'exact':
                        exact_indices.append(len(merged) - 1)
                elif source == 'exact':
                    # Duplicate but this is an exact time - replace and mark
                    merged[-1] = t
                    if (len(merged) - 1) not in exact_indices:
                        exact_indices.append(len(merged) - 1)

        return merged, exact_indices

    # =========================================================================
    # Parse Custom Times
    # =========================================================================

    def parse_custom_times(
        self,
        text: str,
        unit: TimeUnit
    ) -> Tuple[List[float], Optional[str]]:
        """
        Parse a comma-separated list of times.

        Args:
            text: Comma-separated time values
            unit: Unit of the input values

        Returns:
            Tuple of (times_in_days, error_message_or_none)
        """
        if not text.strip():
            return [], None

        times = []
        try:
            for part in text.split(","):
                part = part.strip()
                if part:
                    value = float(part)
                    days = self.convert_to_days(value, unit)
                    times.append(days)
        except ValueError as e:
            return [], f"Invalid time value: {e}"

        return sorted(times), None

    # =========================================================================
    # Complete Generation with Validation
    # =========================================================================

    def generate_output_times(
        self,
        model: str,
        final_time_days: float,
        exact_times_days: Optional[List[float]] = None,
        # Linear by count params
        linear_count: Optional[int] = None,
        # Linear by spacing params
        linear_spacing_days: Optional[float] = None,
        # Exponential params
        exp_t0_days: Optional[float] = None,
        exp_strength: Optional[float] = None,
        exp_base: ExponentialBase = ExponentialBase.E,
        exp_num_steps: Optional[int] = None,
        # Custom params
        custom_times_days: Optional[List[float]] = None
    ) -> TimeGenerationResult:
        """
        Generate output times using the specified model and parameters.

        Args:
            model: One of "custom", "linear_count", "linear_spacing", "exponential"
            final_time_days: Final simulation time in days
            exact_times_days: Optional additional exact times to merge
            ... model-specific parameters ...

        Returns:
            TimeGenerationResult with times, metadata, and any warnings/errors
        """
        warnings = []
        model_times = []

        try:
            if model == "custom":
                model_times = custom_times_days or []

            elif model == "linear_count":
                if linear_count is None:
                    return TimeGenerationResult(
                        times_days=[], model_times_days=[], exact_times_days=[],
                        exact_time_indices=[], warnings=[],
                        error="Number of outputs not specified"
                    )
                model_times = self.generate_linear_by_count(
                    final_time_days, linear_count
                )

            elif model == "linear_spacing":
                if linear_spacing_days is None:
                    return TimeGenerationResult(
                        times_days=[], model_times_days=[], exact_times_days=[],
                        exact_time_indices=[], warnings=[],
                        error="Time spacing not specified"
                    )
                model_times = self.generate_linear_by_spacing(
                    linear_spacing_days, final_time_days
                )

            elif model == "exponential":
                if any(p is None for p in [exp_t0_days, exp_strength, exp_num_steps]):
                    return TimeGenerationResult(
                        times_days=[], model_times_days=[], exact_times_days=[],
                        exact_time_indices=[], warnings=[],
                        error="Exponential parameters incomplete"
                    )
                model_times = self.generate_exponential(
                    exp_t0_days, exp_strength, exp_num_steps,
                    exp_base, final_time_days
                )
            else:
                return TimeGenerationResult(
                    times_days=[], model_times_days=[], exact_times_days=[],
                    exact_time_indices=[], warnings=[],
                    error=f"Unknown model: {model}"
                )

            # Merge with exact times
            exact_times = exact_times_days or []
            merged_times, exact_indices = self.merge_times(
                model_times, exact_times, final_time_days
            )

            # Validation warnings
            count = len(merged_times)
            if count > self.max_outputs_error:
                return TimeGenerationResult(
                    times_days=merged_times,
                    model_times_days=model_times,
                    exact_times_days=exact_times,
                    exact_time_indices=exact_indices,
                    warnings=[],
                    error=f"Too many output times ({count}). Maximum is {self.max_outputs_error}."
                )
            elif count > self.max_outputs_warning:
                warnings.append(
                    f"Large number of output times ({count}). "
                    f"Consider reducing to improve performance."
                )

            return TimeGenerationResult(
                times_days=merged_times,
                model_times_days=model_times,
                exact_times_days=exact_times,
                exact_time_indices=exact_indices,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"Time generation error: {e}")
            return TimeGenerationResult(
                times_days=[], model_times_days=[], exact_times_days=[],
                exact_time_indices=[], warnings=[],
                error=str(e)
            )


# Module-level singleton
_time_generator_service: Optional[TimeGeneratorService] = None


def get_time_generator_service() -> TimeGeneratorService:
    """Get the singleton TimeGeneratorService instance."""
    global _time_generator_service
    if _time_generator_service is None:
        _time_generator_service = TimeGeneratorService()
    return _time_generator_service

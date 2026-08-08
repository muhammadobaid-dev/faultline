"""Per-account, per-model request accounting against Gemini's free daily caps.

Gemini's free tier is metered per project, and our two keys sit on separate Google
accounts, so each one is a genuinely independent allowance rather than two straws in
the same cup. Caps are also per model, which is why a run can be dead on
`gemini-3.6-flash` while Flash-Lite's allowance sits untouched.

The daily counter resets at midnight Pacific - a hard boundary, not a rolling window -
so a tapped account has a known recovery time rather than an unknown one.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("faultline.budget")

try:  # zoneinfo needs tzdata on some Windows installs
    from zoneinfo import ZoneInfo

    _PACIFIC = ZoneInfo("America/Los_Angeles")
except Exception:  # pragma: no cover - exercised only where tzdata is absent
    # Fixed PST. During PDT this rolls the day over an hour late, which errs
    # toward under-spending rather than over-spending.
    _PACIFIC = timezone(timedelta(hours=-8))


def pacific_day(now: datetime | None = None) -> str:
    """The reset bucket a request counts against."""
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(_PACIFIC).strftime("%Y-%m-%d")


def seconds_until_reset(now: datetime | None = None) -> int:
    moment = (now or datetime.now(timezone.utc)).astimezone(_PACIFIC)
    tomorrow = (moment + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - moment).total_seconds())


@dataclass(frozen=True)
class ModelLimits:
    """Free-tier ceilings for one model. `requests_per_day` is the real wall."""

    requests_per_minute: int
    requests_per_day: int


@dataclass
class DailyBudget:
    """Counts requests per (account, model) per Pacific day, persisted to disk.

    Persisted because a run can outlive a process - the Render service spins down
    when idle - and an in-memory counter would reset the ledger every cold start,
    which is exactly when we would most like to know what we have already spent.
    """

    path: Path
    limits: dict[str, ModelLimits]
    _counts: dict[str, int] = field(default_factory=dict)
    _day: str = ""

    def __post_init__(self) -> None:
        self._load()

    # -- accounting -------------------------------------------------------

    @staticmethod
    def key(account: str, model: str) -> str:
        return f"{account}|{model}"

    def spent(self, account: str, model: str) -> int:
        self._roll_over()
        return self._counts.get(self.key(account, model), 0)

    def remaining(self, account: str, model: str) -> int:
        limit = self.limits.get(model)
        if limit is None:
            return 1_000_000  # unmetered provider; cost is the only limit
        return max(0, limit.requests_per_day - self.spent(account, model))

    def has_room(self, account: str, model: str) -> bool:
        return self.remaining(account, model) > 0

    def record(self, account: str, model: str, count: int = 1) -> None:
        self._roll_over()
        k = self.key(account, model)
        self._counts[k] = self._counts.get(k, 0) + count
        self._save()

    def exhaust(self, account: str, model: str) -> None:
        """Mark a pairing as spent for the rest of the day.

        Called when the provider itself reports a per-day quota error, which is
        authoritative in a way our own counter is not: the published cap and the
        enforced cap have already disagreed once, on `gemini-3.6-flash`.
        """
        limit = self.limits.get(model)
        if limit is None:
            return
        self._roll_over()
        self._counts[self.key(account, model)] = limit.requests_per_day
        log.warning(
            "%s on %s is exhausted for the day; resets in %ds",
            model, account, seconds_until_reset(),
        )
        self._save()

    # -- persistence ------------------------------------------------------

    def _roll_over(self) -> None:
        today = pacific_day()
        if self._day != today:
            self._day = today
            self._counts = {}

    def _load(self) -> None:
        self._day = pacific_day()
        if not self.path.exists():
            return
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if stored.get("day") == self._day:
            self._counts = dict(stored.get("counts", {}))

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"day": self._day, "counts": self._counts}, indent=2),
                encoding="utf-8",
            )
        except OSError:  # a ledger we cannot persist is still better than a crash
            log.warning("could not persist the budget ledger to %s", self.path)

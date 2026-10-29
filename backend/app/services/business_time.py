"""Central Time reporting boundaries expressed as naive UTC for stored timestamps."""
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
BUSINESS_ZONE = ZoneInfo('America/Chicago')


def reporting_periods(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    day = now.astimezone(BUSINESS_ZONE).date()
    month = day.replace(day=1)
    next_month = month.replace(year=month.year + 1, month=1) if month.month == 12 else month.replace(month=month.month + 1)
    def utc(date):
        return datetime.combine(date, time.min, BUSINESS_ZONE).astimezone(timezone.utc).replace(tzinfo=None)
    return {'day_start': utc(day), 'day_end': utc(day + timedelta(days=1)),
            'month_start': utc(month), 'month_end': utc(next_month), 'local_day': day.isoformat()}

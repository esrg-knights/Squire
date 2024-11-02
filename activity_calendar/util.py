import icalendar
import datetime
import zoneinfo._zoneinfo

from django.utils.timezone import localtime, get_current_timezone

utc = datetime.timezone.utc


def set_time_for_RDATE_EXDATE(dates: list[datetime.datetime], time: datetime):
    """
    Sets the time (with the corresponding timezone) for a given set of dates.

    :param dates: Collection of datetime objects of which the time should be set
    :param time: A datetime object whose date and timezone are set to the collection of dates
    """
    set_time_fn = lambda date: datetime.datetime.combine(
        localtime(date), localtime(time).time(), tzinfo=get_current_timezone()
    )
    return map(set_time_fn, dates)


class ICalTimezoneFactory:
    """
    Aids in generating VTIMEZONE components.
    NOTE: This only generates a STANDARD and DAYLIGHT component for the most recent
    changes to DST-rules. This works for `Europe/Amsterdam`, but not for `America/New York`
    which has had its rules changed multiple times since the 1970s
    """

    WEEKDAYS = ("SU", "MO", "TU", "WE", "TH", "FR", "SA")
    _zones: list[str, icalendar.Timezone] = {}

    def generate_vtimezone(self, timezone_name: str):
        """
        Generates a VTIMEZONE component, based on the given `timezone_name`.
        If this component was already generated earlier for this timezone, it is
        retrieved from a cache.
        """
        if not timezone_name or "utc" in timezone_name.lower():  # UTC doesn't need a timezone definition
            return None

        if timezone_name in self._zones:
            return self._zones[timezone_name]

        # timezone_name = "America/Tijuana"  # GMT-6/7
        # timezone_name = "America/Godthab" # GMT-1/2
        # timezone_name = "America/Guayaquil"  # GMT -5/5
        z = zoneinfo._zoneinfo.ZoneInfo(timezone_name)

        transition_info = z._tz_after
        transitions: list[icalendar.TimezoneStandard | icalendar.TimezoneDaylight] = []
        if isinstance(transition_info, zoneinfo._zoneinfo._ttinfo):
            # No DST
            transitions.append(self._vtimezone_without_dst(transition_info))
        else:
            # DST
            transitions += self._vtimezone_with_dst(transition_info)

        # Generate component based with the calculated transitions
        vtimezone = icalendar.Timezone(tzid=timezone_name)
        for trans in transitions:
            vtimezone.add_component(trans)
        vtimezone.add("x-lic-location", timezone_name)
        self._zones[timezone_name] = vtimezone
        return vtimezone

    def _vtimezone_without_dst(self, transition_info: zoneinfo._zoneinfo._ttinfo) -> icalendar.TimezoneStandard:
        """Generates a STANDARD-timezone"""
        component = icalendar.TimezoneStandard()
        component.add("tzoffsetfrom", transition_info.utcoff)
        component.add("tzoffsetto", transition_info.utcoff)
        component.add("tzname", transition_info.tzname)
        component.add("dtstart", datetime.datetime(1970, 1, 1))
        return component

    def _vtimezone_with_dst(
        self,
        transition_info: zoneinfo._zoneinfo._TZStr,
    ) -> list[icalendar.TimezoneStandard | icalendar.TimezoneDaylight]:
        """Generates a DAYLIGHT and STANDARD timezone"""
        # Generate DAYLIGHT item
        component_dst = icalendar.TimezoneDaylight()
        component_dst.add("tzoffsetfrom", transition_info.std.utcoff)
        component_dst.add("tzoffsetto", transition_info.dst.utcoff)
        component_dst.add("tzname", transition_info.dst.tzname)
        dst_start_dt = datetime.datetime.fromtimestamp(transition_info.start.year_to_epoch(1970), tz=utc)
        component_dst.add("dtstart", dst_start_dt.replace(tzinfo=None))
        week = transition_info.start.w
        if week == 5:
            week = -1
        rrule = icalendar.vRecur(
            {
                "FREQ": "YEARLY",
                "BYMONTH": transition_info.start.m,
                "BYDAY": f"{week}{self.WEEKDAYS[transition_info.start.d]}",
            }
        )
        component_dst.add("rrule", rrule)

        # Generate STANDARD item
        component_std = icalendar.TimezoneStandard()
        component_std.add("tzoffsetfrom", transition_info.dst.utcoff)
        component_std.add("tzoffsetto", transition_info.std.utcoff)
        component_std.add("tzname", transition_info.std.tzname)
        std_start_dt = datetime.datetime.fromtimestamp(transition_info.end.year_to_epoch(1970), tz=utc)
        component_std.add("dtstart", std_start_dt.replace(tzinfo=None))
        week = transition_info.end.w
        if week == 5:
            week = -1
        rrule = icalendar.vRecur(
            {
                "FREQ": "YEARLY",
                "BYMONTH": transition_info.end.m,
                "BYDAY": f"{week}{self.WEEKDAYS[transition_info.end.d]}",
            }
        )
        component_std.add("rrule", rrule)
        return [component_dst, component_std]


ical_timezone_factory = ICalTimezoneFactory()

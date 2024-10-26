from django.utils.timezone import now, localtime, get_current_timezone
import icalendar
import datetime

import zoneinfo


def set_time_for_RDATE_EXDATE(dates, time):
    """
    Sets the time (with the corresponding timezone) for a given set of dates.

    :param dates: Collection of datetime objects of which the time should be set
    :param time: A datetime object whose date and timezone are set to the collection of dates
    """
    local_time = localtime(time).time()
    set_time_fn = lambda date: get_current_timezone().localize(
        datetime.datetime.combine(localtime(date).date(), local_time),
    )
    return map(set_time_fn, dates)


# Based on: https://djangosnippets.org/snippets/10569/
def generate_vtimezone(timezone: str, for_date=None, num_years=None):
    if not timezone or "utc" in timezone.lower():  # UTC doesn't need a timezone definition
        return None
    if not for_date:
        for_date = now()
    z = zoneinfo.ZoneInfo(timezone)

    transitions = zip(z._utc_transition_times, z._transition_info)
    try:
        end_year = (num_years or 1) + for_date.year
        tzswitches = filter(
            lambda x: x[0].year >= for_date.year and (num_years is None or x[0].year <= end_year), transitions
        )

        return _vtimezone_with_dst(tzswitches, timezone)
    except:
        # Timezone has no DST
        std = (z._utc_transition_times[-1], z._transition_info[-1])
        if std[0].year > for_date.year:
            return None
        return _vtimezone_without_dst(std, timezone)


def _vtimezone_without_dst(std, timezone):
    vtimezone = icalendar.Timezone(tzid=timezone)
    standard = icalendar.TimezoneStandard()
    utc_offset, dst_offset, tz_name = std[1]
    standard.add("dtstart", std[0])
    standard.add("tzoffsetfrom", utc_offset)
    standard.add("tzoffsetto", utc_offset)
    standard.add("tzname", tz_name)
    vtimezone.add_component(standard)
    return vtimezone


def _vtimezone_with_dst(tzswitches, timezone):
    daylight = []
    standard = []

    prev_prev_transition_info = None
    prev_prev_component = None
    prev_component = None
    _, prev_transition_info = next(tzswitches, None)

    if prev_transition_info is not None:
        for transition_time, transition_info in tzswitches:
            utc_offset, dst_offset, tz_name = transition_info

            # utc-offset of the previous component
            prev_utc_offset = prev_transition_info[0]

            if prev_prev_component is not None and transition_info == prev_prev_transition_info:
                # DST-change is the same as earlier; merge the components rather than creating a new one!
                prev_prev_component.add("rdate", transition_time + prev_utc_offset)

                # Swap prev_prev and prev components
                temp_component = prev_component
                prev_component = prev_prev_component
                prev_prev_component = temp_component
            else:
                component = None
                lst = None
                is_dst = dst_offset.total_seconds() != 0

                if is_dst:
                    component = icalendar.TimezoneDaylight()
                    lst = daylight
                else:
                    component = icalendar.TimezoneStandard()
                    lst = standard

                component.add("dtstart", transition_time + prev_utc_offset)
                component.add("rdate", transition_time + prev_utc_offset)
                component.add("tzoffsetfrom", prev_utc_offset)
                component.add("tzoffsetto", utc_offset)
                component.add("tzname", tz_name)

                lst.append(component)
                prev_prev_component = prev_component
                prev_component = component

            prev_prev_transition_info = prev_transition_info
            prev_transition_info = transition_info

        # Create timezone component, and add all standard/dst components to it
        vtimezone = icalendar.Timezone(tzid=timezone)
        for d in daylight:
            vtimezone.add_component(d)
        for s in standard:
            vtimezone.add_component(s)
        return vtimezone

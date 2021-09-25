from django.utils.timezone import pytz, now, localtime, get_current_timezone
import icalendar
import datetime

def dst_aware_to_dst_ignore(date, origin_date, reverse=False):
    """
        Takes the difference in UTC-offsets for two given dates, and applies that
        difference to the first date. A reverse keyword indicates which direction
        the offset should be shifted.

        Can be used to account keep times similar as if Daylight Saving Time did not exist.
        E.g. If a date at 16.00h in CEST (UTC+2) should be considered to be the same time
        as an origin date at 16.00h in CET (UTC+1), even though their UTC-times do not match.

        :param date: The date to modify
        :param origin_date: The origin date
        :param reverse: If True,  shifts `date` backwards (i.e. `date` already acted as if it had
                            the UTC-offset of `origin_date`, and we wish to reverse this change.)
                        Otherwise, shifts `date` forward (i.e. makes the `date` act as if it had
                            the UTC-offset of `origin_date`)
    """

    start_utc_offset = localtime(origin_date).utcoffset()
    date_utc_offset = localtime(date).utcoffset()

    if reverse:
        date = date - (start_utc_offset - date_utc_offset)
    else:
        date = date + (start_utc_offset - date_utc_offset)
    return localtime(date)

def set_time_for_RDATE_EXDATE(dates, time, make_dst_ignore=False):
    """
        Sets the time (with the corresponding timezone) for a given set of dates.

        :param dates: Collection of datetime objects of which the time should be set
        :param time: A datetime object whose date and timezone are set to the collection of dates
        :param make_dst_ignore: If these dates (RDATES or EXDATEs) are made dst-aware later on,
            then this difference can be accounted here by offsetting this change backwards.
    """
    local_time = localtime(time).time()
    set_time_fn = (lambda date:
            get_current_timezone().localize(
                datetime.datetime.combine(localtime(date).date(), local_time),
            )
        )

    if not make_dst_ignore:
        return map(set_time_fn, dates)

    return map(lambda date: dst_aware_to_dst_ignore(set_time_fn(date), time, reverse=True), dates)


# Based on: https://djangosnippets.org/snippets/10569/
def generate_vtimezone(timezone, for_date=None, num_years=None):
    if not timezone or 'utc' in timezone.lower():  # UTC doesn't need a timezone definition
        return None
    if not for_date:
         for_date = now()
    z = pytz.timezone(timezone)
    transitions = zip(z._utc_transition_times, z._transition_info)
    try:
        end_year = (num_years or 1) + for_date.year
        tzswitches = filter(lambda x: x[0].year >= for_date.year
                and (num_years is None or x[0].year <= end_year), transitions)

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
    standard.add('dtstart', std[0])
    standard.add('tzoffsetfrom', utc_offset)
    standard.add('tzoffsetto', utc_offset)
    standard.add('tzname', tz_name)
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

        for (transition_time, transition_info) in tzswitches:
            utc_offset, dst_offset, tz_name = transition_info

            # utc-offset of the previous component
            prev_utc_offset = prev_transition_info[0]

            if prev_prev_component is not None and transition_info == prev_prev_transition_info:
                # DST-change is the same as earlier; merge the components rather than creating a new one!
                prev_prev_component.add('rdate', transition_time + prev_utc_offset)

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

                component.add('dtstart', transition_time + prev_utc_offset)
                component.add('rdate', transition_time + prev_utc_offset)
                component.add('tzoffsetfrom', prev_utc_offset)
                component.add('tzoffsetto', utc_offset)
                component.add('tzname', tz_name)

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

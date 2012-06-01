from dateutil.relativedelta import relativedelta
from datetime import date
from dateutil import parser


def convert_to_date(date):
    """
    Takes a string and convert it to a date object
    """
    return parser.parse(date)


def get_last_day_month(date):
    """
    Gets the last day of the month of the date argument
    """

    last_day = date + relativedelta(day=1, months=+1, days=-1)

    return last_day


def get_first_day_next_month(date):
    """
    Gets the first day of the next month of the date argument
    """

    first_day = date + relativedelta(day=1, months=+1)

    return first_day


def get_last_day_next_month(date):
    """
    Gets the last day of the next month of the date argument
    """

    first_day = get_first_day_next_month(date)
    last_day = get_last_day_month(first_day)

    return last_day
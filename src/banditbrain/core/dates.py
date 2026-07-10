from datetime import date, datetime, timedelta

import numpy as np


def get_prediction_date(d: str | date | datetime | None) -> str:
    """
    Converts a string, date, or datetime object into a standardized prediction date (ISO format).
    Always returns the date of the next day (+1).
    """
    if d is None or d == "":
        date_obj = datetime.today().date()
    elif isinstance(d, str):
        try:
            date_obj = np.datetime64(d).astype("M8[D]").astype(object)
        except Exception:
            date_obj = datetime.fromisoformat(d).date()
    else:
        date_obj = d

    prediction_date = date_obj + timedelta(days=1)
    return prediction_date.isoformat() if hasattr(prediction_date, "isoformat") else str(prediction_date)

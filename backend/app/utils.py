from datetime import timedelta, date, datetime
import numpy as np
from typing import Union

def get_prediction_date(d: Union[str, date, datetime, None]) -> str:
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

def serialize_row(row, columns):
    result = {}
    for col, val in zip(columns, row):
        if isinstance(val, (date, datetime)):
            result[col] = val.isoformat()
        else:
            result[col] = val
    return result


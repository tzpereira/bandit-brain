from datetime import date, datetime

def serialize_row(row, columns):
    result = {}
    for col, val in zip(columns, row):
        if isinstance(val, (date, datetime)):
            result[col] = val.isoformat()
        else:
            result[col] = val
    return result
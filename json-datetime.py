import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)

# Example usage
data = {
    "name": "John Smith",
    "date_of_birth": datetime(1990, 1, 1)
}

json_data = json.dumps(data, cls=DateTimeEncoder)
print(json_data)
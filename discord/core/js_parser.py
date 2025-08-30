class MissingCompleted(Exception): pass
class InvalidFormat(Exception): pass
class NonInteger(Exception): pass

def extract_fish_ids(json_data) -> list[int]:
    if isinstance(json_data, dict):
        if "completed" not in json_data:
            raise MissingCompleted()
        raw = json_data["completed"]
    elif isinstance(json_data, list):
        raw = json_data
    else:
        raise InvalidFormat()
    if not all(isinstance(i, int) for i in raw):
        raise NonInteger()
    return list(dict.fromkeys(raw))
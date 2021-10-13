import dataclasses
import datetime

import dataclasses_json
import marshmallow
from dateutil.parser import isoparse

def parse_date(isodate: str) -> datetime:
    print("PARSE_DATE", isodate)
    return isoparse(isodate)


def _isodate(fn=None) -> dataclasses.field:
    return dataclasses.field(metadata=dataclasses_json.config(
                                        field_name=fn, encoder=datetime.datetime.isoformat,
                                        decoder=parse_date, 
                                        mm_field=marshmallow.fields.DateTime(format="iso", data_key=fn)
                                        ),
                            default_factory=datetime.datetime.now)


@dataclasses_json.dataclass_json
@dataclasses.dataclass(frozen=True)
class Example:
    StartTime: datetime.datetime = _isodate("start_time")

ej = """
{
    "start_time": "2018-08-14T12:54:16.722357636Z"
}
"""


ej2 = """
{
    "start_time": "2018-08-14T12:54:16.722357636+02:00"
}
"""

print(Example.from_json(ej2))
print(Example.schema().loads(ej2))

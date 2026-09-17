from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Location(BaseModel):
    type: str
    # Fields for text location
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    # Fields for pdf location
    page: Optional[int] = None
    paragraph: Optional[int] = None
    # Fields for table location
    table_id: Optional[str] = None
    row: Optional[int] = None
    column: Optional[int] = None
    # Fields for figure location
    figure_id: Optional[str] = None
    region: Optional[str] = None


class Evidence(BaseModel):
    id: str
    source_id: str
    source_type: str
    location: Location
    content: str

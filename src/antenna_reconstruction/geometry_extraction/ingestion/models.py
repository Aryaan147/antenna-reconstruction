from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class MockGeometryInput(BaseModel):
    source_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

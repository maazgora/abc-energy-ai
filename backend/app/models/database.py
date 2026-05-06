from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()  

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    business_segment: str
    annual_usage_mwh: float
    tier: str  
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class ConversationState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    raw_transcript: str
    extracted_data_json: str  
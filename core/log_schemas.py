from pydantic import BaseModel, Field
from datetime import datetime
from typing import *

# --- Core Sub-Schema ---
class TaskStep(BaseModel):
    """ Schema for a single step/node transition within a task. """
    node: str
    timestamp: datetime = Field(default_factory=datetime.now)

# --- 1. Insertion Schema (Full Document) ---
class TaskLogEntry(BaseModel):
    """ The complete schema for a single task log document inserted at START. """
    task_id: str
    prompt: str
    status: str = "In Progress"
    current_event: str = "START"
    # Fields that start empty but are updated later
    web_search_query: Optional[str] = None
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    trajectory: List[TaskStep] = Field(default_factory=list)
    final_response: Optional[str] = None
    task: Optional[str] = None
    task_choice_summary: Optional[str] = None

# --- 2. $SET Update Schema (Partial Document Update) ---
class TaskLogEndUpdate(BaseModel):
    """ Schema for the fields being $set when a task ends. """
    current_event: str = "END"
    final_response: Optional[str]
    task: Optional[str]
    task_choice_summary: Optional[str]
    search_query: Optional[str]
    search_results: List[Dict[str, Any]] # To overwrite final results
    status: str = "Completed"

# --- 3. $PUSH Update Schema (For Array Appending) ---
class TaskLogStepPush(BaseModel):
    """ Schema for the trajectory field update (using $push). """
    trajectory: TaskStep # Pydantic expects a single TaskStep object here
from pydantic import BaseModel, Field

class AgentExecuteInput(BaseModel):
    """ Schema for the input JSON payload to the /v1/agent/execute endpoint. """
    task: str = Field(description="The user's prompt/task for the agentic framework.")
    thread_id: str | None = Field(None, description="The existing thread ID for the task.")

class AgentExecuteOutput(BaseModel):
    """ Schema for the immediate response from the API. """
    task_id: str = Field(description="The unique ID generated for this task.")
    status: str = Field("QUEUED", description="The status of the task.")
    message: str = Field(description="Confirmation message and worker monitoring instructions.")

class TaskStatusOutput(BaseModel):
    """ Schema for checking the status of a task sent to an agent. """
    task_id: str = Field(description="The unique ID of this task.")
    final_response: str | None = Field(description="The final response from the LLM.")
    status: str = Field(description="The current status of the task.")

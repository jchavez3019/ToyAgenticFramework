import uuid
import os
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .api_models import AgentExecuteInput, AgentExecuteOutput, TaskStatusOutput
from worker.tasks import execute_agent_framework
from core import MongoDBLogger
from typing import *

try:
    mongo_logger = MongoDBLogger()
except ValueError:
    raise RuntimeError("MongoDB connection required for API status endpoint.")
app = FastAPI(title="Toy Agentic Framework API")

allowed_origins_string: str = os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost")
origins: List[str] = allowed_origins_string.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    "/v1/agent/execute/",
    response_model=AgentExecuteOutput,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a user prompt for agent execution."
)
async def execute_task(task_input: AgentExecuteInput):
    """

    :param task_input:
    :return:
    """
    # generate a unique task ID
    # TODO: Consider in the future, but perhaps it is better to have MongoDB generate the unique ID.
    new_task_id = str(uuid.uuid4())

    # dispatch the task to Celery
    execute_agent_framework.apply_async(
        args=[new_task_id, task_input.task],
        task_id=new_task_id # let the Celery worker's task ID match the task ID we pass to the LangGraph app
    )

    # return an immediate response
    return AgentExecuteOutput(
        task_id=new_task_id,
        status="QUEUED",
        message=f"Task received and queued. Task ID: {new_task_id}. Check logs or a status endpoint for results."
    )

@app.get(
    "/v1/agent/status/",
    response_model=TaskStatusOutput
)
def get_task_status(task_id: str):
    """
    Checks the status of an agent execution task and returns the final result if completed.
    :param task_id:
    :return:
    """
    task_data = mongo_logger.get_task_by_id(task_id)

    if task_data is None:
        # FIXME:
        #   Originally we would raise an exception, but it could be that the front-end queries so quickly that the
        #   task_id simply has not been put into the database yet. We should figure out how to nicely handle this
        #   scenario. For now, let's initialize the status to 'Unknown'.
        # the user passed a task id that does not exist in the database
        # raise HTTPException(status_code=404, detail=f"Task ID '{task_id}' not found.")
        task_data = {
            "status": "Unknown"
        }

    status = task_data.get("status", "Unknown")

    if status in ['Completed', 'Error']:
        # TODO:
        #   Consider what else should be sent back to the user. Remember to also update `TaskStatusOutput` in
        #   'api_models.py'
        response_data = TaskStatusOutput(
            task_id=task_id,
            final_response=task_data.get("final_response"),
            status=status,
            search_results=task_data.get("search_results", []),
        )
    else:
        response_data = TaskStatusOutput(
            task_id=task_id,
            final_response=None,
            status=status,
            search_results = [],
        )

    return response_data

@app.get("/health/")
def health_check():
    """ Simple health check endpoint to check if the API is running. """
    return {"status": "API is running."}
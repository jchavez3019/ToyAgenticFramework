import os
from pymongo import MongoClient
from core.log_schemas import TaskLogEntry, TaskStep, TaskLogEndUpdate, TaskLogStepPush
from typing import *

class MongoDBLogger:
    def __init__(self):
        # retrieve connection details from environment variables
        self.mongo_uri = os.getenv("MONGO_URI")
        self.database_name = os.getenv("MONGO_DATABASE_NAME", "ToyAgenticFrameworkLogs")
        self.collection_name = os.getenv("MONGO_COLLECTION_NAME", "TaskLogs")

        if not self.mongo_uri:
            raise ValueError("MONGO_URI environment variable not set.")

        # establish connection
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]

        print(f"MongoDB Logger initialized. Database: {self.database_name}, Collection: {self.collection_name}")

    def log_task_start(self, task_id: str, prompt_content: str) -> None:
        """Logs the start of a new task/thread."""
        log_data = TaskLogEntry(
            task_id = task_id,
            prompt = prompt_content,
            # Defaults handle the rest: current_event="START", status="In Progress", trajectory=[]
        )
        self.collection.insert_one(log_data.model_dump(by_alias=True, exclude_none=True))

    def log_task_end(self, task_id: str, final_state: Dict[str, Any], final_status: Optional[str] = "Completed") -> None:
        """Logs the completion of a task, storing the final state."""

        # Use the dedicated update schema
        update_data = TaskLogEndUpdate(
            # final_response=final_state['response'].content,
            final_response=getattr(final_state['response'], 'content', final_state['response']),
            task=final_state['task_classification']['task'],
            task_choice_summary=final_state['task_classification']['choice_summary'],
            # Note: search_results must be a list of dicts or it will fail validation
            search_results=final_state.get('search_results', []),
            search_query=final_state.get('search_query', "n/a"),
            status=final_status
        )

        # Structure the payload for the $set operator
        update_doc = {
            "$set": update_data.model_dump(exclude_none=True)
        }

        self.collection.update_one({"task_id": task_id}, update_doc, upsert=True)

    def log_step(self, task_id: str, node_name: str, updates: Dict[str, Any]) -> None:
        """Logs the transition through a specific node/step in the LangGraph."""

        # Use the dedicated push schema
        push_data = TaskLogStepPush(
            trajectory=TaskStep(
                node=node_name,
            )
        )

        # Structure the payload for the $push operator
        self.collection.update_one(
            {"task_id": task_id},
            {"$push": push_data.model_dump(exclude_none=True)},
            upsert=True
        )

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a task document from MongoDB by its ID
        :param task_id:
        :return:
        """
        # returns None when no matching document is found
        return self.collection.find_one({"task_id": task_id})
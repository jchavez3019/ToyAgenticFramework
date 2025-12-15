import os
from celery import Celery
from dotenv import load_dotenv
from core import build_graph, MongoDBLogger
from langchain_openai import ChatOpenAI

# NOTE: Toggle to True when willing to use the OpenAI API. Preferably set to False when debugging the system to prevent
# execution from wasting tokens. This can be toggled in the `[dev/prod].env` file so that we do not need to manually
# change this file.
USE_LLM = os.getenv("USE_LLM")

# load in the environment variables
load_dotenv("secrets/dev.env")

# check that the Redis URL has been specified
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise ValueError("REDIS_URL not set in the environment.")

# configure the Celery App
celery_app = Celery(
    'agent_tasks',
    broker=redis_url,
    backend=redis_url,
)

@celery_app.task(name='execute_agent_framework')
def execute_agent_framework(task_id: str, prompt_content: str) -> str:
    """
    This is a background task which executes the agentic framework to cater to the user's prompt.
    :param task_id:         The ID of this task.
    :param prompt_content:  The user's prompt.
    :return:                The response from the agentic framework.
    """
    # We want to initialize the Logger and LangGraph inside the worker process.
    # This method runs every time a worker processes a task.
    logger = MongoDBLogger()

    # Set up the initial state for the LangGraph App.
    initial_state = {
        "prompt_content": prompt_content,
        "task_id": task_id
    }
    config = {"configurable": {"thread_id": task_id}}

    if USE_LLM:
        gpt_model = "gpt-4.1"
        llm = ChatOpenAI(model=gpt_model)
        print(f"We are using the ChatGPT model {gpt_model}.")
    else:
        llm = None
        print("We are running the script without actually invoking any LLM's (preferred option when debugging the "
              "LangGraph script without wasting token use).")

    app = build_graph(logger, llm)

    # start the logger
    logger.log_task_start(task_id, prompt_content)

    try:
        # get the response from the framework and store it in MongoDB
        result = app.invoke(initial_state, config)
        logger.log_task_end(task_id, result, final_status="Completed")
    except Exception as e:
        error_state = {"response": f"ERROR: {str(e)}",
                       "task_classification": {"task": "error", "choice_summary": "execution failed"}}
        logger.log_task_end(task_id, error_state, final_status="Failed")
        raise e

from dotenv import load_dotenv
from core import doublecheck_env
import uuid
from langchain_openai import ChatOpenAI
from core import MongoDBLogger, build_graph, display_graph

if __name__ == '__main__':
    USE_LLM = False

    # Load environment variables from .env
    load_dotenv("../secrets/dev.env")

    # Check and print results
    doublecheck_env("../secrets/dev.env")

    try:
        logger = MongoDBLogger()
    except ValueError as e:
        print(f"Logging setup failed with error: {e}\nRunning without database logging.")
        logger = None

    if USE_LLM:
        gpt_model = "gpt-4.1"
        llm = ChatOpenAI(model=gpt_model)
        print(f"We are using the ChatGPT model {gpt_model}.")
    else:
        llm = None
        print("We are running the script without actually invoking any LLM's (preferred option when debugging the "
              "LangGraph script without wasting token use).")

    # Build the graph
    app = build_graph(logger, llm)

    # Display an image of the graph
    display_graph(app)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    content = """
        I am a beginner when it comes to writing blogs. Can you write a blog for me talking about how I am 
        having an amazing time at university and learning a lot as a mechanical engineer at UIUC?
        """

    initial_state = {
        "prompt_content": content,
        "task_id": thread_id,
    }
    if logger:
        logger.log_task_start(initial_state['task_id'], initial_state['prompt_content'])
    print(f"User prompt: \n{initial_state['prompt_content']}")

    # invoke the application graph
    result = app.invoke(initial_state, config)

    if logger:
        logger.log_task_end(thread_id, result)
    print(f"The agentic framework decided that this query facilitated a {result['task_classification']['task']} task "
          f"for the following reason, \n\t{result['task_classification']['choice_summary']}\n")
    if result['search_results']:
        print(f"The agent also searched the web with the following Google query:\n{result['search_query']}")
        print("The query yielded the following results:")
        for i, r in enumerate(result['search_results']):
            print(f"Result {i} | {r}")
    print(f"The final response is as follows:\n{result['response']}")
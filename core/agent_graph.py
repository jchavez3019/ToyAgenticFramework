from PIL import Image
from io import BytesIO
# LangChain imports
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph.graph import END, START, StateGraph
# for access to the Google search engine
from langchain_google_community import GoogleSearchAPIWrapper
# checkpointer for persistence
from langgraph.checkpoint.memory import InMemorySaver
# import logger which logs data to MongoDB
from .mongodb_logger import MongoDBLogger

from typing import *

AGENTS: List[str] = ["general", "code", "summarize", "content"]
T_AGENT = Literal[*AGENTS]
DEFAULT_TASK: T_AGENT = "general"

class TaskClassification(TypedDict):
    """
    Structured dictionary for holding the output of the LLM when determining which category the user's query
    belongs to.
    """
    task: T_AGENT
    choice_summary: str # Not necessary, but interesting to look into why an LLM chose a certain task

class ToyAgentFrameworkState(TypedDict):
    """
    Class describing the state parameters of the agent.
    """
    # the prompt to address
    prompt_content: str
    # id of this task
    task_id: str
    # FIXME: let's optionally support documents in the near future
    documents: List[str]

    # store the classification result which specifies which agent to use
    task_classification: TaskClassification | None

    # stores the search results that were used to aid with the Content Generation Agent
    search_results: List[Dict[str, Any]] | None
    search_query: str | None

    # store the response from the LLM
    response: str

def classify_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                     state: ToyAgentFrameworkState) -> Command[T_AGENT]:
    """
    This task invokes the LLM to figure out which agent it should send the user's request towards.
    :param logger:
    :param llm:
    :param state:   Current state in the graph.
    :return:        Parameters to update in the state in the graph.
    """

    classification_prompt = f"""
    Analyze the following prompt and determine whether it is a general query or one that can benefit from a coding
    agent, a summarizing agent, or a content generating agent (e.g. write a blog). The classification is limited to 
    the options: ['general', 'code', 'summarize', 'content']. 
    
    {state['prompt_content']}
    """
    print("We are currently in the classification task!")
    if llm:
        # get a structured output of what the task at hand is
        structured_llm = llm.with_structured_output(TaskClassification)
        classification = structured_llm.invoke(classification_prompt)
        goto = classification.get("task", DEFAULT_TASK)
    else:
        # by default, use the general llm task
        classification: TaskClassification = {
            'task': DEFAULT_TASK,
            'choice_summary': 'default choice when no llm is used'
        }
        goto=DEFAULT_TASK
    updates = {'task_classification': classification}
    logger.log_step(state['task_id'], 'task_classification', updates)
    return Command(
        update = updates,
        goto = goto,
    )

def general_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                     state: ToyAgentFrameworkState) -> ToyAgentFrameworkState:
    """
    This task simply acts upon the original query, answering the user's prompt.
    :param logger:
    :param llm:
    :param state:   Current state in the graph.
    :return:        Parameters to update in the state in the graph.
    """
    print("We are currently in the general task!")
    original_prompt = state["prompt_content"]
    if llm:
        response = llm.invoke(original_prompt)
    else:
        response = "Hi, I am the general task agent!"

    updates = {'response': response}
    logger.log_step(state['task_id'], 'general', updates)
    return updates


def coding_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                     state: ToyAgentFrameworkState) -> ToyAgentFrameworkState:
    """
    This task solely outputs code for the user.
    :param logger:
    :param llm:
    :param state:   Current state in the graph.
    :return:        Parameters to update in the state in the graph.
    """
    print("We are currently in the coding task!")
    original_prompt = state["prompt_content"]
    draft_prompt = f"""
    You are a useful coding assistant that will aid in answering the prompt below. You output should be in the language
    specified by the user, otherwise, default to Python. You will solely output code and nothing else, i.e. no verbal
    reasoning. Be precise and considerate with your changes, doing the absolute best to avoid creating bugs.
    
    {original_prompt}
    """
    if llm:
        response = llm.invoke(draft_prompt)
    else:
        response = "Hi, I am the general task agent!"

    updates = {'response': response}
    logger.log_step(state['task_id'], 'code', updates)
    return updates


def summarizing_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                     state: ToyAgentFrameworkState) -> ToyAgentFrameworkState:
    """
    This task is responsible for summarizing the user's prompt.
    :param logger:
    :param llm:
    :param state:   Current state in the graph.
    :return:        Parameters to update in the state in the graph.
    """
    print("We are currently in the summarization task!")
    original_prompt = state["prompt_content"]
    draft_prompt = f"""
        You are a useful summarizing assistant that will help the user 
        summarize their content in a concise, readable, and clear manner. 

        {original_prompt}
        """

    if llm:
        response = llm.invoke(draft_prompt)
    else:
        response = "Hi, I am the general task agent!"

    updates = {'response': response}
    logger.log_step(state['task_id'], 'summarize', updates)
    return updates

def content_web_searching_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                               state: ToyAgentFrameworkState) -> ToyAgentFrameworkState:
    """

    :param logger:
    :param llm:
    :param state:
    :return:
    """
    print("We are currently in the content web searching task!")
    original_prompt = state["prompt_content"]

    draft_prompt = f"""
    You are going to read the following prompt and return in a STRICTLY concise fashion, a high-quality
    search query to Google that should return the most relevant and helpful links to the prompt. Your response will
    be passed directly into the Google search bar.

    {original_prompt}
    """
    if llm:
        search_query = llm.invoke(draft_prompt).content
    else:
        # just use the original prompt as the query
        search_query = original_prompt

    # let's initialize the Google Search Wrapper
    search = GoogleSearchAPIWrapper(k=4)  # we retrieve the first 4 results

    # let's now execute the search on the original prompt
    try:
        search_results = search.results(search_query, num_results=4)
    except Exception as e:
        search_results = None
        print(f"Error during the Google Search. Check your API key and CSE ID. Error: \n{e}")

    updates = {'search_query': search_query, 'search_results': search_results}
    logger.log_step(state['task_id'], 'content', updates)
    return updates

def content_generation_task(logger: MongoDBLogger, llm: Optional[ChatOpenAI],
                            state: ToyAgentFrameworkState) -> ToyAgentFrameworkState:
    """
    This task is responsible for generating content related to the user's prompt.
    :param logger:  MongoDBLogger object.
    :param llm:     LLM object instance.
    :param state:   Current state in the graph.
    :return:        Parameters to update in the state in the graph.
    """
    print("We are currently in the content generation task!")
    original_prompt = state["prompt_content"]
    search_results = state["search_results"]

    # format the results for the LLM to easily read and cite
    formatted_sources = []
    if search_results:
        for i, result in enumerate(search_results):
            formatted_sources.append(
                f"[Source {i+1}]: {result.get('snippet', 'No Snippet available.')}"
                f"\nLink: {result.get('link', 'No URL link available.')}"
            )
    # join the formatted sources into a paragraph that we will append to the response below
    sources_text = "\n".join(formatted_sources)

    draft_prompt = f"""
        You are a content generation agent. Your task is to write a high-quality, comprehensive response
        to the user's request. You must use the information provided in the 'SEARCH RESULTS' section
        below if they are highly relevant and include clear citations (e.g., [Source 1], [Source 2]) in your 
        final output.

        ---- USER REQUEST ----
        {original_prompt}
        ---- SEARCH RESULTS ----
        {sources_text}
        """

    if llm:
        response = llm.invoke(draft_prompt)
    else:
        response = "Hi, I am the general task agent!"

    updates = {'response': response}
    logger.log_step(state['task_id'], 'content_post_web_search', updates)
    return updates

def build_graph(logger: MongoDBLogger, llm: Optional[ChatOpenAI]) -> CompiledStateGraph:
    """

    :return:
    """

    # Create the graph
    builder = StateGraph(ToyAgentFrameworkState)

    # Add nodes
    builder.add_node("task_classification", lambda s : classify_task(logger, llm, s))
    builder.add_node("general", lambda s : general_task(logger, llm, s))
    builder.add_node("code", lambda s : coding_task(logger, llm, s))
    builder.add_node("summarize", lambda s : summarizing_task(logger, llm, s))
    builder.add_node("content", lambda s : content_web_searching_task(logger, llm, s))
    builder.add_node("content_post_web_search", lambda s : content_generation_task(logger, llm, s))

    # Add edges
    builder.add_edge(START, "task_classification")
    builder.add_edge("general", END)
    builder.add_edge("code", END)
    builder.add_edge("summarize", END)
    builder.add_edge("content", "content_post_web_search")
    builder.add_edge("content_post_web_search", END)

    memory = InMemorySaver()
    app = builder.compile(checkpointer = memory)

    return app

def display_graph(a: CompiledStateGraph):
    """ Use the Pillow library to open a window which visually display the application graph. """
    # get the raw PNG byte data
    png_bytes = a.get_graph().draw_mermaid_png()
    # wrap the bytes in an in-memory file stream
    image_stream = BytesIO(png_bytes)
    img = Image.open(image_stream)
    img.show()

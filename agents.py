import logging
import os
import sys

from dotenv import load_dotenv
from llama_index.core.agent import ReActAgent
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from agent_tools import crypto_tools
from schemas import BinancePriceData, CoingeckoMarketData


from degen_trader_agent import degen_trader_query_engine

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().handlers = []
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

llm = OpenAI(model="gpt-4-1106-preview", max_tokens=1000, api_key=openai_api_key)
fetch_coingecko_market_data = crypto_tools.fetch_coingecko_market_data

process_news_articles = crypto_tools.process_news_articles


# create query engine tool for the degen trader query engine
degen_trader_query_engine_tool = QueryEngineTool(
    query_engine=degen_trader_query_engine,
    metadata=ToolMetadata(
        name="degen_trader_query_engine",
        description="This tool is used to answer questions related meme coins and degen traders, crypto trading, etc.",
    ),
)
# create query engine tool to be use in the sub question degen_trader query engine
degen_trader_query_engine_tools = [degen_trader_query_engine_tool]
# create a sub question query engine
degen_trader_sub_question_query_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=degen_trader_query_engine_tools,
    llm=llm,
)

# create query engine tool for sub question degen_trader query engine
degen_trader_sub_question_query_engine_tool = QueryEngineTool(
    query_engine=degen_trader_sub_question_query_engine,
    metadata=ToolMetadata(
        name="degen_trader_sub_question_query_engine",
        description="This tool is used to answer sub-questions related to the degen trader query engine.",
    ),
)

fetch_coingecko_market_data = FunctionTool.from_defaults(
    fn=fetch_coingecko_market_data,
    name="fetch_coingecko_market_data",
    description="This tool is used to fetch market data for a specific cryptocurrency from CoinGecko.",
    tool_metadata=ToolMetadata(
        fn_schema=CoingeckoMarketData,
        name="fetch_coingecko_market_data",
        description="This tool is used to fetch market data for a specific cryptocurrency from CoinGecko.",
    ),
)

process_news_articles = FunctionTool.from_defaults(
    fn=process_news_articles,
    name="process_news_articles",
    description="This tool is used to process news articles to  extract relevant information. like sentiment, etc.",
)

# tools
bot1_tools = [
    degen_trader_query_engine_tool,
    fetch_coingecko_market_data,
]

bot2_tools = [
    process_news_articles,
]
discord_ai_agent_tools = [
    degen_trader_query_engine_tool,
    fetch_coingecko_market_data,
    process_news_articles,
]

# response = agent.chat("tell me the latest news on meme coins that are trending")
# print(response)

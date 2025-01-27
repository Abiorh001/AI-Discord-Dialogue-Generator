from decouple import config
import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timedelta
from agents import bot1_tools, bot2_tools, llm
from prompt import bot1_context, bot2_context
from llama_index.core.agent import ReActAgent


# Configuration
channel_id = int(config("CHANNEL_ID"))
bot1_token = config("BOT1_TOKEN")
bot2_token = config("BOT2_TOKEN")
openai_api_key = config("OPENAI_API_KEY")

# Intents setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True


# Bot setup with shared channel
class SharedChannelBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_channel_id = channel_id
        self.opponent = None


# Create memory for each bot
bot1_memory = []  # Stores Bot1's chat history
bot2_memory = []  # Stores Bot2's chat history


# Function to dynamically update chat history
def format_chat_history(memory):
    """Format chat history from memory."""
    try:
        # Extract the last 5 messages from memory
        chat_history = memory[-10:]
        formatted_history = []
        for message in chat_history:
            if message["role"] == "user":
                formatted_history.append(f"User: {message['content']}")
            elif message["role"] == "assistant":
                formatted_history.append(f"Assistant: {message['content']}")
        return "\n".join(formatted_history)
    except Exception as e:
        print(f"Error formatting chat history: {e}")
        return "Chat history not available."


# Bot1 agent with dynamic chat history
# Bot1 agent with dynamic chat history
def bot1_agent(message: str):
    """Generate response for Bot1 using the predefined agent."""
    # Append the user's message to Bot1's memory
    bot1_memory.append({"role": "user", "content": message})

    # Format the chat history
    chat_history = format_chat_history(bot1_memory)

    # Replace {chat_history} in context
    updated_context = bot1_context.replace("{chat_history}", chat_history)
    print("updated_context:", updated_context)
    # Create the agent and generate a response
    agent = ReActAgent.from_tools(
        tools=bot1_tools,
        verbose=True,
        context=updated_context,
        llm=llm,
    )
    response = agent.chat(message)

    # Append Bot1's response to memory
    bot1_memory.append({"role": "assistant", "content": response.response})
    return response


# Bot2 agent with dynamic chat history
def bot2_agent(message: str):
    """Generate response for Bot2 using the predefined agent."""
    # Append the user's message to Bot2's memory
    bot2_memory.append({"role": "user", "content": message})

    # Format the chat history
    chat_history = format_chat_history(bot2_memory)

    # Replace {chat_history} in context
    updated_context = bot2_context.replace("{chat_history}", chat_history)

    # Create the agent and generate a response
    print("updated_context:", updated_context)
    agent = ReActAgent.from_tools(
        tools=bot2_tools,
        verbose=True,
        context=updated_context,
        llm=llm,
    )
    response = agent.chat(message)

    # Append Bot2's response to memory
    bot2_memory.append({"role": "assistant", "content": response.response})
    return response


# Bot instances
bot1 = SharedChannelBot(command_prefix="!", intents=intents)
bot2 = SharedChannelBot(command_prefix="!", intents=intents)

# Set opponents
# bot1.opponent = bot2
# bot2.opponent = bot1


# Add a class to track conversation context
# Add a class to track conversation context
class ConversationTracker:
    def __init__(self):
        self.previous_topics = set()
        self.discussion_history = []

    def add_topic(self, topic):
        self.previous_topics.add(topic)
        if len(self.previous_topics) > 5:
            self.previous_topics.pop()

    def add_message(self, message):
        self.discussion_history.append(message)
        if len(self.discussion_history) > 10:
            self.discussion_history.pop(0)


# Create separate trackers for each bot
bot1_tracker = ConversationTracker()
bot2_tracker = ConversationTracker()


# async def generate_response(agent_function, previous_message, tracker):
#     """Generate a response using LangChain with context tracking."""
#     try:
#         # Extract potential topics from the previous message
#         topics = set(re.findall(r'\$\w+', previous_message))
#         for topic in topics:
#             tracker.add_topic(topic)

#         # Prepare context for the response
#         response = agent_function(previous_message)  # Direct call to agent's chat method

#         # Add the generated response to the conversation history
#         tracker.add_message(response)

#         return response
#     except Exception as e:
#         print(f"Error generating response: {e}")
#         return "Let's continue our discussion about cryptocurrency."


async def generate_response(agent_function, previous_message):
    """Generate a response using LangChain with context tracking."""
    try:
        # Pass the message as a string to the agent function
        response = agent_function(previous_message)  # Correctly handle as raw string
        return response
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Let's continue our discussion about cryptocurrency."


# Event handling for Bot1
@bot1.event
async def on_message(message):
    # Ignore messages not in the target channel or from self
    if message.channel.id != channel_id or message.author == bot1.user:
        return

    # Respond only to messages from bot2
    if message.author == bot2.user:
        # Add a slight delay to simulate real-time responses
        await asyncio.sleep(10)
        channel = bot1.get_channel(channel_id)

        # Debugging: Check the message content
        print(f"Bot1 received message: {message.content}")

        # Generate response for Bot1 using context
        response = await generate_response(bot1_agent, message.content)

        # Debugging: Check the response from Bot1
        print(f"Bot1's response: {response}")

        # Send the response to Bot2
        await channel.send(response)


# Event handling for Bot2
@bot2.event
async def on_message(message):
    # Ignore messages not in the target channel or from self
    if message.channel.id != channel_id or message.author == bot2.user:
        return

    # Respond only to messages from bot1
    if message.author == bot1.user:
        # Add a slight delay to simulate real-time responses
        await asyncio.sleep(10)
        channel = bot2.get_channel(channel_id)

        # Debugging: Check the message content
        print(f"Bot2 received message: {message.content}")
        print("Bot1 Memory:", bot1_memory)
        print("Bot2 Memory:", bot2_memory)

        # Generate response for Bot2 using context
        response = await generate_response(bot2_agent, message.content)

        # Debugging: Check the response from Bot2
        print(f"Bot2's response: {response}")

        # Send the response to Bot1
        await channel.send(response)


async def start_conversation():
    """Initiate the conversation by having Bot1 send the first message."""
    channel = bot1.get_channel(channel_id)

    # Bot1 starts the conversation
    initial_message = "which meme coin i can buy tht is bullish in last 24hrs"
    await channel.send(initial_message)


# Event when Bot1 is ready
@bot1.event
async def on_ready():
    print(f"Trader 1 is online as {bot1.user}")
    await asyncio.sleep(5)
    await start_conversation()


# Event when Bot2 is ready
@bot2.event
async def on_ready():
    print(f"Trader 2 is online as {bot2.user}")


# Main function to run both bots concurrently
async def main():
    await asyncio.gather(bot1.start(bot1_token), bot2.start(bot2_token))


# Start both bots asynchronously
asyncio.run(main())

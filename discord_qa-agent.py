from decouple import config
import discord
from discord.ext import commands, tasks
import asyncio
from agents import llm, discord_ai_agent_tools
from prompt import discord_ai_agent_context
from llama_index.core.agent import ReActAgent

# Configuration
channel_id = int(config("DISCORD-BOT-CHANNEL-ID"))
discord_ai_agent_bot_token = config("DISCORD_AI_AGENT_BOT_TOKEN")
openai_api_key = config("OPENAI_API_KEY")

# Intents setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Memory to track individual user conversations
user_memory = {}


# Function to format chat history for each user
def format_chat_history(username):
    """Format chat history from memory based on the username."""
    chat_history = user_memory.get(username, [])
    formatted_history = []
    for message in chat_history[-10:]:  # Limit to last 10 messages
        role = "User" if message["role"] == "user" else "Assistant"
        formatted_history.append(f"{role}: {message['content']}")
    return "\n".join(formatted_history)


def bot_agent(message: str, username: str):
    """Generate a response for a user using the predefined agent."""
    # Add the user's message to memory
    if username not in user_memory:
        user_memory[username] = []
    user_memory[username].append({"role": "user", "content": message})

    # Format chat history for the given username
    chat_history = format_chat_history(username)

    # Replace {chat_history} and {username} in context
    updated_context = discord_ai_agent_context.replace("{chat_history}", chat_history)
    updated_context = updated_context.replace("{username}", username)

    # Create the agent and generate a response
    agent = ReActAgent.from_tools(
        tools=discord_ai_agent_tools,
        verbose=True,
        context=updated_context,
        llm=llm,
    )
    response = agent.chat(message)

    # Add the assistant's response to memory
    user_memory[username].append({"role": "assistant", "content": response.response})
    return response.response


# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_message(message):
    """Handle new messages and generate responses based on user input."""
    # Ignore messages from the bot or not in the correct channel
    if message.channel.id != channel_id or message.author == bot.user:
        return

    # Retrieve the username
    username = message.author.name

    # Generate response
    response = bot_agent(message.content, username)

    # Send the generated response to the same channel
    await message.channel.send(response)


# Start the bot
bot.run(discord_ai_agent_bot_token)

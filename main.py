import discord
from discord.message import Message

# from ollama import AsyncClient
from openai import AsyncOpenAI
import json
import os
import dotenv

dotenv.load_dotenv()

ACC_TOKEN = os.getenv("TOKEN")

# Define your target channel IDs
AI_CHANNELS = [
    1330237721557471232,  # Hideout
    1334351579058405447,  # Testing
    1330033413524033537,  # SST
]

COUNT_CHANNELS = [
    1330237721557471232,  # Hideout
]

BLOCK_LIST = [159985870458322944, 510016054391734273]

import re


def remove_think_content(text):
    return re.sub(r"\n*<think>.*?</think>\n*", "", text, flags=re.DOTALL)


def is_positive_number(s):
    try:
        # Try to convert the string to a float
        num = float(s)
        # Check if the number is positive
        if num > 0:
            return True
        else:
            return False
    except ValueError:
        # If conversion fails, it's not a number
        return False


class MyClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messagehistory = {}
        system_message = {
            "role": "system",
            "content": """My name is Lolibaba and my userid is 793266426349748235, that's what people call me. My AI model is Deepseek-r1.
                When someone <@username>, that means they are calling me out, and I just respond naturally 
                without mentioning that I was being mentioned. 
                In the context of messaging, <@username> means mentioning or @-ing a user by their user ID. When there's
                a message that includes <@username>, I will implicitly understand that a user is being mentioned."""
        }
        for item in os.listdir():
            if item.endswith(".json"):
                self.messagehistory[int(item.split(".")[0])] = self._load_messages_from_file(
                    item
                )
        print("Initializing message history...")
        for channel in AI_CHANNELS:
            if channel not in self.messagehistory:
                self.messagehistory[channel] = [system_message]  # Initialize with the system message
            else:
                self.messagehistory[channel][0] = system_message
        print(json.dumps(self.messagehistory, indent=4))
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )  # Initialize Ollama client

    def _load_messages_from_file(self, file_path: str) -> list:
        """Load messages from a file. Return an empty list if the file is empty or doesn't exist."""
        try:
            with open(file_path, "r") as file:
                content = file.read()
                if not content:
                    return []
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_messages_to_file(self, file_path: str, messages: list):
        """Save messages to a file."""
        with open(file_path, "w") as file:
            json.dump(messages, file)

    def _parse_mentions(self, message: Message) -> list:
        """Parse mentions from a message."""
        map = {}
        if message.mentions:
            for user in message.mentions:
                map[user.id] = user.global_name
        for id, name in map.items():
            message.content = message.content.replace(str(id), name)
        return message

    async def on_ready(self):
        print(f"Logged on as {self.user}")

    async def generate_response(
        self, user_message: dict, author: str, channelid
    ) -> str:
        """Generate a response using the Ollama model."""
        print(rf"Replying to {author}: {user_message['content']}")
        # Append user message to the conversation history
        self.messagehistory[channelid].append(
            {"role": "user", "content": rf'{author} says: {user_message["content"]}'}
        )
        print(json.dumps(self.messagehistory[channelid], indent=4))
        # Generate response using Ollama
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messagehistory[channelid],
            max_tokens=1000,
        )
        ret: str = remove_think_content(response.choices[0].message.content.strip())

        # Append the tool's response to the conversation history
        self.messagehistory[channelid].append({"role": "system", "content": ret})

        # Save updated messages to file
        self._save_messages_to_file(f"{channelid}.json", self.messagehistory[channelid])

        # Limit the conversation history to 100 messages
        if len(self.messagehistory[channelid]) > 100:
            self.messagehistory[channelid].pop(1)

        print(ret)
        if (
            is_positive_number(ret)
            or is_positive_number(ret[0])
            or ret.lower().startswith("pi")
            or ret.lower().startswith("π")
        ):
            ret = "Hah, don't think you got me this time: " + ret
        return ret.strip()

    async def on_message(self, message: Message):
        if message.author == self.user:
            return  # Ignore bot's own messages

        if message.guild and message.channel.id in COUNT_CHANNELS:
            if is_positive_number(message.content):  # Counting
                await message.channel.typing()
                await message.channel.send(int(round(float(message.content)) + 1))

        if message.guild and message.channel.id in AI_CHANNELS:
            if self.user.mentioned_in(message):  # Generative response
                if message.author.id in BLOCK_LIST:
                    return
                await message.channel.typing()
                self._parse_mentions(message)
                response = await self.generate_response(
                    {"role": "user", "content": message.content},
                    str(message.author.global_name),
                    message.channel.id,
                )
                await message.reply(response)


client = MyClient()
client.run(ACC_TOKEN)

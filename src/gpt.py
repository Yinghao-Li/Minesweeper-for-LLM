"""
# Author: Yinghao Li
# Modified: November 4th, 2023
# ---------------------------------------
# Description: GPT api call and message cache.
"""

import json
import openai
from typing import Union
from .prompts import *
from .io import save_json


class GPT:
    def __init__(
        self,
        resource_path: str,
        temperature: int = 0,
        max_tokens: int = 800,
        top_p: float = 0.95,
        frequency_penalty: float = 0,
        presence_penalty: float = 0,
        stop: list[str] = None,
    ) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.stop = stop
        self.engine = load_gpt_resources(resource_path)

    def response(self, messages: Union[list[dict[str, str]], "MessageCache"]) -> str:
        """
        Generate response from GPT.
        """
        if isinstance(messages, MessageCache):
            messages = messages.content

        if "instruct" in self.engine:
            prompt = messages[-1]["content"]
            r = openai.Completion.create(
                engine=self.engine,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                stop=self.stop,
            )
            return r["choices"][0]["text"]
        else:
            r = openai.ChatCompletion.create(
                messages=messages,
                engine=self.engine,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                stop=self.stop,
            )
            return r["choices"][0]["message"]["content"]

    def __call__(self, messages: Union[list[dict[str, str]], "MessageCache"]) -> str:
        return self.response(messages)


class MessageCache:
    def __init__(self, system_role: str = None) -> None:
        self.system_role = (
            system_role
            if system_role is not None
            else "You are a helpful assistant who is good at playing Minesweeper."
        )
        self.message_cache = list()
        self.add_message("system", self.system_role)

    def add_message(self, role: str, content: str) -> None:
        self.message_cache.append(
            {"role": role, "content": content},
        )

    def add_user_message(self, content: str) -> None:
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message("assistant", content)

    @property
    def content(self) -> list[dict[str, str]]:
        return self.message_cache

    def __str__(self) -> str:
        message = ""
        for msg in self.message_cache:
            message += f">> {msg['role'].upper()}:\n{msg['content']}\n\n"
        return message

    def print(self) -> None:
        print(self.__str__())

    def save(self, path: str) -> None:
        save_json(self.message_cache, path, collapse_level=2)

    def load(self, path: str) -> "MessageCache":
        with open(path, "r", encoding="utf-8") as f:
            self.message_cache = json.load(f)
        return self

    def save_plain(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.__str__())


def load_gpt_resources(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        resource_dict = json.load(f)

    for k, v in resource_dict.items():
        if k != "engine":
            setattr(openai, k, v)

    return resource_dict["engine"]

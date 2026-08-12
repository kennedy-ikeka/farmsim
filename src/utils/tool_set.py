from enum import StrEnum
from typing_extensions import Optional
from pydantic import BaseModel


class ToolSet(StrEnum):
    """Enumeration of available AI agent tools.

    Defines the set of tools that can be used by the AI assistant
    for various tasks like document extraction, analysis, and conversation.
    """

    Farmer = 'Farmer'
    Informant = 'Informant'
    Actor = 'Actor'
    Purchaser = 'Purchaser'
    Seller = 'Seller'


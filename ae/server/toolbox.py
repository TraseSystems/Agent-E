from typing import Any, Dict
from ae.core.skills.click_using_selector import click
from ae.core.skills.enter_text_using_selector import (
    bulk_enter_text,
    EnterTextEntry,
    entertext,
)
from ae.core.skills.get_dom_with_content_type import get_dom_with_content_type
from ae.core.skills.get_url import geturl
from ae.core.skills.open_url import openurl
from ae.core.skills.pdf_text_extractor import extract_text_from_pdf
from ae.core.skills.press_key_combination import press_key_combination

TOOLS = [
    {
        "type": "function",
        "function": {
            "description": "Opens a specified URL in the web browser instance. Returns url of the new page if successful or appropriate error message if the page could not be opened.",
            "name": "openurl",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to. Value must include the protocol (http:// or https://).",
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 3,
                        "description": "Additional wait time in seconds after initial load.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Retrieves the DOM of the current web site based on the given content type.\n   The DOM representation returned contains items ordered in the same way they appear on the page. Keep this in mind when executing user requests that contain ordinals or numbered items.\n   text_only - returns plain text representing all the text in the web site. Use this for any information retrieval task. This will contain the most complete textual information.\n   input_fields - returns a JSON string containing a list of objects representing text input html elements with mmid attribute. Use this strictly for interaction purposes with text input fields.\n   all_fields - returns a JSON string containing a list of objects representing all interactive elements and their attributes with mmid attribute. Use this strictly to identify and interact with any type of elements on page.\n   If information is not available in one content type, you must try another content_type.",
            "name": "get_dom_with_content_type",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "description": "The type of content to extract: 'text_only': Extracts the innerText of the highest element in the document and responds with text, or 'input_fields': Extracts the text input and button elements in the dom.",
                    }
                },
                "required": ["content_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Executes a click action on the element matching the given mmid attribute value. It is best to use mmid attribute as the selector.\n   Returns Success if click was successful or appropriate error message if the element could not be clicked.",
            "name": "click",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "The properly formed query selector string to identify the element for the click action (e.g. [mmid='114']). When \"mmid\" attribute is present, use it for the query selector.",
                    },
                    "wait_before_execution": {
                        "type": "number",
                        "default": 0.0,
                        "description": "Optional wait time in seconds before executing the click event logic.",
                    },
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Get the full URL of the current web page/site. If the user command seems to imply an action that would be suitable for an already open website in their browser, use this to fetch current website URL.",
            "name": "geturl",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Bulk enter text in multiple DOM fields. To be used when there are multiple fields to be filled on the same page.\n   Enters text in the DOM elements matching the given mmid attribute value.\n   The input will receive a list of objects containing the DOM query selector and the text to enter.\n   This will only enter the text and not press enter or anything else.\n   Returns each selector and the result for attempting to enter text.",
            "name": "bulk_enter_text",
            "parameters": {
                "type": "object",
                "properties": {
                    "entries": {
                        "items": {
                            "additionalProperties": {"type": "string"},
                            "type": "object",
                        },
                        "type": "array",
                        "description": "List of objects, each containing 'query_selector' and 'text'.",
                    }
                },
                "required": ["entries"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Single enter given text in the DOM element matching the given mmid attribute value. This will only enter the text and not press enter or anything else.\n   Returns Success if text entry was successful or appropriate error message if text could not be entered.",
            "name": "entertext",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry": {
                        "properties": {
                            "query_selector": {
                                "title": "Query Selector",
                                "type": "string",
                            },
                            "text": {"title": "Text", "type": "string"},
                        },
                        "required": ["query_selector", "text"],
                        "title": "EnterTextEntry",
                        "type": "object",
                        "description": "An object containing 'query_selector' (DOM selector query using mmid attribute e.g. [mmid='114']) and 'text' (text to enter on the element).",
                    }
                },
                "required": ["entry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "description": "Presses the given key on the current web page.\n   This is useful for pressing the enter button to submit a search query, PageDown to scroll, ArrowDown to change selection in a focussed list etc.",
            "name": "press_key_combination",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_combination": {
                        "type": "string",
                        "description": "The key to press, e.g., Enter, PageDown etc",
                    }
                },
                "required": ["key_combination"],
            },
        },
    },
    ## we leave this one out b/c we have our own implementation
    ## this version has the downside of flooding the context window with a bunch of text from large papers
    # {
    #     "type": "function",
    #     "function": {
    #         "description": "Extracts text from a PDF file hosted at the given URL.",
    #         "name": "extract_text_from_pdf",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "pdf_url": {
    #                     "type": "string",
    #                     "description": "The URL of the PDF file to extract text from.",
    #                 }
    #             },
    #             "required": ["pdf_url"],
    #         },
    #     },
    # },
]


async def call_tool(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """
    Calls the specified tool with the given arguments.

    Parameters:
    - tool_name: str - The name of the tool/skill to call
    - tool_args: Dict[str, Any] - Arguments to pass to the tool

    Returns:
    - Any - The result from calling the specified tool

    Raises:
    - ValueError if tool_name is not recognized
    """
    # Map tool names to their corresponding functions
    tool_map = {
        "openurl": openurl,
        "get_dom_with_content_type": get_dom_with_content_type,
        "click": click,
        "geturl": geturl,
        "bulk_enter_text": bulk_enter_text,
        "entertext": entertext,
        "press_key_combination": press_key_combination,
        "extract_text_from_pdf": extract_text_from_pdf,
    }

    # Get the appropriate function
    tool_func = tool_map.get(tool_name)
    if tool_func is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    try:
        # Call the function with unpacked arguments
        return await tool_func(**tool_args)
    except Exception as e:
        # Preserve the original exception type and message
        # raise type(e)(f"Error calling {tool_name}: {str(e)}") from e
        return f"Error calling tool: {str(e)}"

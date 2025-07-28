import json
import os
import uuid
import importlib
import inspect
import argparse
import logging
import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel
from rich import print

# Import the Virtual File System
from tools.vfs import VirtualFileSystem

from tools.base_tool import Tool

load_dotenv()
app = FastAPI()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
)

# --- Constants ---
DEFAULT_MODEL = "moonshotai/kimi-k2-instruct"
DEBUG_MODEL = "llama-3.1-8b-instant"
GROQ_MAX_OUTPUT_TOKENS = 16384

# --- Command Line Arguments ---
parser = argparse.ArgumentParser(description="Proxy server for Anthropic Claude to Groq")
parser.add_argument("--debug", action="store_true", help="Enable debug mode with cheaper model")
parser.add_argument("--log", action="store_true", help="Enable detailed file logging")
args = parser.parse_args()

# Set the model based on debug mode
GROQ_MODEL = DEBUG_MODEL if args.debug else DEFAULT_MODEL
DEBUG_MODE = args.debug

# Set up file logging if requested
if args.log:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"proxy_{timestamp}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info(f"Starting proxy server with model: {GROQ_MODEL}")
    print(f"[bold green]📝 Logging to {log_file}[/bold green]")

def log_message(message, level="info"):
    """Log a message to both console and file if logging is enabled"""
    # Always print to console
    print(message)
    
    # Log to file if enabled
    if args.log:
        if level == "info":
            logging.info(message.replace("[bold blue]", "").replace("[/bold blue]", "").replace("[blue]", "").replace("[/blue]", "").replace("[bold green]", "").replace("[/bold green]", "").replace("[green]", "").replace("[/green]", "").replace("[bold yellow]", "").replace("[/bold yellow]", "").replace("[bold cyan]", "").replace("[/bold cyan]", "").replace("[bold red]", "").replace("[/bold red]", ""))
        elif level == "error":
            logging.error(message.replace("[bold red]", "").replace("[/bold red]", ""))

if DEBUG_MODE:
    print(f"[bold green]🐛 DEBUG MODE ENABLED - Using model: {GROQ_MODEL}[/bold green]")

# --- Project Paths ---
PROJECT_ROOT = Path(__file__).parent.resolve()
TOOLS_DIR = PROJECT_ROOT / "tools"

# ---------- Tool Management ----------

class ToolManager:
    """Manages the loading and execution of tools."""

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir
        self.tools = {}
        
        # Initialize the Virtual File System with the current working directory
        self.vfs = VirtualFileSystem(Path.cwd())
        print(f"[bold blue]🌐 Initialized Virtual File System with base path: {self.vfs.base_path}[/bold blue]")
        
        self.load_tools()

    def load_tools(self):
        """Load all tools from the tools directory."""
        print(f"[bold blue]🔍 Loading tools from {self.tools_dir}...[/bold blue]")
        
        # Define a whitelist of allowed tools for security
        # Format: {module_name: [class_names]}
        tool_whitelist = {
            "write_tool": ["WriteTool"],
            "ls_tool": ["LSTool"],
            "bash_tool": ["BashTool"],
            "read_tool": ["ReadTool"],
        }
        
        for module_name, class_names in tool_whitelist.items():
            try:
                full_module_name = f"{self.tools_dir.name}.{module_name}"
                print(f"  - Importing module: {full_module_name}")
                module = importlib.import_module(full_module_name)
                
                for class_name in class_names:
                    try:
                        print(f"    - Looking for class: {class_name}")
                        tool_class = getattr(module, class_name)
                        tool_instance = tool_class()
                        
                        # Pass the VFS to the tool if it has a set_vfs method
                        if hasattr(tool_instance, 'set_vfs'):
                            tool_instance.set_vfs(self.vfs)
                            print(f"    ✅ Passed VFS to tool: {class_name}")
                            
                        tool_name = tool_instance.name
                        print(f"    ✅ Loaded tool: {tool_name} from {class_name}")
                        self.tools[tool_name] = tool_instance
                    except Exception as e:
                        print(f"    ❌ Error loading class {class_name}: {e}")
            except Exception as e:
                print(f"  ❌ Error importing module {module_name}: {e}")
                
        print(f"[bold green]✅ Loaded {len(self.tools)} tools: {list(self.tools.keys())}[/bold green]")

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name with the given arguments."""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"}
        
        try:
            # Log the current VFS working directory for debugging
            print(f"[bold cyan]📂 Current VFS working directory: {self.vfs.get_cwd()}[/bold cyan]")
            return self.tools[tool_name].execute(**kwargs)
        except Exception as e:
            return {"error": f"Error executing tool '{tool_name}': {str(e)}"}


# ---------- Anthropic Schema ----------
class ContentBlock(BaseModel):
    type: Literal["text"]
    text: str

class ToolUseBlock(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Union[str, int, float, bool, dict, list]]

class ToolResultBlock(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any], Any]

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[Union[ContentBlock, ToolUseBlock, ToolResultBlock]]]

class Tool(BaseModel):
    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]

class MessagesRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, str]]] = "auto"

# ---------- Conversion Helpers ----------


def convert_messages(messages: List[Message]) -> List[dict]:
    converted = []
    for m in messages:
        if isinstance(m.content, str):
            content = m.content
        else:
            parts = []
            for block in m.content:
                if block.type == "text":
                    parts.append(block.text)
                elif block.type == "tool_use":
                    tool_info = f"[Tool Use: {block.name}] {json.dumps(block.input)}"
                    parts.append(tool_info)
                elif block.type == "tool_result":
                    result = block.content
                    print(f"[bold yellow]📥 Tool Result for {block.tool_use_id}: {json.dumps(result, indent=2)}[/bold yellow]")
                    parts.append(f"<tool_result>{json.dumps(result)}</tool_result>")
            content = "\n".join(parts)
        converted.append({"role": m.role, "content": content})
    return converted



def convert_tools(tools: List[Tool]) -> List[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


def convert_tool_calls_to_anthropic(tool_calls) -> List[dict]:
    content = []
    for call in tool_calls:
        fn = call.function
        arguments = json.loads(fn.arguments)

        print(f"[bold green]🛠 Tool Call: {fn.name}({json.dumps(arguments, indent=2)})[/bold green]")

        content.append(
            {"type": "tool_use", "id": call.id, "name": fn.name, "input": arguments}
        )
    return content


# ---------- Main Proxy Route ----------


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the tool manager on startup
    log_message("[bold green]🚀 Application starting up...[/bold green]")
    app.state.tool_manager = ToolManager(tools_dir=TOOLS_DIR)
    yield
    # Clean up resources on shutdown if needed
    log_message("[bold red]🛑 Application shutting down...[/bold red]")

app = FastAPI(lifespan=lifespan)

@app.post("/v1/messages")
async def proxy(request: Request): # Changed to generic Request to access app state
    try:
        body = await request.json()
        messages_request = MessagesRequest(**body)
        model_info = f"[bold cyan]🚀 Anthropic → Groq | Requested Model: {messages_request.model} | Using Model: {GROQ_MODEL}"
        if DEBUG_MODE:
            model_info += " (DEBUG MODE)"
        model_info += "[/bold cyan]"
        log_message(model_info)

        openai_messages = convert_messages(messages_request.messages)
        tools = convert_tools(messages_request.tools) if messages_request.tools else None

        max_tokens = min(messages_request.max_tokens or GROQ_MAX_OUTPUT_TOKENS, GROQ_MAX_OUTPUT_TOKENS)

        if messages_request.max_tokens and messages_request.max_tokens > GROQ_MAX_OUTPUT_TOKENS:
            log_message(f"[bold yellow]⚠️  Capping max_tokens from {messages_request.max_tokens} to {GROQ_MAX_OUTPUT_TOKENS}[/bold yellow]")

        # First call to the model
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=openai_messages,
            temperature=messages_request.temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=messages_request.tool_choice,
        )

        choice = completion.choices[0]
        msg = choice.message
        
        # Log the model's response
        log_message(f"[bold blue]📝 Model Response (first call):[/bold blue]")
        if msg.content:
            # Always log the full content to file if logging is enabled
            if args.log:
                logging.info(f"FULL MODEL RESPONSE (first call):\n{msg.content}")
            # Truncate for console display
            content_preview = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            log_message(f"[blue]{content_preview}[/blue]")

        # If the model wants to use a tool, execute it and send back the result
        if msg.tool_calls:
            # Append the assistant's message with tool calls in the correct format
            assistant_message = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
            openai_messages.append(assistant_message)

            # Execute tools and append results
            for tool_call in msg.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                log_message(f"[bold green]🔨 Executing Tool: {function_name}({json.dumps(arguments, indent=2)})[/bold green]")
                
                # Log available tools for debugging
                available_tools = list(request.app.state.tool_manager.tools.keys())
                log_message(f"[bold yellow]... Available tools: {available_tools}[/bold yellow]")

                result = request.app.state.tool_manager.execute_tool(function_name, **arguments)
                
                log_message(f"[bold yellow]📥 Tool Result for {tool_call.id}: {json.dumps(result, indent=2)}[/bold yellow]")

                openai_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result),
                    }
                )

            # Second call to the model with the tool results
            log_message("[bold cyan]🔄 Resubmitting to model with tool results...[/bold cyan]")
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=openai_messages,
                temperature=messages_request.temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=messages_request.tool_choice if hasattr(messages_request, 'tool_choice') else None,
            )
            msg = completion.choices[0].message
            
            # Log the model's response after tool execution
            log_message(f"[bold green]📝 Model Response (after tool execution):[/bold green]")
            if msg.content:
                # Always log the full content to file if logging is enabled
                if args.log:
                    logging.info(f"FULL MODEL RESPONSE (after tool execution):\n{msg.content}")
                # Truncate for console display
                content_preview = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                log_message(f"[green]{content_preview}[/green]")

        # Normal response processing
        tool_content = [{"type": "text", "text": msg.content}]
        stop_reason = "end_turn"

        response = {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "model": f"groq/{GROQ_MODEL}",
            "role": "assistant",
            "type": "message",
            "content": tool_content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": completion.usage.prompt_tokens,
                "output_tokens": completion.usage.completion_tokens,
            },
        }
        
        # Log that we're returning the response
        log_message(f"[bold blue]📬 Returning response to client[/bold blue]")
        
        return response
        
    except Exception as e:
        # Log the error
        error_msg = f"[bold red]⚠️ ERROR: {str(e)}[/bold red]"
        log_message(error_msg, level="error")
        
        # Print the full traceback for debugging
        import traceback
        tb = traceback.format_exc()
        log_message(f"[bold red]Traceback:\n{tb}[/bold red]", level="error")
        
        # Return a proper error response
        return {
            "id": f"error_{uuid.uuid4().hex[:12]}",
            "error": {
                "type": "server_error",
                "message": f"An error occurred: {str(e)}"
            }
        }


@app.get("/")
def root():
    return {"message": "Groq Anthropic Tool Proxy is alive 💡"}


if __name__ == "__main__":
    # Change from 0.0.0.0 to 127.0.0.1 to restrict access to localhost only
    uvicorn.run(app, host="127.0.0.1", port=7187)

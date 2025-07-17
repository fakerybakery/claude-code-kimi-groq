# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI proxy server that enables using the Kimi K2 model (via Groq) with Claude Code. It translates between Anthropic's API format and Groq's OpenAI-compatible format.

## Commands

### Setup and Development
```bash
# Install uv package manager (if not already installed)
brew install astral-sh/uv/uv  # or: pipx install uv

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Run the proxy server
python proxy.py

# The proxy will start on http://localhost:7187
```

### Using with Claude Code
```bash
# Set environment variables to redirect Claude Code to the proxy
export ANTHROPIC_BASE_URL=http://localhost:7187
export ANTHROPIC_API_KEY=NOT_NEEDED  # if not already authenticated

# Run Claude Code as normal
claude
```

## Architecture

### Core Components

1. **proxy.py** - Main proxy server implementation
   - FastAPI application that intercepts Anthropic API calls
   - Converts Anthropic message format to OpenAI format for Groq
   - Handles tool use blocks and converts between formats
   - Streams responses back in Anthropic's expected format

### Key Technical Details

- **Model**: Uses `moonshotai/kimi-k2-instruct` via Groq API
- **Port**: Runs on port 7187 by default
- **Authentication**: Requires `GROQ_API_KEY` in environment
- **Message Conversion**: Handles system prompts, user messages, assistant responses, and tool use blocks
- **Streaming**: Supports streaming responses with proper SSE format

### Environment Variables

- `GROQ_API_KEY` - Required for Groq API access (stored in .env)
- `ANTHROPIC_BASE_URL` - Set to http://localhost:7187 when using the proxy
- `ANTHROPIC_API_KEY` - Can be set to any value when using the proxy
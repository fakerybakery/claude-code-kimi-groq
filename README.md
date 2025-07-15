# Use Kimi K2 on Claude Code through Groq

Run the Groq <> Anthropic API proxy:

```bash
python proxy.py
```

Set the Anthropic Base URL:

```
export ANTHROPIC_BASE_URL=http://localhost:7187
```

Run Claude Code with the Groq API key:

```bash
claude
```
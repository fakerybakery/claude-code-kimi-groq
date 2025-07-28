# Use Kimi K2 on Claude Code through Groq

This is a fork of fakerybakery's https://github.com/fakerybakery/claude-code-kimi-groq , experimenting with tool use support and additional security features. This is currently experimental, beta software. Use at your own risk, etc.

## Quick start (uv)

```bash
export GROQ_API_KEY=YOUR_GROQ_API_KEY

# one-time setup of uv, if needed
brew install astral-sh/uv/uv   # or pipx install uv

# project setup
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# run the proxy
python proxy.py
```

## CLI Options

The proxy supports several command-line options for configuration:

```
python proxy.py [OPTIONS]
```

Available options:

| Option        | Default           | Description                                            |
| ------------- | ----------------- | ------------------------------------------------------ |
| `--host`      | 127.0.0.1         | Host to bind the server to                             |
| `--port`      | 7187              | Port to run the server on                              |
| `--debug`     | False             | Use cheaper model while testing (llama-3.1-8b-instant) |
| `--log`       | False             | Enable detailed file logging of model responses        |
| `--vfs-base`  | Current directory | Set custom base directory for the Virtual File System  |
| `--tools-dir` | ./tools           | Set custom directory for tool modules                  |
| `--help`      | -                 | Show help message and exit                             |

Example with options:

```bash
python proxy.py --host 0.0.0.0 --port 8000 --debug --log --vfs-base /path/to/workspace --tools-dir /path/to/custom/tools
```

Set the Anthropic Base URL:

```
export ANTHROPIC_BASE_URL=http://localhost:7187
```

If you're not already authenticated with Anthropic you may need to run:

```
export ANTHROPIC_API_KEY=NOT_NEEDED
```

Run Claude Code with the Groq API key:

```bash
claude
```

## If you use this:

If you use this, I'd love to hear about your experience with Kimi K2 and how it compared with Claude! Please open an Issue to share your experience.

## Acknowledgements

Inspired by [claude-code-proxy](https://github.com/1rgs/claude-code-proxy)

## Testing

The project includes a comprehensive test suite focusing on security and functionality of core components:

- Path utilities (`utils.py`)
- Virtual File System (`vfs.py`)
- BashTool (`bash_tool.py`)

### Running Tests

Install development dependencies (including test tools):

```bash
pip install -e ".[dev]"
```

Run all tests:

```bash
pytest tests/
```

Run tests with coverage report:

```bash
pytest --cov=tools tests/
```

See [TESTING.md](TESTING.md) for detailed documentation on the test suite.

## License

[MIT](LICENSE.md)

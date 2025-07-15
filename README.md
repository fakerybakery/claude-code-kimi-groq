# Use Kimi K2 with Claude Code on Groq

Use Kimi K2 model through Groq API with Claude Code. Drop-in replacement for `claude` command.

## Changelog

* **v0.1.0**: Converted from a simple Proxy script to a library. The original proxy script is available in the [`simple-proxy`](https://github.com/fakerybakery/claude-code-kimi-groq/tree/simple-proxy) branch but will no longer be maintained.

## Installation

If you don't already have Claude Code installed, you can install it with:

```
npm install -g @anthropic-ai/claude-code
```

Then install the package:

```bash
pip install cckimi
# or:
# pip install "cckimi @ git+https://github.com/fakerybakery/claude-code-kimi-groq"
```

## Quick Start

Get a free Groq API key from [Groq](https://console.groq.com/keys).

```bash
# Store your Groq API key
cckimi login

# Use `kimi` instead of `claude`
kimi
kimi "write a hello world program"
```

## If you use this

If you use this, I'd love to hear about your experience with Kimi K2 and how it compared with Claude! Please open an Issue to share your experience.

## Acknowledgements

Inspired by [claude-code-proxy](https://github.com/1rgs/claude-code-proxy).

## License

MIT

Disclaimer: Not affiliated with Groq or Moonshot AI.
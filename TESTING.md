# Testing Documentation

This document outlines the testing approach for the Claude Code Kimi Groq proxy and its components, with a focus on security-critical aspects.

## Overview

The test suite focuses on verifying the security and functionality of core components:

1. **Path Utilities** - Tests for path sanitization and validation functions
2. **Virtual File System (VFS)** - Tests for secure file and directory operations
3. **BashTool** - Tests for secure command execution and sandboxing
4. **Integration** - Tests for component interaction

## Test Structure

Tests are organized by component in the `tests/` directory:

```
tests/
├── conftest.py         # Common test fixtures
├── test_utils.py       # Tests for utility functions
├── test_vfs.py         # Tests for Virtual File System
├── test_bash_tool.py   # Tests for BashTool
└── test_integration.py # Integration tests (future)
```

## Running Tests

To run the tests, you need pytest installed:

```bash
pip install pytest
```

Run all tests:

```bash
pytest tests/
```

Run tests for a specific component:

```bash
pytest tests/test_vfs.py
```

Run tests with verbose output:

```bash
pytest -v tests/
```

## Test Coverage

### Path Utilities (`utils.py`)

- **`sanitize_path`** - Tests path normalization and security checks
  - Normal relative paths
  - Absolute paths within base directory
  - Path traversal attempts (`../../../etc/passwd`)
  - Malformed paths
  - Edge cases (empty string, current directory)

- **`validate_file_path`** - Tests file path validation
  - Existing files
  - Non-existent files
  - Directory paths when file expected
  - Paths outside base directory

- **`validate_directory_path`** - Tests directory path validation
  - Existing directories
  - Non-existent directories
  - File paths when directory expected
  - Paths outside base directory

### Virtual File System (`vfs.py`)

- **Initialization** - Tests VFS initialization
  - String paths
  - Path objects

- **`get_cwd`** - Tests getting current working directory

- **`change_directory`** - Tests directory navigation
  - Subdirectories
  - Parent directory
  - Current directory
  - Absolute paths
  - Directory traversal attempts
  - Non-existent directories
  - File paths when directory expected

- **`list_directory`** - Tests directory listing
  - Current directory
  - Specific directory
  - Absolute paths
  - Non-existent directories
  - File paths when directory expected
  - Paths outside base directory

- **`make_directory`** - Tests directory creation
  - Simple directories
  - Nested directories with parents
  - Nested directories without parents
  - Existing directories
  - Paths outside base directory

- **`read_file`** - Tests file reading
  - Existing files
  - Nested files
  - Absolute paths
  - Non-existent files
  - Directory paths when file expected
  - Paths outside base directory

- **`write_file`** - Tests file writing
  - New files
  - Overwriting existing files
  - Nested paths
  - Absolute paths
  - Paths outside base directory
  - Directory paths when file expected

### BashTool (`bash_tool.py`)

- **`CommandSandbox`** - Tests resource limiting
  - Default limits
  - Custom limits

- **Initialization** - Tests BashTool initialization
  - Command handlers
  - VFS integration

- **Rate Limiting** - Tests command execution rate limiting
  - Normal usage
  - Rate limit exceeded

- **Security Patterns** - Tests dangerous pattern detection
  - Command substitution
  - Backtick substitution
  - Output redirection
  - Input redirection
  - Pipes
  - Background execution
  - Eval, exec, source commands

- **Command Parsing** - Tests command parsing and execution
  - Simple commands
  - Commands with arguments
  - Unsupported commands
  - Disallowed arguments
  - Command chaining (allowed and disallowed)

- **Command Handlers** - Tests individual command handlers
  - `pwd` - Current directory
  - `cd` - Directory navigation
  - `mkdir` - Directory creation
  - `ls` - Directory listing

- **Integration** - Tests command sequences and state maintenance
  - Multiple commands in sequence
  - Directory state persistence

## Security-Focused Testing

The test suite emphasizes security aspects:

1. **Path Traversal Prevention** - Tests that attempts to access files/directories outside the allowed base directory are blocked
2. **Command Injection Prevention** - Tests that dangerous shell patterns are detected and blocked
3. **Resource Limiting** - Tests that resource limits are enforced
4. **Rate Limiting** - Tests that command execution is rate-limited
5. **Argument Validation** - Tests that disallowed arguments are blocked

## Future Test Enhancements

1. **Proxy Integration Tests** - Test the proxy's handling of tool calls
2. **CLI Argument Tests** - Test command-line argument parsing
3. **Fuzzing Tests** - Test with randomly generated inputs to find edge cases
4. **Performance Tests** - Test under load conditions
5. **Security Penetration Tests** - Comprehensive tests of security boundaries

## Test Fixtures

The test suite uses pytest fixtures to set up test environments:

- `temp_vfs_dir` - Creates a temporary directory with test files and directories
- `vfs` - Creates a VirtualFileSystem instance for testing
- `bash_tool` - Creates a BashTool instance with VFS for testing

These fixtures are defined in `conftest.py` and are automatically available to all test modules.

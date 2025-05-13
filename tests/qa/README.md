# Arc Memory QA Tests

This directory contains Quality Assurance (QA) tests for the Arc Memory project. These tests are designed to verify the functionality of the package from an end-user perspective.

## Test Files

- **qa_test_installation.py**: Tests the installation and basic functionality of the package
- **qa_test_functionality.py**: Tests the core functionality of the package
- **qa_test_adapters.py**: Tests the framework adapters (LangChain, OpenAI)
- **qa_test_cli.py**: Tests the CLI commands
- **qa_test_ollama.py**: Tests the Ollama integration
- **qa_test_user_journey.py**: Tests the user journey through the package
- **qa_test_documentation.py**: Tests the documentation examples

## Running the Tests

To run a specific test, use:

```bash
python -m tests.qa.qa_test_installation
```

To run all tests, you can use:

```bash
for test in tests/qa/qa_test_*.py; do python -m ${test%.py} || echo "Test $test failed"; done
```

## Known Issues

There are some known issues with the tests that are being tracked in [Issue #65](https://github.com/Arc-Computer/arc-memory/issues/65).

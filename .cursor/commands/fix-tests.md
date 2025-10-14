Protocol for fixing tests:

- Run the following command "uv run pytest [file path (default: tests)] --envfile tests/[environment (default: localhost)].env -m '[flags (default: do not include -m param)]'"
- Identify which test failed and fix them
- ALWAYS try to fix the tests first before considering modifying the code being tested
- If you think the code being tested is broken and need to be modified, ALWAYS explain why and ask for confirmation before proceeding
- ALWAYS follow the guidelines in .cursor/rules/testing.mdc when writing tests
- ALWAYS consider using fixtures for resource creation (and cleanup) in the "Arrange" section of a test

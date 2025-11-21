# Contributing to OpenMod

Thank you for your interest in contributing to OpenMod! We welcome contributions from everyone, regardless of experience level. This document provides guidelines and information to help you contribute effectively.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- Python 3.8+
- Git
- Basic understanding of Discord bots and the discord.py library

### Setting up your development environment

1. Fork the repository on GitHub
2. Clone your fork:
```bash
git clone https://github.com/your-username/openmod.git
cd openmod
```

3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a configuration file:
```bash
cp config.example.py config.py
# Edit config.py with your development settings
```

## How to Contribute

### Reporting Bugs

- Use the issue tracker to report bugs
- Check if the issue already exists before creating a new one
- Provide detailed information about the bug, including steps to reproduce

### Suggesting Features

- Use the issue tracker for feature requests
- Explain the feature in detail and why it would be useful
- Consider the project's core philosophy and privacy-focused approach

### Contributing Code

1. Find an issue to work on or propose a new feature
2. Fork the repository and create a new branch:
```bash
git checkout -b feature/your-feature-name
```

3. Make your changes following the coding standards
4. Write tests for your changes if applicable
5. Update documentation as needed
6. Commit your changes with clear, descriptive commit messages
7. Push your branch to your fork
8. Create a pull request to the main repository

## Development Guidelines

### Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return types
- Write docstrings for all functions, classes, and modules
- Keep functions focused and avoid excessive complexity
- Use meaningful variable and function names

### Security & Privacy

- Never store unnecessary user data
- Implement proper input validation
- Follow security best practices
- Ensure all data handling is transparent and documented
- Respect user privacy at all times

### Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting a pull request
- Test edge cases and error conditions
- Consider performance implications of your changes

### Documentation

- Update README.md if you add new features
- Add docstrings to all public functions and classes
- Update the documentation in the `/docs` directory as needed

## Project Structure

```
openmod/
├── core/           # Core bot functionality, event handlers
├── modules/        # Feature modules (moderation, utility, logging, etc.)
├── database/       # Database models, connection management
├── utils/          # Helper functions, constants, validation tools
├── web/            # Web dashboard components
├── tests/          # Unit and integration tests
├── docs/           # Documentation files
├── config/         # Configuration templates and examples
├── main.py         # Main bot entry point
├── requirements.txt # Python dependencies
└── README.md       # Project documentation
```

## Pull Request Process

1. Ensure your code follows the project's coding standards
2. Add tests if applicable
3. Update documentation as needed
4. Ensure all tests pass
5. Describe your changes in the pull request description
6. Link any related issues
7. Wait for review and address feedback

## Questions?

If you have any questions about contributing, feel free to open an issue or contact the maintainers.

Thank you for contributing to OpenMod!
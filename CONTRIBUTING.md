# Contributing to Universal Personal Cloud Platform (USPC)

Thank you for your interest in contributing to USPC! This project is 100% free and open-source under the GNU Affero General Public License v3.0 (AGPL-3.0).

## Code of Conduct

All contributors and participants are expected to uphold a welcoming, respectful, and harassment-free environment for everyone.

## Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/uspc.git
   cd uspc
   ```

2. **Environment Setup**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Running Tests**:
   ```bash
   make test
   make coverage
   ```

4. **Code Quality and Linting**:
   ```bash
   make lint
   make format
   ```

## Development Rules & Principles

- **Zero Vendor Lock-in**: All components must be 100% free/open-source software (FOSS). Do not introduce proprietary SaaS dependencies.
- **No Secrets in Git**: Never commit tokens, passwords, private keys, or credentials.
- **Test Coverage**: We enforce >90% test coverage with 100% test pass rates across all PRs.
- **No Mocked Test Cheating**: Tests must execute real logic; do not return hardcoded dummy values.
- **Cross-Platform**: Code must support Linux natively and Windows/macOS via virtualization/Podman. Avoid OS-specific hardcoded paths.
- **Security-First**: Validate all inputs, sanitize file paths against traversal, enforce least privilege.

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Ensure all tests pass: `pytest --cov=src`
3. Commit with conventional commit messages: `feat(media): support mkv container streaming`
4. Open a Pull Request describing the changes, testing evidence, and affected platforms.

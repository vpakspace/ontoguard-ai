# 🤝 Contributing to OntoGuard

**Welcome! We're excited to have you here!** 🎉

Thank you for considering contributing to OntoGuard. Your contributions help make AI agents safer and more reliable in production environments. Every contribution, no matter how small, makes a difference.

## 🎯 Our Mission

OntoGuard's mission is to **prevent costly AI agent mistakes** by providing semantic validation through OWL ontologies. We believe that:

- AI agents should be safe and reliable in production
- Business rules should be enforceable and machine-readable
- Open source tools should be accessible to everyone
- Community contributions make software better

**Your contributions help us achieve this mission.** Whether you're fixing bugs, adding features, improving documentation, or helping others—you're making AI safer for everyone.

---

## 🌟 Ways to Contribute

There are many ways to contribute to OntoGuard, and not all of them require coding!

### 🐛 Report Bugs

Found a bug? Help us fix it!

1. **Search existing issues** to see if it's already reported
2. **Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)** to create a new issue
3. Include:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment details (OS, Python version, etc.)

**Good bug reports save everyone time!** 🕐

### 💡 Suggest Features

Have an idea? We'd love to hear it!

1. **Check existing [Feature Requests](https://github.com/cloudbadal007/ontoguard-ai/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)**
2. **Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)**
3. Include:
   - The problem it solves
   - Your proposed solution
   - Use cases and examples
   - Alternatives you've considered

**Great ideas come from the community!** 💭

### 📚 Improve Documentation

Documentation is just as important as code!

- Fix typos or unclear explanations
- Add missing examples
- Improve code comments
- Write tutorials or guides
- Translate documentation (if you speak multiple languages)

**Better docs = more users = better software!** 📖

### 🏗️ Add Example Ontologies

Help others get started faster!

- Create industry-specific ontologies (retail, logistics, etc.)
- Add more business rule examples
- Create template ontologies
- Document ontology design patterns

**Examples help people understand best practices!** 🎨

### 🔌 Framework Integrations

Integrate OntoGuard with more AI frameworks!

- Add support for new frameworks (BabyAGI, Semantic Kernel, etc.)
- Improve existing integrations
- Create integration examples
- Write integration guides

**More integrations = more users!** 🔗

### ✍️ Write Tutorials & Blog Posts

Share your knowledge!

- Write Medium articles about OntoGuard
- Create video tutorials
- Share use cases and case studies
- Write "How I used OntoGuard" posts

**Teaching others helps the whole community!** 🎓

### 💬 Answer Questions

Help others in the community!

- Answer questions in [GitHub Discussions](https://github.com/cloudbadal007/ontoguard-ai/discussions)
- Help troubleshoot issues
- Share your experiences
- Guide newcomers

**Your experience helps others succeed!** 🤝

### 💻 Write Code

Ready to code? Great!

- Fix bugs
- Implement features
- Improve test coverage
- Refactor for better code quality
- Optimize performance

**Code contributions are always welcome!** 💻

---

## 🆕 First-Time Contributors

**New to open source? No problem!** We're here to help you get started.

### Good First Issues

Look for issues labeled [`good first issue`](https://github.com/cloudbadal007/ontoguard-ai/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22). These are specifically chosen to be:
- Well-documented
- Small in scope
- Good learning opportunities
- Perfect for first-time contributors

### Simple Contribution Ideas

Not sure where to start? Try these:

1. **Fix a typo** in the README or documentation
2. **Add a test case** for an existing feature
3. **Improve a docstring** to be clearer
4. **Add an example** to the examples folder
5. **Answer a question** in Discussions

**Every contribution matters, no matter how small!** 🌱

### Mentorship Available

- **Questions?** Open a [GitHub Discussion](https://github.com/cloudbadal007/ontoguard-ai/discussions) with the `question` label
- **Stuck on code?** Ask in the PR comments—we're happy to help
- **Need guidance?** Tag maintainers in issues or discussions

**We're here to help you succeed!** 🎯

---

## 🛠️ Development Setup

Ready to start coding? Let's get your environment set up!

### Prerequisites

- **Python 3.9+** (3.9, 3.10, 3.11, or 3.12)
- **Git** for version control
- **A code editor** (VS Code, PyCharm, etc.)

### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/ontoguard-ai.git
cd ontoguard-ai
```

### Step 2: Create a Virtual Environment

```bash
# Using venv (recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install in development mode with all dev dependencies
pip install -e ".[dev]"

# This installs:
# - Core dependencies (rdflib, pydantic, etc.)
# - Dev tools (pytest, black, ruff, mypy)
```

### Step 4: Verify Installation

```bash
# Run tests to make sure everything works
pytest tests/ -v

# You should see all tests passing ✅
```

### Step 5: Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Now hooks will run automatically before each commit
```

**That's it! You're ready to contribute.** 🚀

---

## 🧪 Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_validator.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src/ontoguard --cov-report=html

# Open htmlcov/index.html in your browser to see coverage report
```

### Run Tests for Specific Python Version

```bash
# If you have multiple Python versions
python3.11 -m pytest tests/ -v
```

**All tests must pass before submitting a PR!** ✅

---

## 📝 Code Style Guidelines

We use automated tools to maintain code quality. Don't worry—they're easy to use!

### Formatting with Black

```bash
# Format all code
black src tests

# Check without formatting
black --check src tests
```

**Black** automatically formats your code to match our style.

### Linting with Ruff

```bash
# Check for issues
ruff check src tests

# Auto-fix issues
ruff check --fix src tests
```

**Ruff** finds and fixes code quality issues.

### Type Checking with Mypy

```bash
# Check types
mypy src tests
```

**Mypy** ensures type safety.

### Import Sorting with isort

```bash
# Sort imports
isort src tests

# Check without sorting
isort --check src tests
```

**isort** organizes your imports.

### Quick Check Before Committing

```bash
# Run all checks at once
black src tests && ruff check src tests && mypy src tests && isort --check src tests
```

**Or use pre-commit hooks** (they run automatically!)

---

## 🔄 Pull Request Process

Ready to submit your contribution? Follow these steps:

### Step 1: Fork the Repository

1. Click "Fork" on the [OntoGuard repository](https://github.com/cloudbadal007/ontoguard-ai)
2. Clone your fork locally

### Step 2: Create a Branch

```bash
# Create a new branch from main
git checkout -b feature/your-feature-name

# Or for bug fixes:
git checkout -b fix/bug-description
```

**Use descriptive branch names!** Examples:
- `feature/add-healthcare-ontology`
- `fix/validator-caching-issue`
- `docs/improve-quick-start`

### Step 3: Make Your Changes

- Write your code
- Add tests (if applicable)
- Update documentation
- Follow code style guidelines

### Step 4: Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "feat: add healthcare ontology example"

# Good commit messages follow this format:
# type: description
# 
# Types: feat, fix, docs, test, refactor, style, chore
```

**Commit message format:**
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `test:` for tests
- `refactor:` for code refactoring
- `style:` for formatting
- `chore:` for maintenance

### Step 5: Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### Step 6: Create a Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your branch
4. Fill out the PR template:
   - **Description**: What does this PR do?
   - **Related Issues**: Link to any related issues
   - **Testing**: How did you test this?
   - **Checklist**: Complete all applicable items

### Pull Request Checklist

Before submitting, make sure:

- [ ] **Tests pass** - All existing and new tests pass
- [ ] **Code formatted** - Black, isort, and ruff checks pass
- [ ] **Type checking** - Mypy passes (if applicable)
- [ ] **Documentation updated** - README, docstrings, or docs updated
- [ ] **No merge conflicts** - Branch is up to date with main
- [ ] **Descriptive title** - Clear what the PR does
- [ ] **Linked issues** - Related issues are linked
- [ ] **Self-reviewed** - You've reviewed your own code

### Review Process

1. **Automated checks** run (tests, linting, etc.)
2. **Maintainers review** your code
3. **Feedback provided** - We may request changes
4. **Approval** - Once approved, we'll merge!

**Don't worry if we request changes—it's part of the process!** We're here to help. 💪

---

## 📋 Code of Conduct

### Our Commitment

We are committed to providing a welcoming and inclusive environment for all contributors. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

### Expected Behavior

- ✅ Be respectful and inclusive
- ✅ Welcome newcomers and help them learn
- ✅ Give constructive feedback
- ✅ Focus on what's best for the community

### Unacceptable Behavior

- ❌ Harassment or discrimination
- ❌ Trolling or personal attacks
- ❌ Publishing others' private information
- ❌ Any unprofessional conduct

### Reporting Issues

If you experience or witness unacceptable behavior:

- **Email**: badal.aiworld@gmail.com
- **GitHub**: Open a private issue or discussion
- All reports will be reviewed and handled confidentially

**We take the Code of Conduct seriously.** 🛡️

---

## 🏆 Recognition

### Contributors List

All contributors are recognized in:
- **README.md** - Contributors section
- **Release notes** - For significant contributions
- **GitHub Contributors** - Automatic GitHub recognition

### Special Recognition

- **Significant contributions** get special thanks in release notes
- **Major features** get co-author credit
- **Documentation improvements** are highlighted
- **Community help** is always appreciated

### Path to Maintainer

Interested in becoming a maintainer? Here's the path:

1. **Consistent contributions** - Regular, quality contributions
2. **Community engagement** - Help others, answer questions
3. **Code quality** - Write clean, tested, documented code
4. **Project understanding** - Deep understanding of OntoGuard
5. **Maintainer invitation** - Invited by current maintainers

**Maintainers help shape the future of OntoGuard!** 🌟

---

## ❓ Questions?

### Need Help?

- **GitHub Discussions** - [Ask questions here: Discussions](https://github.com/cloudbadal007/ontoguard-ai/discussions)
- **Issues** - [Open an issue](https://github.com/cloudbadal007/ontoguard-ai/issues/new) for bugs or features
- **Email** - badal.aiworld@gmail.com

### Common Questions

**Q: Do I need to be an expert to contribute?**  
A: No! We welcome contributors of all skill levels. There are many ways to contribute beyond coding.

**Q: How do I know if my contribution is good enough?**  
A: If it follows our guidelines and helps the project, it's good enough! We're here to help you improve.

**Q: What if I make a mistake?**  
A: That's okay! We all make mistakes. We'll help you fix it and learn from it.

**Q: How long does a PR review take?**  
A: Usually 1-3 business days. For urgent fixes, tag maintainers.

**Q: Can I work on multiple issues at once?**  
A: Yes! Just create separate branches and PRs for each.

**Don't hesitate to ask questions!** We're here to help. 🤝

---

## 🎉 Thank You!

**Thank you for contributing to OntoGuard!**

Every contribution, whether it's:
- A single line of code
- A bug report
- A documentation improvement
- A helpful answer in discussions
- A star on GitHub

**...makes OntoGuard better for everyone.**

**Together, we're building a safer future for AI in production.** 🛡️

---

## 📚 Additional Resources

- [README.md](README.md) - Project overview
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community guidelines
- [CHANGELOG.md](CHANGELOG.md) - Project history
- [Examples](examples/) - Usage examples
- [Documentation](docs/) - Detailed documentation

---

**Ready to contribute?** [Find a good first issue](https://github.com/cloudbadal007/ontoguard-ai/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22) or [start a discussion](https://github.com/cloudbadal007/ontoguard-ai/discussions)! 🚀

*Last updated: January 2026*

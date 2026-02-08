# Contributing to AvatarAI

First off, thank you for considering contributing to AvatarAI! It's people like you that make things up and running.

## 🤝 How to Contribute

### 1. Reporting Bugs
If you find a bug, please create a new [Issue](https://github.com/mekinus/AvatarAI/issues) describing:
- What happened.
- What you expected to happen.
- Steps to reproduce the issue.
- Screenshots or logs if possible.

### 2. Suggesting Enhancements
Open an **Issue** with the tag `enhancement` to discuss your idea before writing any code. This saves you time ensuring your feature fits the project goals.

### 3. Pull Requests (Code Contributions)
We follow the standard [GitHub Flow](https://guides.github.com/introduction/flow/):

1. **Fork** the repository to your own GitHub account.
2. **Clone** the project to your machine.
3. Create a new **branch** for your feature:
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. **Make your changes** and test them.
5. **Commit** your changes with meaningful messages:
   ```bash
   git commit -m "feat: add new voice command for jump"
   ```
   *(We prefer [Conventional Commits](https://www.conventionalcommits.org/) format)*
6. **Push** to your branch:
   ```bash
   git push origin feature/amazing-feature
   ```
7. Open a **Pull Request** on our repository targeting the `main` branch.

---

## 💻 Coding Guidelines

### Python (Backend)
- Follow **PEP 8** style guide.
- Use meaningful variable names.
- Keep the architecture modular (Chat Layer → Brain Layer → Planner Layer).
- Ensure requirements are updated in `requirements.txt` if you add libraries.

### Unity (Frontend)
- Use **C#** naming conventions (PascalCase for methods/public fields, camelCase for arguments).
- Serialize fields with `[SerializeField] private` instead of public variables where possible.
- Avoid large prefabs commits if possible (they are hard to merge).

### General
- **No Secrets:** NEVER commit API keys or tokens.
- **No Piracy:** NEVER commit ROM files.

---

## 🧪 Testing

Before submitting a PR, please verify:
1. The Python backend starts without errors.
2. Unity connects successfully to the backend.
3. The new feature works as intended and doesn't break existing gameplay/chat.

Thank you for your help! 🚀

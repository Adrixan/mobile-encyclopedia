# Agentic Coding Template

A GitHub starter template pre-configured for AI-assisted and autonomous agentic coding, using [copilot-instructions](https://github.com/Adrixan/copilot-instructions) integrated as a Git submodule and linked according to **Method 2** from the upstream instructions.

## 🚀 Overview

This template provides unified configuration and domain-specific rules across multiple AI coding agents:
- **GitHub Copilot**: Reads `.github/copilot-instructions.md` and `.github/instructions/`
- **Antigravity Agent**: Reads `ANTIGRAVITY.md` and `instructions/`
- **Gemini CLI**: Reads `GEMINI.md` and `instructions/`

All instruction files and orchestrators are maintained in the [`copilot-instructions`](https://github.com/Adrixan/copilot-instructions) submodule at `.github/copilot-instructions` and exposed via relative symbolic links.

---

## 📦 How to Use This Template

### 1. Create a New Repository from this Template

#### Via GitHub CLI:
```bash
gh repo create my-new-project --template Adrixan/agentic-template --public --clone
cd my-new-project
```

#### Via GitHub Web UI:
Click the **"Use this template"** button at the top of the repository and choose **"Create a new repository"**.

---

### 2. Initialize Submodules

When cloning or initializing your new repository, make sure the submodule is fetched:

```bash
# If cloning fresh:
git clone --recurse-submodules <YOUR_REPO_URL>

# Or inside an existing checkout:
git submodule update --init --recursive
```

> **Note for Windows Users**: Ensure Developer Mode is enabled and configure Git to preserve symbolic links:
> ```bash
> git config core.symlinks true
> ```

---

## 🔄 Updating AI Instructions

To pull the latest behavioral rules, security guidelines, and technology updates from upstream:

```bash
git submodule update --remote --merge
```

---

## 📁 Repository Layout

```text
.
├── .github/
│   ├── copilot-instructions/       # Git submodule (https://github.com/Adrixan/copilot-instructions)
│   ├── copilot-instructions.md     # Symlink -> copilot-instructions/copilot-instructions.md
│   └── instructions/               # Symlink -> copilot-instructions/instructions
├── ANTIGRAVITY.md                  # Symlink -> .github/copilot-instructions/ANTIGRAVITY.md
├── GEMINI.md                       # Symlink -> .github/copilot-instructions/GEMINI.md
├── instructions/                   # Symlink -> .github/copilot-instructions/instructions
├── .gitmodules                     # Submodule configuration
└── README.md
```

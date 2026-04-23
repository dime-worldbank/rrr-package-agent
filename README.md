# Reproducibility Package Reviewer Agent

This open-source agent skill package follows the standard described here: <https://agentskills.io/home>.

## Where to run this agent?

This open-source agent skill package can be run in any environment that supports AI agents. The default environment described in this README is VS Code extensions such as GitHub Copilot or Claude Code.

For instructions in other environments, see: TODO

## Getting Started - VS Code

### Prerequisites

- Git installed
- VS Code installed
- An AI agent extension installed (e.g., GitHub Copilot, Claude Code)
- A license for the AI agent extension

### Clone the Repository

You may clone this repository using any Git client of your choice - such as GitHub Desktop or GitKraken. If using Git from the command line, you can use the following commands:

```bash
git clone https://github.com/dime-worldbank/rrr-package-agent.git
cd rrr-package-agent
```

### Add a package to review

Add the package you want to review to the `./package/` folder. This is the only folder you need to modify.

### Run the workflow

Run the slash command `/review-completeness` in your agent's chat interface. Review the output in the chat interface to see the results of the review. You can also see this output in the `./report/` folder.


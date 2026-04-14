# mcp-py-venus-step

An **MCP Server** designed to expose **Hamilton Liquid Handling** robotic operations as tools for Large Language Models (LLMs). This project allows AI agents to orchestrate laboratory workflows by executing discrete, modular "steps" via the `py-venus-step` interface.

## 📖 Overview

`mcp-py-venus-step` provides a standardized interface for LLMs to interact with Hamilton STAR, STARlet, or VANTAGE systems. By leveraging the **Model Context Protocol (MCP)**, it transforms complex robotic commands into "tools" that an AI can understand and call.

Instead of manually writing complex scripts for every variation of a protocol, an LLM can now:
* **Execute discrete actions** like aspirating, dispensing, or tip handling on demand.
* **Monitor robot state** and deck layout in real-time during a run.
* **Orchestrate protocols** by dynamically chaining steps based on experimental data, observations, or natural language instructions.

## 🛠️ Tech Stack

* **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/):** The core communication layer connecting the LLM (e.g., Claude, local agents) to the robotic tools.
* **[py-venus-step](https://github.com/BirdBare/py-venus-step):** The underlying library used to interface with the Hamilton Venus software.
* **[FastMCP](https://gofastmcp.com/getting-started/welcome):** Used to build the tools, clients, and resources.
* **[Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview):** Built with managed agents in mind. Reducing context overhead to allow extremelly robust execution and error handling.
## ✨ Features

* **Modular Step Execution:** Exposes core liquid handling primitives (Aspiration, Dispense, Tip Pick-up, Tip Eject) as discoverable MCP tools.
* **Error Translation:** Maps low-level robotic hardware errors into descriptive feedback, allowing the AI to suggest corrections or pause for intervention.
* **Deck Awareness:** Provides the AI with a digital twin representation of the deck, including labware positions and volume tracking.
* **Asynchronous Orchestration:** Designed to handle the timing requirements of robotic hardware while maintaining a responsive connection to the LLM client.
"""

# HK Flood Swarm

A Python LLM-agent flood prediction swarm for Hong Kong. This system utilizes a swarm of specialized agents to analyze real-time weather data from the Hong Kong Observatory (HKO) and predict flood risks with high transparency and reasoning.

## Overview

Traditional ML flood models often struggle with novel compound events and lack explainability. This swarm architecture addresses these issues by:
- **Reasoning from first principles:** Agents analyze data contextually rather than relying solely on historical patterns.
- **Explainable AI:** Every prediction includes a full "chain of thought" narrative in both English and Traditional Chinese.
- **Compound Event Detection:** A dedicated agent identifies dangerous co-occurrences (e.g., heavy rain during peak high tide) that single-point models might miss.

## Key Features

- **Multi-Agent Swarm:** Specialized agents for Rainfall, Tide, Warnings, Forecast, and Lightning.
- **Compound Risk Detection:** Specialized logic to identify complex risk scenarios.
- **Bilingual Output:** Automatically generates narratives in English and Traditional Chinese.
- **FastAPI Backend:** Modern, asynchronous API for running alerts and retrieving history.
- **Interactive Dashboard:** A frontend to visualize current risks and agent signals.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key (or compatible LLM provider)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd FloodHKAgent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

### Configuration

Create a `.env` file in the root directory and configure your environment variables. See `app/settings.py` for all available options.

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_DEFAULT_MODEL=gpt-4o  # Recommended for synthesis
FLOOD_SWARM_LOG_DIR=logs
```

## Running the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.
- **Dashboard:** `http://127.0.0.1:8000/`
- **API Documentation:** `http://127.0.0.1:8000/docs`

## Running Tests

Run the test suite using `pytest`:

```bash
pytest
```

## Project Structure

- `app/`: Source code
  - `agents/`: Individual specialist agents and the orchestrator.
  - `interfaces/`: API endpoints and frontend integration.
  - `models/`: Pydantic schemas for data validation.
  - `services/`: Core logic (LLM runtime, HKO client, logging).
- `tests/`: Unit and integration tests.
- `logs/`: Archive of run outputs in JSON format.
- `plan.md`: Detailed technical specification and architectural design.

## Technical Documentation

For a deep dive into the architecture, agent internals, and swarm coordination protocols, please refer to the [Technical Plan (plan.md)](plan.md).

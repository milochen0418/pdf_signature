# PDF Signature

PDF Signature is a lightweight web app for uploading PDF files, previewing pages, and adding signature overlays before saving the signed result. It focuses on a simple, guided flow so users can review a document, place a signature, and export the updated PDF in one place.

Key goals:
- Fast PDF preview and navigation
- Clear, minimal signing workflow
- Reliable export of the signed document

> Before making changes, read the project guidelines in [AGENTS.md](AGENTS.md).


## Getting Started

This project is managed with [Poetry](https://python-poetry.org/).

### Prerequisites

- Python 3.11.x
- Poetry


### Installation

1. Ensure Poetry uses Python 3.11:

```bash
poetry env use python3.11
poetry env info
```

2. Install dependencies:

```bash
poetry install
```

### Running the App

Start the development server:

```bash
poetry run ./reflex_rerun.sh
```

The application will be available at `http://localhost:3000`.


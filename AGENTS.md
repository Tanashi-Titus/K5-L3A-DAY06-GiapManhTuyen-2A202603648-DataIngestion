# Project execution policy

- For this repository, use only `D:\miniconda3\python.exe` (Miniconda base; Python 3.13.2).
- Do not create or activate virtual environments, and do not run scripts with another Python interpreter.
- Run package inspection, installation, app, ingestion, benchmark, and test commands with the explicit Miniconda interpreter. Install any necessary packages into that same Miniconda base only, after checking the existing versions and compatibility.
- Keep the user's API key in `starter/.env`; never print it or commit it.
- Do not remove Python environments outside this repository unless the user identifies their exact paths and asks for removal.

The automatically discoverable `miniconda-only` skill contains the same project-specific workflow.

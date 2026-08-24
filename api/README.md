InterviewOS API.

Run from this directory:

```
PYTHONPATH=src python3 -m uvicorn interviewos.http.app:app --reload --port 8000
PYTHONPATH=src python3 -m pytest tests -q
```

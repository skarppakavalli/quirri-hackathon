kit-voice-assistant/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   │
│   ├── agent/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   └── tools.py
│   │
│   ├── services/
│   │   ├── college_client.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── knowledge.py
│   │
│   ├── database/
│   │   ├── db.py
│   │   └── history.py
│   │
│   └── documents/
│       ├── handbook.pdf
│       ├── admission_brochure.pdf
│       └── lesson_notes.pdf
│
├── frontend/
│   └── app.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
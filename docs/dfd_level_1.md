# Level 1 Data Flow Diagram

```mermaid
flowchart TD
    P(("Player"))
    A(("Admin"))
    DB[("SQLite Database")]

    SD["Single-Device Play"]
    MD["Multi-Device Play"]
    SRA["Smart Role Assignment"]
    AI["AI Insights"]

    P -->|"player info, clues, votes"| SD
    P -->|"player info, clues, votes, join requests"| MD
    A -->|"settings"| DB

    SRA -->|"assigned roles"| SD
    SRA -->|"assigned roles"| MD
    AI -->|"word suggestions, tips, predictions"| SD
    AI -->|"word suggestions, tips, predictions"| MD

    SD -->|"game results"| DB
    MD -->|"game results"| DB
    DB -->|"game history"| SRA
    DB -->|"game history"| AI
```

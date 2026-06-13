```mermaid
graph TD
    P["Player"]:::entity
    AD["Admin / Settings"]:::entity

    subgraph SYS["Imposter Game System"]
        direction TB
        UI["Web Routes & Templates<br/>(Flask)"]
        GL["Game Logic<br/>(win check, round mgmt)"]
        MLA["ML Assignment<br/>(role assign, starter, grace)"]
        MLI["ML Insights<br/>(tips, predict, word stats)"]

        GL -->|"win check, player roles"| UI
        UI -->|"names, clues, votes"| GL
        MLA -->|"assigned roles + starter"| GL
        MLI -->|"tips, predictions, labels"| UI
    end

    DB[("SQLite Database<br/>(imposter.db)")]:::store

    UI -->|"game_id, session"| P
    P -->|"names, clues, votes"| UI

    AD -->|"smart_assign, defaults"| UI
    UI -->|"settings saved"| AD

    GL -->|"games, players, events":::flow --> DB
    DB -->|"finished games (winners)":::flow --> MLA
    DB -->|"finished games (winners)":::flow --> MLI

    S1["① Input sanitization<br/>validate_clue()"]:::sec
    S2["② Session token auth<br/>game_session_required"]:::sec
    S3["③ Param validation<br/>validate_positive_int()"]:::sec

    UI -.- S1
    UI -.- S2
    UI -.- S3

    classDef entity fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    classDef system fill:#fff3e0,stroke:#f57c00,stroke-width:2px,stroke-dasharray: 5 5
    classDef store fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef sec fill:#fce4ec,stroke:#c62828,stroke-width:1px
    classDef flow fill:none,stroke:#666
```

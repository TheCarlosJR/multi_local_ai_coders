                                +------------------+
                                |   VSCode / UI    |
                                +--------+---------+
                                         |
                                         |
                                       HTTP / Socket
                                         |
+--------------------+         +---------v---------+         +--------------------+
|   Memory & RAG     |<------->|   Orquestrador    |<------->|   Tools & APIs     |
|   (ChromaDB)       |         |    (Python)       |         |  - File System     |
+--------------------+         +---------+---------+         |  - Git / GitHub    |
                                         |                   |  - Terminal        |
                                         |                   |  - Browser/Web     |
                                  +------v--------+          +--------------------+
                                  |  Multi-Agents |
                                  | (AutoGen /    |
                                  |  LangChain)   |
                                  +---------------+

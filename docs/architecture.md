# Architecture Notes

## Current First Build

- Browser extension captures page text
- FastAPI receives and stores memory items in MongoDB when available
- React dashboard reads memory items through API
- Search, graph, and timeline use mock derived data

## Next Build Steps

1. Add MongoDB persistence
2. Add embeddings pipeline
3. Add vector search
4. Add Neo4j graph relationships
5. Add auth and user-specific memory spaces

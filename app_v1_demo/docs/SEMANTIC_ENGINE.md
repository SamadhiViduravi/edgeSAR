# Semantic engines — deferred

No Llama or rule semantic engine is loaded in Phase 1. Future engines consume fixed structured observations and propose validated mission-level tasks. They must not produce flight commands or raw waypoints. Text-only models do not view images; perception is a separate adapter. There is no silent mocked-model fallback.

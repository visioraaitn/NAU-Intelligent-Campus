__all__ = ["ChatOrchestrator"]


def __getattr__(name: str):
    # Linguistic helpers are also imported by academic services. Importing a
    # helper must not eagerly import the orchestrator back into those services.
    if name == "ChatOrchestrator":
        from app.services.dialogue.orchestrator import ChatOrchestrator
        return ChatOrchestrator
    raise AttributeError(name)

from .models import Conversation


def get_user_conversation(user, conversation_id):
    """Return a conversation only when the authenticated user participates."""
    if not user.is_authenticated:
        return None
    return Conversation.objects.filter(
        id=conversation_id,
        participants=user,
    ).first()

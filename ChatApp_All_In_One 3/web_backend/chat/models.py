from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_profile')
    display_name = models.CharField(max_length=80, blank=True)
    about = models.CharField(max_length=160, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    last_seen = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)
    read_receipts = models.BooleanField(default=True)
    show_last_seen = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.display_name or self.user.get_username()

class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_made')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_received')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = [('blocker','blocked')]

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_conversations')
    title = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to='groups/', blank=True, null=True)
    is_group = models.BooleanField(default=False)
    admins = models.ManyToManyField(User, related_name='admin_chat_groups', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_chat_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ['-updated_at']
    def __str__(self): return self.title or f'Conversation {self.pk}'

class Message(models.Model):
    MESSAGE_TYPES = [('text','Text'),('image','Image'),('video','Video'),('file','File'),('audio','Audio'),('voice','Voice')]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_messages')
    content = models.TextField(max_length=5000, blank=True)
    attachment = models.FileField(upload_to='chat_uploads/%Y/%m/', blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    forwarded_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='forwards')
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_for_everyone = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    class Meta: ordering = ['created_at','id']
    def __str__(self): return f'Message {self.pk} in conversation {self.conversation_id}'

class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = [('message','user','emoji')]

class Status(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_statuses')
    text = models.CharField(max_length=700, blank=True)
    media = models.FileField(upload_to='statuses/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    viewers = models.ManyToManyField(User, related_name='viewed_chat_statuses', blank=True)
    class Meta: ordering = ['-created_at']
    @property
    def active(self): return self.expires_at > timezone.now()

class CallSignal(models.Model):
    CALL_TYPES = [('audio','Audio'),('video','Video')]
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_started')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_received')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    call_type = models.CharField(max_length=5, choices=CALL_TYPES)
    status = models.CharField(max_length=12, default='ringing')
    signal = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

class ChatPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_preferences')
    theme = models.CharField(max_length=10, default='light')
    font_size = models.CharField(max_length=10, default='medium')
    notifications_enabled = models.BooleanField(default=True)

class ConversationSetting(models.Model):
    """Per-user controls for an individual conversation."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_settings')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='user_settings')
    is_archived = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'conversation'], name='unique_user_conversation_setting')]

class HiddenMessage(models.Model):
    """A message hidden only from one user's view (delete for me)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_chat_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='hidden_for')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'message'], name='unique_hidden_message_per_user')]

class MessageReceipt(models.Model):
    STATUS_CHOICES = [('delivered', 'Delivered'), ('read', 'Read')]
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_receipts')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='delivered')
    delivered_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['message', 'user'], name='unique_message_receipt')]

class UserReport(models.Model):
    REPORT_TYPES = [('user', 'User'), ('message', 'Message'), ('group', 'Group')]
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_reports_made')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    reported_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_reports_received')
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=80)
    details = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)

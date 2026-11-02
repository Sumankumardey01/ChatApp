from django.contrib import admin
from .models import (Conversation, Message, Profile, Block, MessageReaction,
                     Status, CallSignal, ChatPreference, ConversationSetting, HiddenMessage, MessageReceipt, UserReport)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id','title','is_group','created_at','updated_at')
    list_filter = ('is_group','created_at')
    filter_horizontal = ('participants','admins')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id','conversation','sender','message_type','created_at','is_read')
    list_filter = ('message_type','is_read','created_at')
    search_fields = ('content','sender__username')

admin.site.register([Profile, Block, MessageReaction, Status, CallSignal, ChatPreference, ConversationSetting, HiddenMessage, MessageReceipt])

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ("id", "report_type", "reporter", "reported_user", "created_at", "is_reviewed")
    list_filter = ("report_type", "is_reviewed", "created_at")
    search_fields = ("reporter__username", "reported_user__username", "reason", "details")

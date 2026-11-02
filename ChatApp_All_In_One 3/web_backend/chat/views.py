from django.contrib import messages as django_messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .forms import RegisterForm, StartConversationForm
from .models import (
    Conversation,
    Message,
    GroupInvitation,
    Block,
)
from .models import Profile, MessageReaction, Status, CallSignal, ChatPreference
from .permissions import get_user_conversation


def home(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            django_messages.success(
                request,
                "Your account has been created successfully! You can log in now.",
            )
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "chat/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        next_url = request.POST.get("next", "")
        if form.is_valid():
            login(request, form.get_user())
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect("chat")
        django_messages.error(
            request, "Your username or password is incorrect. Please try again."
        )
    else:
        form = AuthenticationForm(request)
    return render(request, "chat/login.html", {"form": form, "next": next_url})


@login_required(login_url="login")
def chat_view(request):
    conversations = (
        Conversation.objects.filter(participants=request.user)
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
                distinct=True,
            )
        )
        .prefetch_related("participants", "messages")
        .distinct()
        .order_by("-updated_at")
    )
    for conversation in conversations:
        conversation.last_message = conversation.messages.order_by("-created_at", "-id").first()
    return render(request, "chat/chat.html", {
        "conversations": conversations,
        "start_conversation_form": StartConversationForm(),
    })


@login_required(login_url="login")
@require_POST
def start_conversation(request):
    form = StartConversationForm(request.POST)
    if not form.is_valid():
        for error_list in form.errors.values():
            django_messages.error(request, " ".join(error_list))
        return redirect("chat")

    recipient = User.objects.get(username__iexact=form.cleaned_data["username"])
    if Block.objects.filter(Q(blocker=request.user, blocked=recipient) | Q(blocker=recipient, blocked=request.user)).exists():
        django_messages.error(request, "This conversation is unavailable due to privacy settings.")
        return redirect("chat")
    if recipient.pk == request.user.pk:
        django_messages.error(request, "You cannot start a conversation with yourself.")
        return redirect("chat")

    existing = (
        Conversation.objects.filter(participants=request.user)
        .filter(participants=recipient)
        .distinct()
    )
    for conversation in existing:
        if conversation.participants.count() == 2:
            return redirect("chat")

    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, recipient)
    django_messages.success(request, f"Conversation started with {recipient.username}.")
    return redirect("chat")


@login_required(login_url="login")
@require_POST
def send_message(request, conversation_id):
    conversation = get_user_conversation(request.user, conversation_id)
    if conversation is None:
        return JsonResponse({"error": "Conversation not found."}, status=404)

    if not conversation.is_group:
        other = conversation.participants.exclude(pk=request.user.pk).first()
        if other and Block.objects.filter(Q(blocker=other, blocked=request.user) | Q(blocker=request.user, blocked=other)).exists():
            return JsonResponse({"error": "Messaging is unavailable due to privacy settings."}, status=403)

    content = request.POST.get("content", "").strip()
    if not content:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)
    if len(content) > 5000:
        return JsonResponse({"error": "Message is too long."}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
    )
    conversation.save(update_fields=["updated_at"])
    payload = {
        "id": message.id,
        "content": message.content,
        "sender": message.sender.username,
        "sender_id": message.sender_id,
        "created_at": message.created_at.isoformat(),
        "is_read": message.is_read,
    }
    # Broadcast immediately to every connected participant. HTTP polling remains
    # enabled in the browser as a resilient fallback if WebSockets are unavailable.
    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {"type": "chat.message", "message": payload},
            )
    except Exception:
        # A temporary channel-layer problem must not discard a saved message.
        pass
    return JsonResponse({
        **payload,
    }, status=201)


@login_required(login_url="login")
@require_GET
def conversation_messages(request, conversation_id):
    conversation = get_user_conversation(request.user, conversation_id)
    if conversation is None:
        return JsonResponse({"error": "Conversation not found."}, status=404)

    queryset = conversation.messages.select_related("sender").exclude(hidden_for__user=request.user).order_by("created_at", "id")
    after = request.GET.get("after")
    if after is not None:
        try:
            after_id = int(after)
            if after_id < 0:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid message cursor."}, status=400)
        queryset = queryset.filter(id__gt=after_id)

    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return JsonResponse({
        "conversation_id": conversation.id,
        "messages": [{
            "id": message.id,
            "content": message.content,
            "sender": message.sender.username,
            "sender_id": message.sender_id,
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
            "message_type": message.message_type,
            "attachment_url": message.attachment.url if message.attachment else "",
            "edited": bool(message.edited_at),
            "deleted": message.deleted_for_everyone,
            "reply_to_id": message.reply_to_id,
            "forwarded": bool(message.forwarded_from_id),
            "delivery": "read" if message.receipts.filter(status="read").exists() else ("delivered" if message.receipts.exists() else ("read" if message.is_read else "sent")),
            "reactions": list(message.reactions.values("emoji").annotate(count=Count("id"))),
        } for message in queryset],
    })


@login_required(login_url="login")
@require_GET
def sidebar_updates(request):
    conversations = (
        Conversation.objects.filter(participants=request.user)
        .annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
                distinct=True,
            )
        )
        .prefetch_related("participants")
        .distinct()
        .order_by("-updated_at")
    )
    results = []
    for conversation in conversations:
        other = conversation.participants.exclude(pk=request.user.pk).first()
        last_message = conversation.messages.order_by("-created_at", "-id").first()
        results.append({
            "id": conversation.id,
            "name": other.username if other else "Conversation",
            "preview": last_message.content[:35] if last_message else "No messages yet",
            "time": last_message.created_at.isoformat() if last_message else "",
            "unread_count": conversation.unread_count,
        })
    return JsonResponse({"conversations": results})

# Extended ChatApp endpoints: groups, media, message actions, profiles, status,
# privacy controls, preferences and WebRTC signalling records.
from datetime import timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from .models import Profile, Block, MessageReaction, Status, CallSignal, ChatPreference

@login_required
@require_POST
def create_group(request):
    name = request.POST.get('name','').strip()[:100]
    ids = request.POST.getlist('members')
    if not name:
        return JsonResponse({'error':'Group name is required.'}, status=400)
    members = list(User.objects.filter(id__in=ids))
    if len(members) < 1:
        return JsonResponse({'error':'Choose at least one other member.'}, status=400)
    if request.user not in members: members.append(request.user)
    group = Conversation.objects.create(title=name, description=request.POST.get('description','')[:300], is_group=True, created_by=request.user)
    group.participants.set(members); group.admins.add(request.user)
    return JsonResponse({'id':group.id,'name':group.title,'members':[u.username for u in members]}, status=201)

@login_required
@require_POST
def group_members(request, conversation_id):
    group = get_user_conversation(request.user, conversation_id)
    if not group or not group.is_group: return JsonResponse({'error':'Group not found.'}, status=404)
    if not group.admins.filter(pk=request.user.pk).exists(): return JsonResponse({'error':'Only admins can manage members.'}, status=403)
    action = request.POST.get('action'); user_id = request.POST.get('user_id')
    target = User.objects.filter(pk=user_id).first()
    if not target: return JsonResponse({'error':'User not found.'}, status=404)
    if action == 'add': group.participants.add(target)
    elif action == 'remove' and target.pk != request.user.pk: group.participants.remove(target); group.admins.remove(target)
    elif action == 'promote': group.admins.add(target)
    else: return JsonResponse({'error':'Unsupported member action.'}, status=400)
    return JsonResponse({'ok':True})

@login_required
@require_POST
def upload_message(request, conversation_id):
    conversation = get_user_conversation(request.user, conversation_id)
    uploaded = request.FILES.get('file')
    if not conversation: return JsonResponse({'error':'Conversation not found.'}, status=404)
    if not uploaded: return JsonResponse({'error':'Select a file.'}, status=400)
    if uploaded.size > 25 * 1024 * 1024: return JsonResponse({'error':'Maximum upload size is 25 MB.'}, status=400)
    mime = uploaded.content_type or ''
    if mime.startswith('image/'): kind='image'
    elif mime.startswith('video/'): kind='video'
    elif mime.startswith('audio/'): kind='audio'
    else: kind='file'
    message = Message.objects.create(conversation=conversation, sender=request.user, content=request.POST.get('content','')[:5000], attachment=uploaded, message_type=kind)
    conversation.save(update_fields=['updated_at'])
    return JsonResponse({'id':message.id,'type':kind,'file_url':message.attachment.url,'filename':uploaded.name,'sender':request.user.username,'created_at':message.created_at.isoformat()}, status=201)

@login_required
@require_POST
def message_action(request, message_id):
    message = Message.objects.filter(pk=message_id, conversation__participants=request.user).first()
    if not message: return JsonResponse({'error':'Message not found.'}, status=404)
    action = request.POST.get('action')
    if action == 'edit':
        if message.sender_id != request.user.id: return JsonResponse({'error':'You can only edit your own messages.'}, status=403)
        content=request.POST.get('content','').strip()
        if not content or len(content)>5000: return JsonResponse({'error':'Message must contain 1–5000 characters.'}, status=400)
        message.content=content; message.edited_at=timezone.now(); message.save(update_fields=['content','edited_at'])
    elif action == 'delete':
        if message.sender_id != request.user.id: return JsonResponse({'error':'You can only delete your own messages.'}, status=403)
        message.deleted_for_everyone=True; message.content=''; message.attachment=None; message.save(update_fields=['deleted_for_everyone','content','attachment'])
    elif action == 'react':
        emoji=request.POST.get('emoji','').strip()[:16]
        if not emoji: return JsonResponse({'error':'Emoji required.'}, status=400)
        reaction, created=MessageReaction.objects.get_or_create(message=message,user=request.user,emoji=emoji)
        if not created: reaction.delete()
    elif action == 'forward':
        target_id=request.POST.get('conversation_id')
        target=get_user_conversation(request.user,target_id) if str(target_id).isdigit() else None
        if not target: return JsonResponse({'error':'Target conversation not found.'}, status=404)
        Message.objects.create(conversation=target,sender=request.user,content=message.content,attachment=message.attachment,message_type=message.message_type,forwarded_from=message)
        target.save(update_fields=['updated_at'])
    else: return JsonResponse({'error':'Unsupported action.'}, status=400)
    return JsonResponse({'ok':True})

@login_required
@require_POST
def profile_update(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.display_name=request.POST.get('display_name','')[:80]
    profile.about=request.POST.get('about','')[:160]
    if request.FILES.get('avatar'): profile.avatar=request.FILES['avatar']
    profile.save()
    return JsonResponse({'ok':True,'display_name':profile.display_name,'about':profile.about,'avatar':profile.avatar.url if profile.avatar else ''})

@login_required
@require_GET
def user_search(request):
    q=request.GET.get('q','').strip()
    users=User.objects.filter(username__icontains=q).exclude(pk=request.user.pk)[:20] if q else User.objects.none()
    blocked=Block.objects.filter(blocker=request.user).values_list('blocked_id',flat=True)
    return JsonResponse({'users':[{'id':u.id,'username':u.username,'display_name':getattr(getattr(u,'chat_profile',None),'display_name','')} for u in users if u.id not in blocked]})

@login_required
@require_POST
def privacy_action(request):
    user_id=request.POST.get('user_id')
    target=User.objects.filter(pk=user_id).first()
    if not target or target.pk==request.user.pk: return JsonResponse({'error':'Invalid user.'},status=400)
    obj,created=Block.objects.get_or_create(blocker=request.user,blocked=target)
    if request.POST.get('action')=='unblock': obj.delete()
    elif request.POST.get('action')!='block': return JsonResponse({'error':'Invalid action.'},status=400)
    return JsonResponse({'ok':True})

@login_required
@require_POST
def status_create(request):
    text=request.POST.get('text','').strip()[:700]; media=request.FILES.get('media')
    if not text and not media: return JsonResponse({'error':'Add text or media.'},status=400)
    if media and media.size>25*1024*1024: return JsonResponse({'error':'Maximum upload size is 25 MB.'},status=400)
    status=Status.objects.create(user=request.user,text=text,media=media,expires_at=timezone.now()+timedelta(hours=24))
    return JsonResponse({'id':status.id,'expires_at':status.expires_at.isoformat()},status=201)

@login_required
@require_GET
def status_list(request):
    rows=Status.objects.filter(expires_at__gt=timezone.now()).exclude(user= request.user).select_related('user')
    return JsonResponse({'statuses':[{'id':s.id,'username':s.user.username,'text':s.text,'media_url':s.media.url if s.media else '', 'created_at':s.created_at.isoformat(),'view_count':s.viewers.count()} for s in rows]})

@login_required
@require_POST
def status_view(request,status_id):
    status=Status.objects.filter(pk=status_id,expires_at__gt=timezone.now()).first()
    if not status: return JsonResponse({'error':'Status not found.'},status=404)
    status.viewers.add(request.user)
    return JsonResponse({'ok':True})

@login_required
@require_POST
def preference_update(request):
    prefs,_=ChatPreference.objects.get_or_create(user=request.user)
    if 'theme' in request.POST and request.POST['theme'] in {'light','dark'}: prefs.theme=request.POST['theme']
    if 'font_size' in request.POST and request.POST['font_size'] in {'small','medium','large'}: prefs.font_size=request.POST['font_size']
    if 'notifications_enabled' in request.POST: prefs.notifications_enabled=request.POST['notifications_enabled'].lower() in {'1','true','yes'}
    prefs.save(); return JsonResponse({'ok':True})

@login_required
@require_POST
def call_signal(request, conversation_id):
    conversation=get_user_conversation(request.user,conversation_id)
    if not conversation: return JsonResponse({'error':'Conversation not found.'},status=404)
    import json
    try: data=json.loads(request.body or '{}')
    except json.JSONDecodeError: return JsonResponse({'error':'Invalid JSON.'},status=400)
    action=data.get('action'); call_id=data.get('call_id')
    if action=='start':
        recipient=User.objects.filter(pk=data.get('recipient_id')).first()
        if not recipient or recipient.pk==request.user.pk or not conversation.participants.filter(pk=recipient.pk).exists(): return JsonResponse({'error':'Invalid call recipient.'},status=400)
        call=CallSignal.objects.create(caller=request.user,recipient=recipient,conversation=conversation,call_type=data.get('call_type','audio') if data.get('call_type') in {'audio','video'} else 'audio',signal=data.get('signal',{}))
        return JsonResponse({'call_id':call.id,'status':call.status},status=201)
    call=CallSignal.objects.filter(pk=call_id,conversation=conversation).filter(Q(caller=request.user)|Q(recipient=request.user)).first()
    if not call: return JsonResponse({'error':'Call not found.'},status=404)
    if action=='signal': call.signal=data.get('signal',{}); call.save(update_fields=['signal'])
    elif action in {'accept','reject','end'}:
        call.status={'accept':'active','reject':'rejected','end':'ended'}[action]
        if action in {'reject','end'}: call.ended_at=timezone.now()
        call.save(update_fields=['status','ended_at'])
    else: return JsonResponse({'error':'Unsupported call action.'},status=400)
    return JsonResponse({'ok':True,'status':call.status})

# Additional essential account-level chat controls.
from .models import ConversationSetting, HiddenMessage, MessageReceipt, UserReport

@login_required
@require_POST
def conversation_settings(request, conversation_id):
    conversation = get_user_conversation(request.user, conversation_id)
    if not conversation:
        return JsonResponse({'error': 'Conversation not found.'}, status=404)
    setting, _ = ConversationSetting.objects.get_or_create(user=request.user, conversation=conversation)
    allowed = {'archive': 'is_archived', 'pin': 'is_pinned', 'mute': 'is_muted'}
    action = request.POST.get('action')
    field = allowed.get(action)
    if not field:
        return JsonResponse({'error': 'Use archive, pin or mute.'}, status=400)
    value = request.POST.get('value', 'true').lower() in {'1', 'true', 'yes', 'on'}
    setattr(setting, field, value)
    setting.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'action': action, 'value': value})

@login_required
@require_POST
def hide_message(request, message_id):
    message = Message.objects.filter(pk=message_id, conversation__participants=request.user).first()
    if not message:
        return JsonResponse({'error': 'Message not found.'}, status=404)
    HiddenMessage.objects.get_or_create(user=request.user, message=message)
    return JsonResponse({'ok': True})

@login_required
@require_POST
def mark_message_read(request, conversation_id):
    conversation = get_user_conversation(request.user, conversation_id)
    if not conversation:
        return JsonResponse({'error': 'Conversation not found.'}, status=404)
    ids = request.POST.getlist('message_ids')
    qs = conversation.messages.exclude(sender=request.user)
    if ids:
        qs = qs.filter(id__in=[int(x) for x in ids if str(x).isdigit()])
    now = timezone.now()
    messages_to_mark = list(qs.only('id', 'sender_id'))
    for msg in messages_to_mark:
        MessageReceipt.objects.update_or_create(
            message=msg, user=request.user,
            defaults={'status': 'read', 'read_at': now},
        )
    qs.update(is_read=True)
    return JsonResponse({'ok': True, 'marked_read': len(messages_to_mark)})

@login_required
@require_POST
def report_content(request):
    kind = request.POST.get('report_type', 'user')
    reason = request.POST.get('reason', '').strip()[:80]
    details = request.POST.get('details', '').strip()[:1000]
    if kind not in {'user', 'message', 'group'} or not reason:
        return JsonResponse({'error': 'Choose a valid report type and provide a reason.'}, status=400)
    report = UserReport(reporter=request.user, report_type=kind, reason=reason, details=details)
    if kind == 'user':
        target = User.objects.filter(pk=request.POST.get('user_id')).first()
        if not target or target.pk == request.user.pk:
            return JsonResponse({'error': 'Invalid user.'}, status=400)
        report.reported_user = target
    elif kind == 'message':
        msg = Message.objects.filter(pk=request.POST.get('message_id'), conversation__participants=request.user).first()
        if not msg:
            return JsonResponse({'error': 'Message not found.'}, status=404)
        report.message = msg
        report.reported_user = msg.sender
        report.conversation = msg.conversation
    else:
        group = get_user_conversation(request.user, request.POST.get('conversation_id'))
        if not group or not group.is_group:
            return JsonResponse({'error': 'Group not found.'}, status=404)
        report.conversation = group
    report.save()
    return JsonResponse({'ok': True, 'report_id': report.id}, status=201)

@login_required
@require_GET
def status_viewers(request, status_id):
    status = Status.objects.filter(pk=status_id, user=request.user).first()
    if not status:
        return JsonResponse({'error': 'Your status was not found.'}, status=404)
    viewers = status.viewers.values('id', 'username')
    return JsonResponse({'viewers': list(viewers), 'count': status.viewers.count()})

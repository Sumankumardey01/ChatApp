from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", __import__("django.contrib.auth.views", fromlist=["LogoutView"]).LogoutView.as_view(next_page="home"), name="logout"),
    path("chat/", views.chat_view, name="chat"),
    path("chat/start/", views.start_conversation, name="start_conversation"),
    path("chat/conversation/<int:conversation_id>/send/", views.send_message, name="send_message"),
    path("chat/conversation/<int:conversation_id>/messages/", views.conversation_messages, name="conversation_messages"),
    path("chat/api/sidebar-updates/", views.sidebar_updates, name="sidebar_updates"),
    path("api/users/search/", views.user_search, name="user_search"),
    path("api/profile/update/", views.profile_update, name="profile_update"),
    path("api/groups/create/", views.create_group, name="create_group"),
    path("api/groups/<int:conversation_id>/members/", views.group_members, name="group_members"),
    path("api/conversations/<int:conversation_id>/upload/", views.upload_message, name="upload_message"),
    path("api/messages/<int:message_id>/action/", views.message_action, name="message_action"),
    path("api/privacy/block/", views.privacy_action, name="privacy_action"),
    path("api/status/create/", views.status_create, name="status_create"),
    path("api/status/", views.status_list, name="status_list"),
    path("api/status/<int:status_id>/view/", views.status_view, name="status_view"),
    path("api/preferences/update/", views.preference_update, name="preference_update"),
    path("api/conversations/<int:conversation_id>/calls/", views.call_signal, name="call_signal"),
    path("api/conversations/<int:conversation_id>/settings/", views.conversation_settings, name="conversation_settings"),
    path("api/conversations/<int:conversation_id>/read/", views.mark_message_read, name="mark_message_read"),
    path("api/messages/<int:message_id>/hide/", views.hide_message, name="hide_message"),
    path("api/reports/create/", views.report_content, name="report_content"),
    path("api/status/<int:status_id>/viewers/", views.status_viewers, name="status_viewers"),
    path(
    "api/groups/<int:conversation_id>/invite/",
    views.send_group_invitation,
    name="send_group_invitation"
    ),
    path(
    "api/group-invitations/<int:invitation_id>/respond/",
    views.respond_group_invitation,
    name="respond_group_invitation"
    ),
]

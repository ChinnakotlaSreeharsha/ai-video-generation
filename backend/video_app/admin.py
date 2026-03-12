from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count
from .models import UserProfile, VideoGeneration, Avatar


# ─────────────────────────────────────────────
# Avatar Admin
# ─────────────────────────────────────────────

@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    list_display   = ("id", "name", "category", "is_active", "sort_order",
                      "preview_thumb", "video_link", "created_at")
    list_filter    = ("category", "is_active")
    search_fields  = ("name", "description")
    ordering       = ("sort_order", "name")
    list_editable  = ("is_active", "sort_order")
    readonly_fields = ("slug", "created_at", "updated_at", "preview_large")
    fieldsets = (
        ("Identity", {
            "fields": ("name", "slug", "category", "description", "is_active", "sort_order"),
        }),
        ("Media", {
            "fields": ("preview_image", "preview_large", "source_video"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def preview_thumb(self, obj):
        if obj.preview_url:
            return format_html(
                '<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;">',
                obj.preview_url,
            )
        return "—"
    preview_thumb.short_description = "Preview"

    def preview_large(self, obj):
        if obj.preview_url:
            return format_html(
                '<img src="{}" style="max-width:320px;border-radius:10px;">',
                obj.preview_url,
            )
        return "No image uploaded."
    preview_large.short_description = "Preview (full)"

    def video_link(self, obj):
        if obj.source_video:
            return format_html(
                '<a href="{}" target="_blank">▶ Play</a>',
                obj.source_video.url,
            )
        return "—"
    video_link.short_description = "Source Video"


# ─────────────────────────────────────────────
# Inline: show profile inside User admin
# ─────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model   = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields  = ("avatar", "bio", "default_language", "video_quality",
                "notify_video_done", "notify_errors", "notify_updates", "notify_marketing")
    readonly_fields = ("created_at", "updated_at") if hasattr(UserProfile, "created_at") else ()


# ─────────────────────────────────────────────
# Inline: show videos inside User admin
# ─────────────────────────────────────────────

class VideoGenerationInline(admin.TabularInline):
    model  = VideoGeneration
    extra  = 0
    can_delete = False
    show_change_link = True
    readonly_fields = ("created_at", "language", "status", "duration_s",
                       "avatar_display", "video_preview", "short_text_display")
    fields  = ("created_at", "language", "status", "duration_s",
               "avatar_display", "short_text_display", "video_preview")

    def video_preview(self, obj):
        if obj.video_url:
            return format_html('<a href="{}" target="_blank">▶ Play</a>', obj.video_url)
        return "—"
    video_preview.short_description = "Video"

    def short_text_display(self, obj):
        return obj.short_text
    short_text_display.short_description = "Script"

    def avatar_display(self, obj):
        if obj.avatar:
            thumb = obj.avatar.preview_url
            if thumb:
                return format_html(
                    '<img src="{}" style="width:32px;height:32px;object-fit:cover;border-radius:4px;"> {}',
                    thumb, obj.avatar.name,
                )
            return obj.avatar.name
        return obj.avatar_name or "—"
    avatar_display.short_description = "Avatar"


# ─────────────────────────────────────────────
# Extended User admin
# ─────────────────────────────────────────────

class UserAdmin(BaseUserAdmin):
    inlines      = (UserProfileInline, VideoGenerationInline)
    list_display = ("username", "email", "first_name", "last_name",
                    "is_active", "date_joined", "video_count")
    list_filter  = ("is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering     = ("-date_joined",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_video_count=Count("videos"))

    def video_count(self, obj):
        return obj._video_count
    video_count.short_description  = "Videos"
    video_count.admin_order_field  = "_video_count"


# ─────────────────────────────────────────────
# VideoGeneration standalone admin
# ─────────────────────────────────────────────

@admin.register(VideoGeneration)
class VideoGenerationAdmin(admin.ModelAdmin):
    list_display   = ("id", "user_link", "language", "status",
                      "duration_display", "avatar_display", "created_at", "video_link")
    list_filter    = ("status", "language", "avatar__category", "created_at")
    search_fields  = ("user__username", "user__email", "input_text", "avatar__name")
    ordering       = ("-created_at",)
    readonly_fields = ("user", "language", "input_text", "audio_file", "video_file",
                       "avatar", "avatar_name", "status", "duration_s", "created_at",
                       "video_preview_large")
    fields = ("user", "language", "status", "duration_s", "avatar", "avatar_name",
              "input_text", "audio_file", "video_file", "created_at", "video_preview_large")

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>',
            obj.user.id, obj.user.username
        )
    user_link.short_description = "User"
    user_link.admin_order_field = "user__username"

    def duration_display(self, obj):
        if obj.duration_s is not None:
            return f"{obj.duration_s:.1f}s"
        return "—"
    duration_display.short_description = "Duration"
    duration_display.admin_order_field = "duration_s"

    def avatar_display(self, obj):
        if obj.avatar:
            thumb = obj.avatar.preview_url
            if thumb:
                return format_html(
                    '<img src="{}" style="width:28px;height:28px;object-fit:cover;'
                    'border-radius:4px;vertical-align:middle;margin-right:6px;"> {}',
                    thumb, obj.avatar.name,
                )
            return obj.avatar.name
        return obj.avatar_name or "—"
    avatar_display.short_description = "Avatar"

    def video_link(self, obj):
        if obj.video_url:
            return format_html('<a href="{}" target="_blank">▶ Play</a>', obj.video_url)
        return "—"
    video_link.short_description = "Video"

    def video_preview_large(self, obj):
        if obj.video_url:
            return format_html(
                '<video width="480" controls style="border-radius:8px;">'
                '<source src="{}" type="video/mp4"></video>',
                obj.video_url
            )
        return "No video file."
    video_preview_large.short_description = "Preview"


# ─────────────────────────────────────────────
# Re-register User with extended admin
# ─────────────────────────────────────────────

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# ── Site branding ─────────────────────────────
admin.site.site_header  = "Stackly Admin"
admin.site.site_title   = "Stackly"
admin.site.index_title  = "User & Video Activity"
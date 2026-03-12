from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify


# ─────────────────────────────────────────────
# User Profile
# ─────────────────────────────────────────────

class UserProfile(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Legacy ImageField kept so old rows don't break; new uploads go to Cloudinary
    avatar = models.ImageField(upload_to="profile_avatars/", blank=True, null=True)

    # Cloudinary URL for profile photo (replaces local file storage)
    avatar_cloudinary_url = models.URLField(blank=True, default="")

    bio = models.TextField(blank=True, default="")

    default_language = models.CharField(max_length=10, default="en")
    video_quality    = models.CharField(max_length=10, default="hd")

    notify_video_done   = models.BooleanField(default=True)
    notify_errors       = models.BooleanField(default=True)
    notify_updates      = models.BooleanField(default=False)
    notify_marketing    = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username})"

    @property
    def avatar_url(self):
        """
        Returns the best available avatar URL:
        1. Cloudinary URL (new uploads)
        2. Legacy local ImageField URL (old uploads)
        3. Empty string (no avatar)
        """
        if self.avatar_cloudinary_url:
            return self.avatar_cloudinary_url
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:
                return ""
        return ""

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def initials(self):
        fn = self.user.first_name
        ln = self.user.last_name
        if fn and ln:
            return f"{fn[0].upper()}{ln[0].upper()}"
        return self.user.username[:2].upper()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


# ─────────────────────────────────────────────
# Platform Avatar Library  (admin-managed)
# ─────────────────────────────────────────────

class Avatar(models.Model):
    """
    A reusable platform avatar managed by admins.
    New avatars can be added via the admin panel without any code changes.
    """

    CATEGORY_CHOICES = [
        ("presenter",  "Presenter"),
        ("teacher",    "Teacher"),
        ("business",   "Business"),
        ("narrator",   "Narrator"),
        ("influencer", "Influencer"),
        ("custom",     "Custom"),
    ]

    name          = models.CharField(max_length=100)
    slug          = models.SlugField(max_length=120, unique=True, blank=True)
    preview_image = models.ImageField(
        upload_to="avatars/previews/",
        help_text="Thumbnail shown in the avatar selection grid.",
    )
    source_video  = models.FileField(
        upload_to="avatars/source/",
        help_text="Source video used by the Wav2Lip pipeline.",
    )
    description   = models.TextField(
        blank=True, default="",
        help_text="Short description shown below the avatar card.",
    )
    category      = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="presenter",
    )
    is_active     = models.BooleanField(
        default=True,
        help_text="Inactive avatars are hidden from the selection UI.",
    )
    sort_order    = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first in the grid.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Avatar"
        verbose_name_plural = "Avatars"

    def __str__(self):
        return f"{self.name} [{self.category}]"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug, counter = base_slug, 1
            while Avatar.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def preview_url(self):
        if self.preview_image:
            try:
                return self.preview_image.url
            except Exception:
                return ""
        return ""

    @property
    def source_video_path(self):
        """Absolute filesystem path to the source video, for pipeline use."""
        if self.source_video:
            try:
                return self.source_video.path
            except Exception:
                return ""
        return ""


# ─────────────────────────────────────────────
# User Avatar  (user-uploaded)
# ─────────────────────────────────────────────

class UserAvatar(models.Model):
    """
    An avatar uploaded by a regular user.
    - Private avatars  → available to the owner immediately (auto-approved).
    - Public avatars   → require admin approval before appearing in the shared library.
    """

    REVIEW_CHOICES = [
        ("pending",  "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    owner         = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_avatars",
    )
    name          = models.CharField(max_length=100)
    slug          = models.SlugField(max_length=120, blank=True)
    description   = models.TextField(blank=True, default="")
    category      = models.CharField(
        max_length=20,
        choices=Avatar.CATEGORY_CHOICES,
        default="custom",
    )

    preview_image = models.ImageField(
        upload_to="user_avatars/previews/",
        blank=True, null=True,
        help_text="Thumbnail shown in the avatar grid.",
    )
    source_video  = models.FileField(
        upload_to="user_avatars/source/",
        help_text="Source video used by the Wav2Lip pipeline.",
    )

    is_public     = models.BooleanField(
        default=False,
        help_text="If True, shared with all users after admin approval.",
    )
    review_status = models.CharField(
        max_length=10,
        choices=REVIEW_CHOICES,
        default="pending",
        help_text="Admin review status. Relevant only for public avatars.",
    )
    review_note   = models.TextField(
        blank=True, default="",
        help_text="Internal admin note (e.g. rejection reason).",
    )

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User Avatar"
        verbose_name_plural = "User Avatars"

    def __str__(self):
        return f"UserAvatar({self.owner.username} / {self.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.owner.username}-{self.name}")
            slug, counter = base_slug, 1
            while UserAvatar.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def preview_url(self):
        if self.preview_image:
            try:
                return self.preview_image.url
            except Exception:
                return ""
        return ""

    @property
    def source_video_path(self):
        if self.source_video:
            try:
                return self.source_video.path
            except Exception:
                return ""
        return ""

    @property
    def is_usable(self):
        """True when this avatar can be used in the pipeline by its owner."""
        if not self.is_active:
            return False
        if not self.is_public:
            return True           # private → always usable by owner
        return self.review_status == "approved"


# ─────────────────────────────────────────────
# Video Generation
# ─────────────────────────────────────────────

class VideoGeneration(models.Model):
    """
    Stores every video pipeline run.
    audio_file / video_file now store full Cloudinary URLs.
    avatar FK  → platform Avatar  (nullable for old rows).
    avatar_name → legacy plain-text fallback.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("done",    "Done"),
        ("failed",  "Failed"),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="videos")
    language   = models.CharField(max_length=10, default="en")
    input_text = models.TextField(blank=True, default="")

    # Platform avatar FK (nullable for backwards compat)
    avatar     = models.ForeignKey(
        Avatar,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="generated_videos",
    )
    # Legacy name field kept for pre-FK rows
    avatar_name = models.CharField(max_length=255, blank=True, default="")

    # Stores full Cloudinary URLs (e.g. https://res.cloudinary.com/...)
    # max_length bumped to 1000 to safely hold long Cloudinary URLs
    audio_file = models.CharField(max_length=1000, blank=True, default="")
    video_file = models.CharField(max_length=1000, blank=True, default="")

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default="done")
    duration_s = models.FloatField(null=True, blank=True,
                                   help_text="Pipeline wall-clock seconds")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"VideoGeneration(user={self.user.username}, "
            f"lang={self.language}, {self.created_at:%Y-%m-%d %H:%M})"
        )

    @property
    def video_url(self):
        """
        Returns the video URL directly.
        video_file now stores a full Cloudinary URL so no path manipulation needed.
        """
        return self.video_file or ""

    @property
    def audio_url(self):
        """Returns the audio URL directly (Cloudinary URL)."""
        return self.audio_file or ""

    @property
    def thumbnail_url(self):
        if self.avatar and self.avatar.preview_url:
            return self.avatar.preview_url
        return ""

    @property
    def short_text(self):
        return (self.input_text[:60] + "…") if len(self.input_text) > 60 else self.input_text

    @property
    def avatar_display_name(self):
        if self.avatar:
            return self.avatar.name
        return self.avatar_name or "—"
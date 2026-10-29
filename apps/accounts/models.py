import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrator'
        BUREAU_HEAD = 'BUREAU_HEAD', 'Bureau Head'
        CASE_OFFICER = 'CASE_OFFICER', 'Case Officer'
        REGIONAL_OFFICER = 'REGIONAL_OFFICER', 'Regional Officer'
        SENIOR_MGMT = 'SENIOR_MGMT', 'Senior Management'
        COMPETENT_AUTH = 'COMPETENT_AUTH', 'Competent Authority'

    class Region(models.TextChoices):
        NORTHERN = 'NORTHERN', 'Northern Region'
        NORTH_WEST = 'NORTH_WEST', 'North-Western Region'
        SOUTHERN = 'SOUTHERN', 'Southern Region'
        SOUTH_WEST = 'SOUTH_WEST', 'South-Western Region'
        EASTERN = 'EASTERN', 'Eastern Region'
        WESTERN = 'WESTERN', 'Western Region'
        CENTRAL = 'CENTRAL', 'Central Region'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.CASE_OFFICER)
    assigned_bureau = models.ForeignKey(
        'bureaus.Bureau',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='officers'
    )
    authorized_region = models.CharField(
        max_length=50,
        choices=Region.choices,
        blank=True,
        help_text="Designated AICTE region for Regional Officers"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'display_name']

    class Meta:
        ordering = ['username']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    @property
    def is_bureau_head(self):
        return self.role == self.Role.BUREAU_HEAD

    @property
    def is_case_officer(self):
        return self.role == self.Role.CASE_OFFICER

    @property
    def is_regional_officer(self):
        return self.role == self.Role.REGIONAL_OFFICER

    @property
    def is_senior_mgmt(self):
        return self.role == self.Role.SENIOR_MGMT

    @property
    def is_competent_auth(self):
        return self.role == self.Role.COMPETENT_AUTH

class EmailOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_otps')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'

    def __str__(self):
        return f"OTP for {self.user.username} ({self.otp_code})"

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() <= self.expires_at and self.attempts < 5

class PublicEmailOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Public Email OTP'
        verbose_name_plural = 'Public Email OTPs'

    def __str__(self):
        return f"Public OTP for {self.email} ({self.otp_code})"

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() <= self.expires_at and self.attempts < 5


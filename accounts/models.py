from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class CustomUserManager(BaseUserManager):
    def _create_user(self, mobile_number, password=None, **extra_fields):
        """Creates and returns a user with an email and password."""
        if not mobile_number:
            raise ValueError('The Mobile Number field must be set')

        # Normalize the mobile number directly, not as an email
        mobile_number = self.normalize_mobile_number(mobile_number)
        user = self.model(mobile_number=mobile_number, **extra_fields)

        if password:
            user.set_password(password)
        else:
            raise ValueError('The password must be set')

        user.save(using=self._db)
        return user

    def create_user(self, mobile_number, password=None, **extra_fields):
        """Creates and returns a regular user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(mobile_number, password, **extra_fields)

    def create_superuser(self, mobile_number, password=None, **extra_fields):
        """Creates and returns a superuser with the given mobile number and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(mobile_number, password, **extra_fields)

    def normalize_mobile_number(self, mobile_number):
        """Normalizes the mobile number for storage."""
        return mobile_number.strip()  # Simple normalization, adjust as needed

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model for mobile number authentication."""
    name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    is_favorite = models.BooleanField(default=False)
    is_vip = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.mobile_number

    def has_perm(self, perm, obj=None):
        """Checks if the user has a specific permission."""
        return True  # Adjust as necessary

    def has_module_perms(self, app_label):
        """Checks if the user has permissions for the specified app label."""
        return True  # Adjust as necessary


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100, blank=True, null=True)  # Addressed person's name
    email = models.EmailField(blank=True, null=True)  # Addressed person's email
    mobile_number = models.CharField(max_length=15, blank=True, null=True)  # Addressed person's mobile number
    address = models.TextField()
    pincode = models.CharField(max_length=6, blank=False, null=False, default=None)
    post_office = models.CharField(max_length=100, default="Unknown")
    block = models.CharField(max_length=100, default="Unknown")
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    is_home = models.BooleanField(default=False)
    is_office = models.BooleanField(default=False)
    is_other = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        elif not Address.objects.filter(user=self.user, is_default=True).exists():
            # Set as default if it's the first address for the user
            self.is_default = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address}, {self.district}, {self.state}, {self.country}"
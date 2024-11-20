from rest_framework import serializers
from .models import Address, CustomUser

# accounts/serializers.py

from rest_framework import serializers
from .models import CustomUser, Address

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'email', 'mobile_number', 'address', 'pincode', 'post_office', 'block',
            'district', 'state', 'country', 'is_home', 'is_office', 'is_other', 'is_default'
        ]

    def validate(self, data):
        # Ensure that only one address can have is_default=True per user
        request = self.context.get('request')

        if data.get('is_default') and request and request.user.is_authenticated:
            user_addresses = request.user.addresses.exclude(pk=self.instance.pk)  # Exclude current instance
            if user_addresses.filter(is_default=True).exists():
                raise serializers.ValidationError('Only one address can be the default.')

        return data

class UserSerializer(serializers.ModelSerializer):
    address = AddressSerializer()

    class Meta:
        model = CustomUser
        fields = ['name', 'mobile_number', 'email', 'address']

    def create(self, validated_data):
        address_data = validated_data.pop('address')
        user = CustomUser.objects.create(**validated_data)

        # Create the address associated with the user
        Address.objects.create(user=user, **address_data)
        return user

    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)

        # Update the user's basic info
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update the associated address if provided
        if address_data:
            # Assuming only one default address exists; otherwise, specify the logic for multiple addresses
            address_instance = instance.addresses.filter(is_default=True).first()
            if address_instance:
                for attr, value in address_data.items():
                    setattr(address_instance, attr, value)
                address_instance.save()
            else:
                # Handle case if no default address exists (e.g., create a new address)
                Address.objects.create(user=instance, **address_data)

        instance.save()
        return instance


class CreateStaffUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['name', 'mobile_number', 'email', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data, is_staff=True)

        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for public user details view, omits fields like favorite status."""
    class Meta:
        model = CustomUser
        fields = ['name', 'mobile_number']
        read_only_fields = ['name', 'mobile_number']


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login, handles mobile number and optional password."""
    mobile_number = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False)


class UserAdminSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'mobile_number', 'email', 'is_favorite', 'is_vip', 'addresses']

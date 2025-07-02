from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext as _
from rest_framework import serializers

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    verification_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'is_employee', 'verification_code']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }

    def create(self, validated_data):
        is_employee = validated_data.get('is_employee', False)
        code = validated_data.pop('verification_code', None)

        if is_employee and code != 'ABC123':
            raise serializers.ValidationError({"verification_code": "Invalid employee code."})

        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()
        return user


class AuthTokenSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
    )

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        user = None
        UserModel = get_user_model()
        try:
            user_obj = UserModel.objects.get(email=identifier)
        except UserModel.DoesNotExist:
            try:
                user_obj = UserModel.objects.get(username=identifier)
            except UserModel.DoesNotExist:
                user_obj = None

        if user_obj:
            user = authenticate(
                request=self.context.get('request'),
                username=user_obj.email,
                password=password
            )

        if not user:
            raise serializers.ValidationError(_("Invalid credentials"), code='authorization')

        attrs['user'] = user
        return attrs

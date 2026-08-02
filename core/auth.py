from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CoreJWTAuthentication(JWTAuthentication):
    """JWTAuthentication que resuelve el usuario contra core.User
    (modelo mock) en lugar del auth.User por defecto."""

    def get_user(self, validated_token):
        from .models import User

        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise InvalidToken('Token contains no user_id')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise InvalidToken('User not found')
        return user

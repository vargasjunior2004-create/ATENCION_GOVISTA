import time
import logging

from django.db import OperationalError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger('core')


class CoreJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        from .models import User

        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise InvalidToken('Token contains no user_id')

        for attempt in range(5):
            try:
                user = User.objects.get(id=user_id)
                break
            except User.DoesNotExist:
                raise InvalidToken('User not found')
            except OperationalError as e:
                if 'database is locked' not in str(e):
                    raise
                wait = 0.5 * (attempt + 1)
                logger.warning('DB locked in auth, retry %d in %.1fs', attempt + 1, wait)
                time.sleep(wait)
        else:
            raise InvalidToken('Database unavailable')

        if not user.active:
            raise InvalidToken('User is inactive')

        token_version = validated_token.get('ver')
        # Los tokens emitidos antes de esta versión no llevan 'ver'. Se
        # aceptan hasta que expiren; los nuevos siempre lo incluyen.
        if token_version is not None and int(token_version) != user.token_version:
            raise InvalidToken('Token has been revoked')

        return user

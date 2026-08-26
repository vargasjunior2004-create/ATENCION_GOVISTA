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
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise InvalidToken('User not found')
            except OperationalError as e:
                if 'database is locked' not in str(e):
                    raise
                wait = 0.5 * (attempt + 1)
                logger.warning('DB locked in auth, retry %d in %.1fs', attempt + 1, wait)
                time.sleep(wait)
        raise InvalidToken('Database unavailable')

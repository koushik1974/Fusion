from Fusion.settings.development import *

ROOT_URLCONF = 'Fusion.smoke_urls'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

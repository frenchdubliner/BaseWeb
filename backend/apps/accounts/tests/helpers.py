from django.contrib.auth import get_user_model

User = get_user_model()

VALID_PHONE = "+14155552671"


def make_user(email="user@example.com", password="Sup3rSecret!42", is_active=True, **kwargs):
    defaults = dict(
        first_name="Jane",
        last_name="Doe",
        phone_number=VALID_PHONE,
        dropoff_location="abington",
        payment_preference="cash_40",
    )
    defaults.update(kwargs)
    user = User.objects.create_user(email=email, password=password, **defaults)
    if is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    return user


def registration_payload(**overrides):
    payload = {
        "email": "newuser@example.com",
        "password": "Sup3rSecret!42",
        "confirm_password": "Sup3rSecret!42",
        "first_name": "New",
        "last_name": "User",
        "phone_number": VALID_PHONE,
        "dropoff_location": "norton",
        "payment_preference": "store_credit_70",
    }
    payload.update(overrides)
    return payload

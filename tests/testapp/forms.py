"""ModelForms for testing ValidatePartialUniqueMixin."""
from django import forms

from testapp.models import RoomBookingQ, RoomBookingText, NullableRoomNumberQ


class RoomBookingTextForm(forms.ModelForm):
    """Always fails with ImproperlyConfigured error, because mixin cannot be used with text-based conditions."""
    class Meta:
        model = RoomBookingText
        fields = ('user', 'room', 'deleted_at')


class RoomBookingAllFieldsForm(forms.ModelForm):
    """All fields are present on the form."""
    class Meta:
        model = RoomBookingQ
        fields = ('user', 'room', 'deleted_at')


class RoomBookingNoConditionFieldForm(forms.ModelForm):
    """Index fields are present on the form, but the condition field is not."""
    class Meta:
        model = RoomBookingQ
        fields = ('user', 'room')


class RoomBookingJustRoomForm(forms.ModelForm):
    """Only one out of the two indexed fields is present on the form."""
    class Meta:
        model = RoomBookingQ
        fields = ('room', )


class NullableRoomNumberAllFieldsForm(forms.ModelForm):
    """All fields are present on the form."""
    class Meta:
        model = NullableRoomNumberQ
        fields = ('room', 'room_number', 'deleted_at')

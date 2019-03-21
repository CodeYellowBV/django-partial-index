"""
Tests for actual use of the indexes after creating models with them.
"""
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from testapp.forms import RoomBookingAllFieldsForm, RoomBookingNoConditionFieldForm, RoomBookingJustRoomForm, RoomBookingTextForm, NullableRoomNumberAllFieldsForm
from testapp.models import User, Room, RoomBookingQ, NullableRoomNumberQ


class OnlyQTestCase(TestCase):
    def test_text_condition_improperlyconfigured(self):
        form = RoomBookingTextForm(data={'user': 1, 'room': 1})
        with self.assertRaises(ImproperlyConfigured):
            form.is_valid()


class FormTestCase(object):
    """Base class for form tests.
    """
    formclass = None
    conflict_error = 'Room booking q with this Room and User already exists.'

    def setUp(self):
        self.user1 = User.objects.create(name='User1')
        self.user2 = User.objects.create(name='User2')
        self.room1 = Room.objects.create(name='Room1')
        self.room2 = Room.objects.create(name='Room2')
        self.booking1 = RoomBookingQ.objects.create(user=self.user1, room=self.room1)
        self.booking2 = RoomBookingQ.objects.create(user=self.user1, room=self.room2)

    def test_add_duplicate_invalid(self):
        if self.formclass != RoomBookingJustRoomForm:
            form = self.formclass(data={'user': self.user1.id, 'room': self.room1.id})
            self.assertFalse(form.is_valid(), 'Form errors: %s' % form.errors)
            self.assertIn(self.conflict_error, form.errors['__all__'])
        else:
            pass  # Skipped - JustRoomForm only works for modifications.

    def test_add_duplicate_when_deleted_valid(self):
        if self.formclass != RoomBookingJustRoomForm:
            self.booking1.deleted_at = datetime.datetime.utcnow()
            self.booking1.save()

            form = self.formclass(data={'user': self.user1.id, 'room': self.room1.id})
            self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
            self.assertFalse(form.errors)
        else:
            pass  # Skipped - JustRoomForm only works for modifications.

    def test_add_non_duplicate_valid(self):
        if self.formclass != RoomBookingJustRoomForm:
            form = self.formclass(data={'user': self.user2.id, 'room': self.room1.id})
            self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
            self.assertFalse(form.errors)
        else:
            pass  # Skipped - JustRoomForm only works for modifications.

    def test_modify_existing_valid(self):
        form = self.formclass(data={'user': self.user1.id, 'room': self.room1.id}, instance=self.booking1)
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

    def test_modify_another_to_be_duplicate_invalid(self):
        form = self.formclass(data={'user': self.user1.id, 'room': self.room1.id}, instance=self.booking2)
        self.assertFalse(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertIn(self.conflict_error, form.errors['__all__'])

    def test_modify_another_to_be_duplicate_when_deleted_valid(self):
        self.booking1.deleted_at = datetime.datetime.utcnow()
        self.booking1.save()

        form = self.formclass(data={'user': self.user1.id, 'room': self.room1.id}, instance=self.booking2)
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)


class AllFieldsFormTest(FormTestCase, TestCase):
    """Test that partial unique validation on a ModelForm works when all fields are present on the form."""
    formclass = RoomBookingAllFieldsForm


class NoConditionFieldFormTest(FormTestCase, TestCase):
    """Test that partial unique validation on a ModelForm works when all index fields, but not the condition field are present on the form."""
    formclass = RoomBookingNoConditionFieldForm


class SingleFieldFormTest(FormTestCase, TestCase):
    """Test that partial unique validation on a ModelForm works when not all unique fields are present on the form.

    These have to be provided from an existing instance.
    """
    formclass = RoomBookingJustRoomForm


class NullableFieldFormTest(TestCase):
    """Test that partial unique validation on a ModelForm treats null values as non-unique."""
    formclass = NullableRoomNumberAllFieldsForm
    conflict_error = 'Nullable room number q with this Room and Room number already exists.'

    def setUp(self):
        self.room1 = Room.objects.create(name='Room1')
        self.room2 = Room.objects.create(name='Room2')
        self.number1_1 = NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)
        self.number1_2 = NullableRoomNumberQ.objects.create(room=self.room1, room_number=2)
        self.number2_1 = NullableRoomNumberQ.objects.create(room=self.room2, room_number=1)
        self.number2_none = NullableRoomNumberQ.objects.create(room=self.room2, room_number=None)

    def test_add_duplicate_invalid(self):
        form = self.formclass(data={'room': self.room1.id, 'room_number': 1})
        self.assertFalse(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertIn(self.conflict_error, form.errors['__all__'])

    def test_add_duplicate_when_deleted_valid(self):
        self.number1_1.deleted_at = datetime.datetime.utcnow()
        self.number1_1.save()
        
        form = self.formclass(data={'room': self.room1.id, 'room_number': 1})
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

    def test_add_non_duplicate_valid(self):
        form = self.formclass(data={'room': self.room1.id, 'room_number': 3})
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

    def test_modify_existing_valid(self):
        form = self.formclass(data={'room': self.room1.id, 'room_number': 3}, instance=self.number1_1)
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

    def test_modify_another_to_be_duplicate_on_fk_invalid(self):
        form = self.formclass(data={'room': self.room1.id, 'room_number': 1}, instance=self.number2_1)
        self.assertFalse(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertIn(self.conflict_error, form.errors['__all__'])

    def test_modify_another_to_be_duplicate_on_integer_invalid(self):
        form = self.formclass(data={'room': self.room1.id, 'room_number': 2}, instance=self.number1_1)
        self.assertFalse(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertIn(self.conflict_error, form.errors['__all__'])

    def test_modify_another_to_be_duplicate_on_nulled_field_valid(self):
        form = self.formclass(data={'room': self.room2.id, 'room_number': None}, instance=self.number2_1)
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

    def test_modify_another_to_be_duplicate_when_deleted_valid(self):
        self.number1_1.deleted_at = datetime.datetime.utcnow()
        self.number1_1.save()

        form = self.formclass(data={'room': self.room1.id, 'room_number': 1}, instance=self.number2_none)
        self.assertTrue(form.is_valid(), 'Form errors: %s' % form.errors)
        self.assertFalse(form.errors)

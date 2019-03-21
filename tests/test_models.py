"""
Tests for actual use of the indexes after creating models with them.
"""
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from testapp.models import User, Room, RoomBookingText, JobText, ComparisonText, NullableRoomNumberText, RoomBookingQ, JobQ, ComparisonQ, NullableRoomNumberQ, Label


class PartialIndexRoomBookingTest(TestCase):
    """Test that partial unique constraints work as expected when inserting data to the db.

    Models and indexes are created when django creates the test db, they do not need to be set up.
    """

    def setUp(self):
        self.user1 = User.objects.create(name='User1')
        self.user2 = User.objects.create(name='User2')
        self.room1 = Room.objects.create(name='Room1')
        self.room2 = Room.objects.create(name='Room2')

    def test_roombooking_text_different_rooms(self):
        RoomBookingText.objects.create(user=self.user1, room=self.room1)
        RoomBookingText.objects.create(user=self.user1, room=self.room2)

    def test_roombooking_q_different_rooms(self):
        RoomBookingQ.objects.create(user=self.user1, room=self.room1)
        RoomBookingQ.objects.create(user=self.user1, room=self.room2)

    def test_roombooking_text_different_users(self):
        RoomBookingText.objects.create(user=self.user1, room=self.room1)
        RoomBookingText.objects.create(user=self.user2, room=self.room1)

    def test_roombooking_q_different_users(self):
        RoomBookingQ.objects.create(user=self.user1, room=self.room1)
        RoomBookingQ.objects.create(user=self.user2, room=self.room1)

    def test_roombooking_text_same_mark_first_deleted(self):
        for i in range(3):
            book = RoomBookingText.objects.create(user=self.user1, room=self.room1)
            book.deleted_at = timezone.now()
            book.save()
        RoomBookingText.objects.create(user=self.user1, room=self.room1)

    def test_roombooking_q_same_mark_first_deleted(self):
        for i in range(3):
            book = RoomBookingQ.objects.create(user=self.user1, room=self.room1)
            book.deleted_at = timezone.now()
            book.save()
        RoomBookingQ.objects.create(user=self.user1, room=self.room1)

    def test_roombooking_text_same_conflict(self):
        RoomBookingText.objects.create(user=self.user1, room=self.room1)
        with self.assertRaises(IntegrityError):
            RoomBookingText.objects.create(user=self.user1, room=self.room1)

    def test_roombooking_q_same_conflict(self):
        RoomBookingQ.objects.create(user=self.user1, room=self.room1)

        room_booking = RoomBookingQ(user=self.user1, room=self.room1)
        with self.assertRaises(ValidationError) as cm:
            room_booking.full_clean()

        self.assertSetEqual({NON_FIELD_ERRORS}, set(cm.exception.message_dict.keys()))
        self.assertEqual('unique_together', cm.exception.error_dict[NON_FIELD_ERRORS][0].code)

        with self.assertRaises(IntegrityError):
            room_booking.save()


class PartialIndexJobTest(TestCase):
    """Test that partial unique constraints work as expected when inserting data to the db.

    Models and indexes are created when django creates the test db, they do not need to be set up.
    """
    def test_job_text_same_id(self):
        job1 = JobText.objects.create(order=1, group=1)
        job2 = JobText.objects.create(order=1, group=2)
        self.assertEqual(job1.order, job2.order)

    def test_job_q_same_id(self):
        job1 = JobQ.objects.create(order=1, group=1)
        job2 = JobQ.objects.create(order=1, group=2)
        self.assertEqual(job1.order, job2.order)

    def test_job_text_same_group(self):
        JobText.objects.create(order=1, group=1)
        with self.assertRaises(IntegrityError):
            JobText.objects.create(order=2, group=1)

    def test_job_q_same_group(self):
        JobQ.objects.create(order=1, group=1)

        job = JobQ(order=2, group=1)
        with self.assertRaises(ValidationError) as cm:
            job.full_clean()

        self.assertSetEqual({'group'}, set(cm.exception.message_dict.keys()))
        self.assertEqual('unique', cm.exception.error_dict['group'][0].code)

        with self.assertRaises(IntegrityError):
            job.save()

    def test_job_text_complete_same_group(self):
        job1 = JobText.objects.create(order=1, group=1, is_complete=True)
        job2 = JobText.objects.create(order=1, group=1)
        self.assertEqual(job1.order, job2.order)

    def test_job_q_complete_same_group(self):
        job1 = JobQ.objects.create(order=1, group=1, is_complete=True)
        job2 = JobQ.objects.create(order=1, group=1)
        self.assertEqual(job1.order, job2.order)

    def test_job_text_complete_later_same_group(self):
        job1 = JobText.objects.create(order=1, group=1)
        job2 = JobText.objects.create(order=1, group=1, is_complete=True)
        self.assertEqual(job1.order, job2.order)

    def test_job_q_complete_later_same_group(self):
        job1 = JobQ.objects.create(order=1, group=1)
        job2 = JobQ.objects.create(order=1, group=1, is_complete=True)
        self.assertEqual(job1.order, job2.order)


class PartialIndexComparisonTest(TestCase):
    """Test that partial unique constraints work as expected when inserting data to the db.

    Models and indexes are created when django creates the test db, they do not need to be set up.
    """
    def test_comparison_text_duplicate_same_number(self):
        ComparisonText.objects.create(a=1, b=1)
        with self.assertRaises(IntegrityError):
            ComparisonText.objects.create(a=1, b=1)

    def test_comparison_q_duplicate_same_number(self):
        ComparisonQ.objects.create(a=1, b=1)
        with self.assertRaises(IntegrityError):
            ComparisonQ.objects.create(a=1, b=1)

    def test_comparison_text_different_same_number(self):
        ComparisonText.objects.create(a=1, b=1)
        ComparisonText.objects.create(a=2, b=2)

    def test_comparison_q_different_same_number(self):
        ComparisonQ.objects.create(a=1, b=1)
        ComparisonQ.objects.create(a=2, b=2)

    def test_comparison_text_duplicate_different_numbers(self):
        ComparisonText.objects.create(a=1, b=2)
        ComparisonText.objects.create(a=1, b=2)

    def test_comparison_q_duplicate_different_numbers(self):
        ComparisonQ.objects.create(a=1, b=2)
        ComparisonQ.objects.create(a=1, b=2)


class PartialIndexRoomNumberTest(TestCase):
    """Test that partial unique constraints work as expected when inserting data to the db.

    Models and indexes are created when django creates the test db, they do not need to be set up.
    """

    def setUp(self):
        self.room1 = Room.objects.create(name='Room1')
        self.room2 = Room.objects.create(name='Room2')

    def test_nullable_roomnumber_text_different_rooms(self):
        NullableRoomNumberText.objects.create(room=self.room1, room_number=1)
        NullableRoomNumberText.objects.create(room=self.room2, room_number=1)

    def test_nullable_roomnumber_q_different_rooms(self):
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)
        NullableRoomNumberQ.objects.create(room=self.room2, room_number=1)

    def test_nullable_roomnumber_text_different_room_numbers(self):
        NullableRoomNumberText.objects.create(room=self.room1, room_number=1)
        NullableRoomNumberText.objects.create(room=self.room1, room_number=2)

    def test_nullable_roomnumber_q_different_users(self):
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=2)

    def test_nullable_roomnumber_text_same_mark_first_deleted(self):
        for i in range(3):
            nr = NullableRoomNumberText.objects.create(room=self.room1, room_number=1)
            nr.deleted_at = timezone.now()
            nr.save()
        NullableRoomNumberText.objects.create(room=self.room1, room_number=1)

    def test_nullable_roomnumber_q_same_mark_first_deleted(self):
        for i in range(3):
            nr = NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)
            nr.deleted_at = timezone.now()
            nr.save()
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)

    def test_nullable_roomnumber_text_same_conflict(self):
        NullableRoomNumberText.objects.create(room=self.room1, room_number=1)
        with self.assertRaises(IntegrityError):
            NullableRoomNumberText.objects.create(room=self.room1, room_number=1)

    def test_nullable_roomnumber_q_same_conflict(self):
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)
        with self.assertRaises(IntegrityError):
            NullableRoomNumberQ.objects.create(room=self.room1, room_number=1)


    def test_nullable_roomnumber_text_same_no_conflict_for_null_number(self):
        NullableRoomNumberText.objects.create(room=self.room1, room_number=None)
        NullableRoomNumberText.objects.create(room=self.room1, room_number=None)

    def test_nullable_roomnumber_q_same_no_conflict_for_null_number(self):
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=None)
        NullableRoomNumberQ.objects.create(room=self.room1, room_number=None)


class PartialIndexLabelValidationTest(TestCase):
    """Test that partial unique validations are all executed."""

    def setUp(self):
        self.room1 = Room.objects.create(name='room 1')
        self.room2 = Room.objects.create(name='room 2')
        self.user1 = User.objects.create(name='user 1')
        self.user2 = User.objects.create(name='user 2')

    def test_single_unique_constraints_are_still_evaluated(self):
        Label.objects.create(label='a', user=self.user1, room=self.room1, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-01T00:00:00')

        label = Label(label='b', user=self.user2, room=self.room2, uuid='22222222-0000-0000-0000-000000000000', created_at='2019-01-01T00:00:00')
        with self.assertRaises(ValidationError) as cm:
            label.full_clean()

        self.assertSetEqual({'created_at'}, set(cm.exception.message_dict.keys()))
        self.assertEqual('unique', cm.exception.error_dict['created_at'][0].code)

        with self.assertRaises(IntegrityError):
            label.save()

    def test_standard_single_field_unique_constraints_do_not_block_evaluation_of_partial_index_constraints(self):
        Label.objects.create(label='a', user=self.user1, room=self.room1, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-01T00:00:00')

        label = Label(label='b', user=self.user2, room=self.room2, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-01T00:00:00')
        with self.assertRaises(ValidationError) as cm:
            label.full_clean()

        self.assertSetEqual({'created_at', 'uuid'}, set(cm.exception.message_dict.keys()))
        self.assertEqual('unique', cm.exception.error_dict['created_at'][0].code)
        self.assertEqual('unique', cm.exception.error_dict['uuid'][0].code)

        with self.assertRaises(IntegrityError):
            label.save()

    def test_standard_unique_together_constraints_do_not_block_evaluation_of_partial_index_constraints(self):
        Label.objects.create(label='a', user=self.user1, room=self.room1, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-01T11:11:11')

        label = Label(label='b', user=self.user1, room=self.room1, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-02T22:22:22')
        with self.assertRaises(ValidationError) as cm:
            label.full_clean()

        self.assertSetEqual({NON_FIELD_ERRORS, 'uuid'}, set(cm.exception.message_dict.keys()))
        self.assertEqual(1, len(cm.exception.error_dict['uuid']))
        self.assertEqual(1, len(cm.exception.error_dict[NON_FIELD_ERRORS]))
        self.assertEqual('unique', cm.exception.error_dict['uuid'][0].code)
        self.assertEqual('unique_together', cm.exception.error_dict[NON_FIELD_ERRORS][0].code)

        with self.assertRaises(IntegrityError):
            label.save()

    def test_all_partial_constraints_are_included_in_validation_errors(self):
        Label.objects.create(label='a', user=self.user1, room=self.room1, uuid='11111111-0000-0000-0000-000000000000', created_at='2019-01-01T11:11:11')

        label = Label(label='a', user=self.user1, room=self.room1, uuid='22222222-0000-0000-0000-000000000000', created_at='2019-01-02T22:22:22')
        with self.assertRaises(ValidationError) as cm:
            label.full_clean()

        self.assertSetEqual({NON_FIELD_ERRORS}, set(cm.exception.message_dict.keys()))
        self.assertEqual(2, len(cm.exception.error_dict[NON_FIELD_ERRORS]))
        self.assertEqual('unique_together', cm.exception.error_dict[NON_FIELD_ERRORS][0].code)
        self.assertEqual(['label', 'room'], cm.exception.error_dict[NON_FIELD_ERRORS][0].params['unique_check'])
        self.assertEqual('unique_together', cm.exception.error_dict[NON_FIELD_ERRORS][1].code)
        self.assertEqual(['label', 'user'], cm.exception.error_dict[NON_FIELD_ERRORS][1].params['unique_check'])

        with self.assertRaises(IntegrityError):
            label.save()

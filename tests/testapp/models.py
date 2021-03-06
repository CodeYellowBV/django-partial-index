"""Models for tests."""
from __future__ import unicode_literals

from django.db import models

from partial_index import PartialIndex, PQ, PF, ValidatePartialUniqueMixin


class AB(models.Model):
    a = models.CharField(max_length=50)
    b = models.CharField(max_length=50)


class ABC(models.Model):
    a = models.CharField(max_length=50)
    b = models.CharField(max_length=50)
    c = models.CharField(max_length=50)


class User(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class RoomBookingText(ValidatePartialUniqueMixin, models.Model):
    """Note that ValidatePartialUniqueMixin cannot actually be used on this model, as it uses text-based index conditions.

    Any ModelForm or DRF Serializer validation will fail.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['user', 'room'], unique=True, where='deleted_at IS NULL')]


class RoomBookingQ(ValidatePartialUniqueMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['user', 'room'], unique=True, where=PQ(deleted_at__isnull=True))]


class JobText(models.Model):
    order = models.IntegerField()
    group = models.IntegerField()
    is_complete = models.BooleanField(default=False)

    class Meta:
        indexes = [
            PartialIndex(fields=['-order'], unique=False, where_postgresql='is_complete = false', where_sqlite='is_complete = 0'),
            PartialIndex(fields=['group'], unique=True, where_postgresql='is_complete = false', where_sqlite='is_complete = 0'),
        ]


class JobQ(ValidatePartialUniqueMixin, models.Model):
    order = models.IntegerField()
    group = models.IntegerField()
    is_complete = models.BooleanField(default=False)

    class Meta:
        indexes = [
            PartialIndex(fields=['-order'], unique=False, where=PQ(is_complete=False)),
            PartialIndex(fields=['group'], unique=True, where=PQ(is_complete=False)),
        ]


class ComparisonText(models.Model):
    """Partial index that references multiple fields on the model."""
    a = models.IntegerField()
    b = models.IntegerField()

    class Meta:
        indexes = [
            PartialIndex(fields=['a', 'b'], unique=True, where='a = b'),
        ]


class ComparisonQ(models.Model):
    """Partial index that references multiple fields on the model."""
    a = models.IntegerField()
    b = models.IntegerField()

    class Meta:
        indexes = [
            PartialIndex(fields=['a', 'b'], unique=True, where=PQ(a=PF('b'))),
        ]


class NullableRoomNumberText(ValidatePartialUniqueMixin, models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    room_number = models.IntegerField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['room', 'room_number'], unique=True, where='deleted_at IS NULL')]


class NullableRoomNumberQ(ValidatePartialUniqueMixin, models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    room_number = models.IntegerField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['room', 'room_number'], unique=True, where=PQ(deleted_at__isnull=True))]


class Label(ValidatePartialUniqueMixin, models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    label = models.TextField()
    uuid = models.UUIDField()
    created_at = models.DateTimeField(unique=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            PartialIndex(fields=['room', 'label'], unique=True, where=PQ(deleted_at__isnull=True)),
            PartialIndex(fields=['user', 'label'], unique=True, where=PQ(deleted_at__isnull=True)),
            PartialIndex(fields=['uuid'], unique=True, where=PQ(deleted_at__isnull=True)),
        ]
        unique_together = [['room', 'user']]  # Regardless of deletion status

from django.db import models

from partial_index import PartialIndex, PartialUniqueValidations


class AB(models.Model):
    a = models.CharField(max_length=50)
    b = models.CharField(max_length=50)


class User(models.Model):
    name = models.CharField(max_length=50)


class Room(PartialUniqueValidations, models.Model):
    name = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['name'], unique=True, where='1=1')] # Basically just unique=True on name


class RoomBooking(PartialUniqueValidations, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [PartialIndex(fields=['user', 'room'], unique=True, where='deleted_at IS NULL')]


class Job(PartialUniqueValidations, models.Model):
    order = models.IntegerField()
    group = models.IntegerField()
    is_complete = models.BooleanField(default=False)

    class Meta:
        indexes = [
            PartialIndex(fields=['-order'], unique=False, where_postgresql='is_complete = false', where_sqlite='is_complete = 0'),
            PartialIndex(fields=['group'], unique=True, where_postgresql='is_complete = false', where_sqlite='is_complete = 0'),
        ]

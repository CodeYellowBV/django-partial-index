from collections import defaultdict
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError, NON_FIELD_ERRORS
from django.db.models import Q

from .index import PartialIndex
from . import query


class PartialUniqueValidationError(ValidationError):
    pass


class ValidatePartialUniqueMixin(object):
    """PartialIndex with unique=True validation to ModelForms and Django Rest Framework Serializers.

    Mixin should be added before the parent model class, for example:

    class MyModel(ValidatePartialUniqueMixin, models.Model):
        ...

        indexes = [
            PartialIndex(...)
        ]

    The mixin is usable only for PartialIndexes with a Q-object where-condition. If applied to a model
    with a text-based where-condition, an error is raised.

    Important Note:
    Django's standard ModelForm validation for unique constraints is sub-optimal. If a field belonging to the
    unique index is not present on the form, then it the constraint is not validated. This requires adding
    hidden fields on the form, checking them against tampering, etc.

    ValidatePartialUniqueMixin does not follow that example:
    It always validates with all fields, even if they are not on the form.
    """

    def validate_unique(self, exclude=None):
        errors = {}

        # Standard unique validation first.
        try:
            super(ValidatePartialUniqueMixin, self).validate_unique(exclude=exclude)
        except ValidationError as e:
            errors.update(e.error_dict)

        # Merge ours into the existing errors (if any)
        try:
            if getattr(settings, 'DJANGO_PARTIAL_INDEX_FORCE_VALIDATION', True):
                exclude = None
            self.validate_partial_unique(exclude=exclude)
        except ValidationError as e:
            errors.update(e.error_dict)

        if errors:
            raise PartialUniqueValidationError(errors)

    def validate_partial_unique(self, exclude=None):
        """Check partial unique constraints on the model and raise ValidationError if any failed.

        We want to check if another instance already exists with the fields mentioned in idx.fields, but only if idx.where matches.
        But can't just check for the fields in idx.fields - idx.where may refer to other fields on the current (or other) models.
        Also can't check for all fields on the current model - should not include irrelevant fields which may hide duplicates.

        To find potential conflicts, we need to build a queryset which:
        1. Filters by idx.fields with their current values on this instance,
        2. Filters on idx.where
        3. Filters by fields mentioned in idx.where, with their current values on this instance,
        4. Excludes current object if it does not match the where condition.

        Note that step 2 ensures the lookup only looks for conflicts among rows covered by the PartialIndes,
        and steps 2+3 ensures that the QuerySet is empty if the PartialIndex does not cover the current object.
        """
        # Find PartialIndexes with unique=True defined on model.
        unique_idxs = [idx for idx in self._meta.indexes if isinstance(idx, PartialIndex) and idx.unique]

        exclude = set(exclude) if exclude else set()

        if unique_idxs:
            model_fields = set(f.name for f in self._meta.get_fields(include_parents=True, include_hidden=True))

            errors = defaultdict(list)
            for idx in unique_idxs:
                where = idx.where
                if not isinstance(where, Q):
                    raise ImproperlyConfigured(
                        'ValidatePartialUniqueMixin is not supported for PartialIndexes with a text-based where condition. ' +
                        'Please upgrade to Q-object based where conditions.'
                    )

                mentioned_fields = set(idx.fields) | set(query.q_mentioned_fields(where, self.__class__))

                missing_fields = mentioned_fields - model_fields
                if missing_fields:
                    raise RuntimeError('Unable to use ValidatePartialUniqueMixin: expecting to find fields %s on model. ' +
                                       'This is a bug in the PartialIndex definition or the django-partial-index library itself.')

                # Skip indexes with excluded fields
                if mentioned_fields & exclude:
                    continue

                values = {}
                skip = False
                for field_name in mentioned_fields:
                    field_value = getattr(self, field_name)
                    if field_value is None and field_name in idx.fields:
                        # Can never be unique if value is NULL.  If
                        # field is non-nullable we'll get a validation
                        # error from the field validations themselves.
                        skip = True
                    else:
                        values[field_name] = field_value

                if skip:
                    continue

                conflict = self.__class__.objects.filter(**values)  # Step 1 and 3
                conflict = conflict.filter(where)  # Step 2
                if self.pk:
                    conflict = conflict.exclude(pk=self.pk)  # Step 4

                if conflict.exists():
                    if len(idx.fields) == 1:
                        key = idx.fields[0]
                    else:
                        key = NON_FIELD_ERRORS
                    errors[key].append(self.unique_error_message(self.__class__, sorted(idx.fields)))

            if errors:
                raise PartialUniqueValidationError(errors)

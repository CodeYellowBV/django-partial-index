# Provide a nicer error message than failing to import models.Index.

VERSION = (0, 4, 0)
__version__ = '.'.join(str(v) for v in VERSION)


MIN_DJANGO_VERSION = (1, 11)
DJANGO_VERSION_ERROR = 'Django version %s or later is required for django-partial-index.' % '.'.join(str(v) for v in MIN_DJANGO_VERSION)

try:
    import django
except ImportError:
    raise ImportError(DJANGO_VERSION_ERROR)

if tuple(django.VERSION[:2]) < MIN_DJANGO_VERSION:
    raise ImportError(DJANGO_VERSION_ERROR)


from django.db import connections
from django.db.models import Index
from django.db.models.expressions import RawSQL
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

class PartialIndex(Index):
    suffix = 'partial'
    # Allow an index name longer than 30 characters since this index can only be used on PostgreSQL and SQLite,
    # and the Django default 30 character limit for cross-database compatibility isn't applicable.
    # The "partial" suffix is 4 letters longer than the default "idx".
    max_name_length = 34
    sql_create_index = {
        'postgresql': 'CREATE%(unique)s INDEX %(name)s ON %(table)s%(using)s (%(columns)s)%(extra)s WHERE %(where)s',
        'sqlite': 'CREATE%(unique)s INDEX %(name)s ON %(table)s%(using)s (%(columns)s) WHERE %(where)s',
    }

    # Mutable default fields=[] looks wrong, but it's copied from super class.
    def __init__(self, fields=[], name=None, unique=None, where='', where_postgresql='', where_sqlite=''):
        if unique not in [True, False]:
            raise ValueError('Unique must be True or False')
        if where:
            if where_postgresql or where_sqlite:
                raise ValueError('If providing a single where predicate, must not provide where_postgresql or where_sqlite')
        else:
            if not where_postgresql and not where_sqlite:
                raise ValueError('At least one where predicate must be provided')
            if where_postgresql == where_sqlite:
                raise ValueError('If providing a separate where_postgresql and where_sqlite, then they must be different.' +
                                 'If the same expression works for both, just use single where.')
        self.unique = unique
        self.where = where
        self.where_postgresql = where_postgresql
        self.where_sqlite = where_sqlite
        super(PartialIndex, self).__init__(fields=fields, name=name)

    def __repr__(self):
        if self.where:
            anywhere = "where='%s'" % self.where
        else:
            anywhere = "where_postgresql='%s', where_sqlite='%s'" % (self.where_postgresql, self.where_sqlite)

        return "<%(name)s: fields=%(fields)s, unique=%(unique)s, %(anywhere)s>" % {
            'name': self.__class__.__name__,
            'fields': "'{}'".format(', '.join(self.fields)),
            'unique': self.unique,
            'anywhere': anywhere
        }

    def deconstruct(self):
        path, args, kwargs = super(PartialIndex, self).deconstruct()
        kwargs['unique'] = self.unique
        kwargs['where'] = self.where
        kwargs['where_postgresql'] = self.where_postgresql
        kwargs['where_sqlite'] = self.where_sqlite
        return path, args, kwargs

    @classmethod
    def get_valid_vendor_for_connection(cls, connection):
        v = connection.vendor
        if v not in cls.sql_create_index:
            raise ValueError('Database vendor %s is not supported for django-partial-index.' % v)
        return v

    def get_sql_create_template_values(self, model, schema_editor, using):
        # This method exists on Django 1.11 Index class, but has been moved to the SchemaEditor on Django 2.0.
        # This makes it complex to call superclass methods and avoid duplicating code.
        # Can be simplified if Django 1.11 support is dropped one day.

        # Copied from Django 1.11 Index.get_sql_create_template_values(), which does not exist in Django 2.0:
        fields = [model._meta.get_field(field_name) for field_name, order in self.fields_orders]
        tablespace_sql = schema_editor._get_index_tablespace_sql(model, fields)
        quote_name = schema_editor.quote_name
        columns = [
            ('%s %s' % (quote_name(field.column), order)).strip()
            for field, (field_name, order) in zip(fields, self.fields_orders)
        ]
        parameters = {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
            'columns': ', '.join(columns),
            'using': using,
            'extra': tablespace_sql,
        }

        # PartialIndex updates:
        parameters['unique'] = ' UNIQUE' if self.unique else ''
        # Note: the WHERE predicate is not yet checked for syntax or field names, and is inserted into the CREATE INDEX query unescaped.
        # This is bad for usability, but is not a security risk, as the string cannot come from user input.
        vendor = self.get_valid_vendor_for_connection(schema_editor.connection)
        parameters['where'] = self.get_where_condition_for_vendor(vendor)
        return parameters

    def get_where_condition_for_vendor(self, vendor):
        if vendor == 'postgresql':
            return self.where_postgresql or self.where
        elif vendor == 'sqlite':
            return self.where_sqlite or self.where
        else:
            raise ValueError('Should never happen')
        

    def create_sql(self, model, schema_editor, using=''):
        vendor = self.get_valid_vendor_for_connection(schema_editor.connection)
        sql_template = self.sql_create_index[vendor]
        sql_parameters = self.get_sql_create_template_values(model, schema_editor, using)
        return sql_template % sql_parameters

    def name_hash_extra_data(self):
        return [str(self.unique), self.where, self.where_postgresql, self.where_sqlite]

    def set_name_with_model(self, model):
        """Sets an unique generated name for the index.

        PartialIndex would like to only override "hash_data = ...", but the entire method must be duplicated for that.
        """
        table_name = model._meta.db_table
        column_names = [model._meta.get_field(field_name).column for field_name, order in self.fields_orders]
        column_names_with_order = [
            (('-%s' if order else '%s') % column_name)
            for column_name, (field_name, order) in zip(column_names, self.fields_orders)
        ]
        # The length of the parts of the name is based on the default max
        # length of 30 characters.
        hash_data = [table_name] + column_names_with_order + [self.suffix] + self.name_hash_extra_data()
        self.name = '%s_%s_%s' % (
            table_name[:11],
            column_names[0][:7],
            '%s_%s' % (self._hash_generator(*hash_data), self.suffix),
        )
        assert len(self.name) <= self.max_name_length, (
            'Index too long for multiple database support. Is self.suffix '
            'longer than 3 characters?'
        )
        self.check_name()



class PartialUniqueValidations(object):
    def validate_unique(self, exclude=None):
        errors = {}

        # First, check original/standard Django constraints
        try:
            super(PartialUniqueValidations, self).validate_unique(exclude=exclude)
        except ValidationError as e:
            errors = e.error_dict

        index_checks = self._get_unique_partial_index_checks(exclude=exclude)
        errors.update(self._perform_unique_partial_index_checks(index_checks))

        if errors:
            raise ValidationError(errors)


    def _unique_partial_indexes_for_class(self, cls):
        return [i for i in cls._meta.indexes if isinstance(i, PartialIndex) and i.unique]


    def _get_unique_partial_index_checks(self, exclude=None):
        if exclude is None:
            exclude = []

        indexes_to_check = []

        # Build list of unique partial indexes per class
        i = self._unique_partial_indexes_for_class(self.__class__)
        unique_indexes = [(self.__class__, i)]
        for parent_class in self._meta.get_parent_list():
            if parent_class._meta.indexes:
                i = self._unique_partial_indexes_for_class(parent_class._meta.indexes)
                if i:
                    unique_indexes.append((parent_class, i))

        # Omit index checks that have any excluded fields
        for model_class, checks in unique_indexes:
            for unique_index in checks:
                for name in unique_index.fields:
                    if name in exclude:
                        break
                else:
                    indexes_to_check.append((model_class, unique_index))

        return indexes_to_check


    def _perform_unique_partial_index_checks(self, unique_checks):
        errors = {}

        for model_class, unique_check in unique_checks:
            # Try to look up an existing object with the same values as this
            # object's values for all the unique field.

            lookup_kwargs = {}
            for field_name in unique_check.fields:
                f = self._meta.get_field(field_name)
                lookup_value = getattr(self, f.attname)
                # TODO: Handle multiple backends with different feature flags.
                if (lookup_value is None or
                        (lookup_value == '' and connection.features.interprets_empty_strings_as_nulls)):
                    # no value, skip the lookup
                    continue
                if f.primary_key and not self._state.adding:
                    # no need to check for unique primary key when editing
                    continue
                lookup_kwargs[str(field_name)] = lookup_value

            # some fields were skipped, no reason to do the check
            if len(unique_check.fields) != len(lookup_kwargs):
                continue

            qs = model_class._default_manager.filter(**lookup_kwargs)

            # Exclude the current object from the query if we are editing an
            # instance (as opposed to creating a new one)
            # Note that we need to use the pk as defined by model_class, not
            # self.pk. These can be different fields because model inheritance
            # allows single model to have effectively multiple primary keys.
            # Refs #17615.
            model_class_pk = self._get_pk_val(model_class._meta)
            if not self._state.adding and model_class_pk is not None:
                qs = qs.exclude(pk=model_class_pk)

            # See also the NOTE in PartialIndex.get_sql_create_template_values()!
            vendor = PartialIndex.get_valid_vendor_for_connection(connections[model_class._default_manager.db])
            qs = qs.annotate(_partial_index_where=RawSQL(unique_check.get_where_condition_for_vendor(vendor), []))
            qs = qs.filter(_partial_index_where=True)

            if qs.exists():
                if len(unique_check.fields) == 1:
                    key = unique_check.fields[0]
                else:
                    key = NON_FIELD_ERRORS
                errors.setdefault(key, []).append(self.unique_error_message(model_class, unique_check.fields))

        return errors
        

from django.db import models
from django.utils.datastructures import DictWrapper
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import BigIntegerField, IntegerField
from django.utils import timezone

psql_engines = ('django.db.backends.postgresql_psycopg2',
                'django.contrib.gis.db.backends.postgis')

def db_type(connection, primary_key=False):
    c = connection
    cengine = c.settings_dict['ENGINE']
    #print("\n------------------\n[share] cengine = %s" % cengine)
    cengine_id = -1
    if cengine in psql_engines:
        cengine_id = psql_engines.index(cengine)
    if cengine_id > -1:
        if primary_key:
            return 'bigserial'
        else:
            return 'bigint'
    data = DictWrapper(self.__dict__, c.ops.quote_name, "qn_")
    #print("\n------------------\n[share] data = %s" % data)
    if cengine_id == 0:      # postgresql
        try:
            return c.creation.data_types[self.get_internal_type()] % data
        except KeyError:
            return None
    elif cengine_id == 1:    # postGIS
        try:
            #print("\n------------------\n[share] c.creation.connection = %s" % c.creation.connection)
            return c.creation.connection.data_types[self.get_internal_type()] % data
        except KeyError:
            return None
    return None


class BigAutoField(models.AutoField):
    # used to return bigserial for ids in postgresql (monkey patching)
    """
    This class allows Bigserial in model keys, because Django defaults to Serial
    or integers only which run out at 2**32 or 2,147,483,647.
    Bigints allow us to go to 2**63 or 9,223,372,036,854,775,807.
    """
    def __init__(self, *args, **kwargs):
        super(BigAutoField, self).__init__(*args, **kwargs)

    def db_type(self, connection):  # Big_AF
        return db_type(connection, primary_key=True)

class BigAutoField_ForMigrations(models.AutoField):
    # used to return bigserial for ids in postgresql (monkey patching) - kC
    """
    This class is necessary because Django migrations framework will generate
    ALTER TABLE foo ALTER COLUMN id TYPE BIGSERIAL
    which is incorrect as BIGSERIAL is postgresql shortcut for bigint with a
    sequence attached .
    Django must use bigserial during CREATE TABLE and bigint during ALTER TABLE
    Goal is to use BigAutoField for all primary keys in the models, and as we
    generate the makemigration files for the one-time conversions,
    we modify them to use this class instead during migrations.AlterField
    """
    def __init__(self, *args, **kwargs):
        super(BigAutoField_ForMigrations, self).__init__(*args, **kwargs)

    def db_type(self, connection):  # BigAF_ForMigrations
        return db_type(connection, primary_key=False)

class BigForeignKey(ForeignKey):
    """
    We use BigForeignKey inst. ForeignKeys for keys that reference BigAutoFields
    """
    def db_type(self, connection):
        rel_field = self.rel.get_related_field()
        # print "db_type: %s [%s]" % (rel_field.db_type(connection=connection),
        # rel_field)
        if (isinstance(rel_field, (models.AutoField, BigAutoField))) and \
                connection.settings_dict['ENGINE'] in psql_engines:
            return BigIntegerField().db_type(connection=connection)
        elif isinstance(rel_field, models.AutoField):   # Not postgreSQL
            return IntegerField().db_type(connection=connection)
        return rel_field.db_type(connection=connection)

class Float16Field(models.Field):   # custom 16-bit float-field. UNTESTED
    def db_type(self,connection):
        return 'float'

# --------------------------------- sample usage for use/migrations
class ModelPkey(models.Model):
    id = BigAutoField(primary_key=True)
    class Meta:
        abstract = True

class ModelWithoutPkey(models.Model):
    """
    As per the issue in BigAutoField_ForMigrations,
    To migrate existing models from models.Model to ModelPkey, we need a 2-step approach
    1 - replace existing inheritance from models.Model to ModelPkey_ForMigrations and run makemigrations and migrate
    2 - replace existing inheritance from ModelPkey_ForMigrations to ModelPkey
    """
    class Meta:
        abstract = True

class ModelPkey_ForMigrations(models.Model):
    id = BigAutoField_ForMigrations(primary_key=True)
    class Meta:
        abstract = True

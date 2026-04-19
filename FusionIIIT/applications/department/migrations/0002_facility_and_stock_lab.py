from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('department', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('branch', models.CharField(blank=True, default='', max_length=40)),
                ('location', models.CharField(blank=True, default='', max_length=100)),
                ('lab', models.CharField(blank=True, default='', max_length=100)),
                ('amount', models.IntegerField(default=1)),
                ('picture', models.ImageField(blank=True, null=True, upload_to='department/facilities')),
                ('stock_request_id', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'department_facility',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.RunSQL(
            sql="ALTER TABLE IF EXISTS department_stock ADD COLUMN IF NOT EXISTS lab varchar(100) DEFAULT '';",
            reverse_sql="ALTER TABLE IF EXISTS department_stock DROP COLUMN IF EXISTS lab;",
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('department', '0002_facility_and_stock_lab'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS department_stock (
                id SERIAL PRIMARY KEY,
                request_maker_id VARCHAR(20) REFERENCES globals_extrainfo(id) ON DELETE CASCADE,
                request_date TIMESTAMP WITHOUT TIME ZONE,
                brief VARCHAR(50) NOT NULL,
                request_details VARCHAR(300) NOT NULL,
                upload_request VARCHAR(100),
                status VARCHAR(20) DEFAULT 'PENDING',
                remarks VARCHAR(300) DEFAULT '',
                request_receiver VARCHAR(50) NOT NULL,
                stock_item_name VARCHAR(100) NOT NULL,
                quantity INTEGER DEFAULT 1,
                lab VARCHAR(100) DEFAULT '',
                issued_by_id VARCHAR(20) REFERENCES globals_extrainfo(id) ON DELETE SET NULL,
                issued_quantity INTEGER,
                issued_date TIMESTAMP WITHOUT TIME ZONE
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS department_stock;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS department_feedback (
                id SERIAL PRIMARY KEY,
                submitter_id VARCHAR(20) REFERENCES globals_extrainfo(id) ON DELETE CASCADE,
                subject VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                upload_feedback VARCHAR(100),
                category VARCHAR(100),
                is_confidential BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'NEW',
                resolution_remarks TEXT,
                resolved_by_id VARCHAR(20) REFERENCES globals_extrainfo(id) ON DELETE SET NULL,
                submitted_at TIMESTAMP WITHOUT TIME ZONE,
                resolved_at TIMESTAMP WITHOUT TIME ZONE
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS department_feedback;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS department_timetable (
                id SERIAL PRIMARY KEY,
                department VARCHAR(10) NOT NULL,
                programme VARCHAR(10) NOT NULL,
                batch VARCHAR(40) NOT NULL,
                day_of_week VARCHAR(10) NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                subject VARCHAR(100) NOT NULL,
                faculty VARCHAR(100) NOT NULL,
                room_no VARCHAR(20) NOT NULL,
                academic_year VARCHAR(20) NOT NULL,
                semester VARCHAR(10) NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE,
                updated_at TIMESTAMP WITHOUT TIME ZONE
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS department_timetable;",
        ),
    ]

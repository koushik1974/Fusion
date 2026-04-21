# Module Name: Department

## Designated User Roles & Permissions

### 1. Role Name: Department Admin (DeptAdmin)

* **Description:** Primary manager for all department operations and system settings. Holds the highest permissions for administrative tasks.

* **Permissions:**

    * Full CRUD (Create, Read, Update, Delete) operations on all department module data.
    * Ability to assign and manage sub-roles for other department users.
    * Access to audit logs and comprehensive reporting tools.
    * Can allocate and issue stocks from approved requisitions.
    * Can create and manage timetables (department-restricted).
    * Can create and modify department facilities.
    * Can manage announcements for the department.
    * Can view and resolve feedback/complaints from faculty and students.
    * Can manage faculty and student directories and profiles.
    * Full access to all department data and configurations.

### 2. Role Name: Head of Department (HOD)

* **Description:** Senior academic authority responsible for approvals and oversight of department operations. Acts as the approval authority in the workflow hierarchy.

* **Permissions:**

    * Read and approve/reject stock requisitions from faculty.
    * View all department announcements and communicate with staff.
    * Access department performance reports and summaries.
    * View and respond to feedback/complaints.
    * Approve profile change requests from faculty members.
    * View comprehensive timetables and facilities.
    * Monitor departmental inventory and resource allocation.
    * Access audit trails for accountability.
    * Cannot directly modify core configurations (DeptAdmin reserved).

### 3. Role Name: Faculty/Staff (AP - Academic Personnel)

* **Description:** Standard operational user responsible for day-to-day activities and data entry related to academic operations.

* **Permissions:**

    * Submit stock requisitions for departmental needs.
    * View assigned records and personal allocations.
    * Edit specific fields such as status updates in personal domain.
    * Generate individual activity summaries and reports.
    * View and access timetable information.
    * Submit feedback and complaints regarding department operations.
    * Request profile changes and updates.
    * View department announcements.
    * Access personal directory and view collegial information.

### 4. Role Name: Student/End-User

* **Description:** Consumer of the module's services. Limited access primarily for viewing information and submitting requests.

* **Permissions:**

    * Read-only access to personal records and allocations.
    * View department announcements and important notices.
    * Submit feedback and complaints regarding department services.
    * View personal timetable and class schedules.
    * Access student directory information.
    * Submit requests for information or services via frontend interfaces.
    * View facility information available to students.
    * Cannot modify any department data or configurations.

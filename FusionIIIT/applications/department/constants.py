"""
Department Module Constants

This module centralizes all constant values used across the Department module,
including role names, status values, and helper functions for role normalization.
"""


class DepartmentRoles:
    """Department role name constants"""
    HOD = 'hod'
    DEPTADMIN = 'deptadmin'
    DEPT_ADMIN = 'dept_admin'
    ASSISTANT_PROF = 'assistant professor'


class StockStatus:
    """Stock request status constants"""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    ALLOCATED = 'ALLOCATED'
    ISSUED = 'ISSUED'
    
    VALID_STATES = {PENDING, APPROVED, REJECTED, ALLOCATED, ISSUED}


class FeedbackStatus:
    """Feedback status constants"""
    NEW = 'NEW'
    RESOLVED = 'RESOLVED'
    
    VALID_STATES = {NEW, RESOLVED}


class AnnouncementDefaults:
    """Announcement default values"""
    BATCH = 'Year-1'
    DEPARTMENT = 'ALL'


def normalize_role(designation_name):
    """
    Normalize role designation name to standard format.
    
    Args:
        designation_name (str): Raw designation name from database
        
    Returns:
        str: Normalized role name or None if not recognized
        
    Examples:
        normalize_role('HOD') -> 'hod'
        normalize_role('Head of Department') -> 'hod'
        normalize_role('Dept Admin') -> 'deptadmin'
        normalize_role('Assistant Professor') -> 'assistant professor'
    """
    if not designation_name:
        return None
    
    name_lower = str(designation_name).strip().lower()
    
    # Check for HOD variants
    if name_lower.startswith('hod') or 'head of department' in name_lower or 'headofdepartment' in name_lower:
        return DepartmentRoles.HOD
    
    # Check for DeptAdmin variants
    if 'deptadmin' in name_lower or 'dept_admin' in name_lower or 'department admin' in name_lower:
        return DepartmentRoles.DEPTADMIN
    
    # Check for Assistant Professor
    if 'assistant professor' in name_lower:
        return DepartmentRoles.ASSISTANT_PROF
    
    # Return original lowercase if no match
    return name_lower


def is_hod(designation_name):
    """Check if designation is HOD"""
    return normalize_role(designation_name) == DepartmentRoles.HOD


def is_deptadmin(designation_name):
    """Check if designation is Department Admin"""
    normalized = normalize_role(designation_name)
    return normalized in {DepartmentRoles.DEPTADMIN, DepartmentRoles.DEPT_ADMIN}


def is_assistant_professor(designation_name):
    """Check if designation is Assistant Professor"""
    return normalize_role(designation_name) == DepartmentRoles.ASSISTANT_PROF


def is_valid_stock_status(status):
    """Check if stock status is valid"""
    return status in StockStatus.VALID_STATES


def is_valid_feedback_status(status):
    """Check if feedback status is valid"""
    return status in FeedbackStatus.VALID_STATES

from ninja import Router, Schema
from typing import List
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from .mongo_utils import log_activity, log_learning_analytics
from django_ratelimit.decorators import ratelimit
from django.db import connection

from .models import (
    Course,
    Lesson,
    Enrollment,
    Progress,
    Announcement
)

from .auth import JWTAuth, require_role


router = Router()

def success_response(message, data=None):
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(message):
    return {
        "success": False,
        "message": message,
        "data": None
    }

# ========================
# HEALTH CHECK
# ========================
@router.get("/health")
def health_check(request):

    db_status = "disconnected"
    redis_status = "disconnected"

    # PostgreSQL Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        pass

    # Redis Check
    try:
        cache.set("health_test", "ok", 10)
        cache.get("health_test")
        redis_status = "connected"
    except Exception:
        pass

    return success_response(
    "System healthy",
    {
        "database": db_status,
        "redis": redis_status
    }
)

# ========================
# SCHEMAS
# ========================
class CourseOutSchema(Schema):
    id: int
    title: str
    description: str


class CourseCreateSchema(Schema):
    title: str
    description: str


class CourseUpdateSchema(Schema):
    title: str = None
    description: str = None

# ========================
# LESSON SCHEMA
# ========================
class LessonCreateSchema(Schema):
    course_id: int
    title: str
    content: str
    order: int


# ========================
# ENROLLMENT SCHEMA
# ========================
class EnrollmentCreateSchema(Schema):
    course_id: int


# ========================
# PROGRESS SCHEMA
# ========================
class ProgressCreateSchema(Schema):
    enrollment_id: int
    lesson_id: int
    is_completed: bool

class AnnouncementCreateSchema(Schema):
    course_id: int
    title: str
    content: str

# ========================
# LIST (PUBLIC) + REDIS CACHE
# ========================
@router.get("/")
@ratelimit(key="ip", rate="60/m", block=True)
def list_courses(
    request,
    search: str = None,
    sort: str = None
):
    queryset = Course.objects.all()

    # SEARCH
    if search:
        queryset = queryset.filter(
            title__icontains=search
        )

    # SORT
    if sort == "title":
        queryset = queryset.order_by("title")

    elif sort == "-title":
        queryset = queryset.order_by("-title")

    elif sort == "id":
        queryset = queryset.order_by("id")

    elif sort == "-id":
        queryset = queryset.order_by("-id")

    courses = list(
        queryset.values(
            "id",
            "title",
            "description"
        )
    )

    return success_response(
    "Courses retrieved successfully",
    {
        "count": len(courses),
        "courses": courses
    }
)

# ========================
# CREATE COURSE
# ========================
@router.post("/", auth=JWTAuth())
@require_role(["instructor"])
def create_course(request, data: CourseCreateSchema):
    user = request.auth

    course = Course.objects.create(
        title=data.title,
        description=data.description,
        instructor=user
    )

    log_activity(
        user_id=user.id,
        action="CREATE_COURSE",
        detail=f"Course '{course.title}' created"
    )

    log_learning_analytics(
        user_id=user.id,
        course_id=course.id,
        event_type="COURSE_CREATED",
        progress=0
    )

    cache.delete("course_list")

    return success_response(
    "Course created successfully",
    {
        "id": course.id,
        "title": course.title,
        "description": course.description
    }
)


# ========================
# LESSONS
# ========================
@router.get("/lessons")
def list_lessons(request):

    lessons = list(
        Lesson.objects.values(
            "id",
            "title",
            "content",
            "order",
            "course_id"
        )
    )

    return success_response(
        "Lessons retrieved successfully",
        lessons
    )

@router.post("/lessons", auth=JWTAuth())
@require_role(["instructor"])
def create_lesson(request, data: LessonCreateSchema):

    course = get_object_or_404(
        Course,
        id=data.course_id
    )

    lesson = Lesson.objects.create(
        course=course,
        title=data.title,
        content=data.content,
        order=data.order
    )

    return success_response(
    "Lesson created successfully",
    {
        "id": lesson.id,
        "title": lesson.title
    }
)


@router.get("/lessons/{lesson_id}")
def get_lesson(request, lesson_id: int):

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id
    )

    return success_response(
    "Lesson retrieved successfully",
    {
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content,
        "order": lesson.order,
        "course_id": lesson.course.id
    }
)


# ========================
# ENROLLMENTS
# ========================
@router.get("/enrollments", auth=JWTAuth())
def list_enrollments(request):

    enrollments = list(
        Enrollment.objects.values(
            "id",
            "student_id",
            "course_id"
        )
    )

    return success_response(
        "Enrollments retrieved successfully",
        enrollments
    )

@router.post("/enrollments", auth=JWTAuth())
@require_role(["student"])
def create_enrollment(request, data: EnrollmentCreateSchema):

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.auth,
        course_id=data.course_id
    )

    return success_response(
    "Enrollment created successfully",
    {
        "id": enrollment.id,
        "course_id": enrollment.course.id,
        "student_id": enrollment.student.id
    }
)


# ========================
# PROGRESS
# ========================
@router.get("/progress", auth=JWTAuth())
def list_progress(request):

    progress = list(
        Progress.objects.values(
            "id",
            "enrollment_id",
            "lesson_id",
            "is_completed"
        )
    )

    return success_response(
        "Progress retrieved successfully",
        progress
    )

@router.post("/progress", auth=JWTAuth())
def create_progress(request, data: ProgressCreateSchema):

    progress, created = Progress.objects.update_or_create(
        enrollment_id=data.enrollment_id,
        lesson_id=data.lesson_id,
        defaults={
            "is_completed": data.is_completed
        }
    )

    return success_response(
    "Progress updated successfully",
    {
        "id": progress.id,
        "is_completed": progress.is_completed
    }
)

# ========================
# STUDENT DASHBOARD
# ========================

@router.get("/dashboard", auth=JWTAuth())
@require_role(["student"])
def student_dashboard(request):

    student = request.auth

    enrollments = Enrollment.objects.filter(
        student=student
    )

    total_courses = enrollments.count()

    total_progress = Progress.objects.filter(
        enrollment__student=student
    ).count()

    completed_lessons = Progress.objects.filter(
        enrollment__student=student,
        is_completed=True
    ).count()

    return success_response(
    "Dashboard retrieved successfully",
    {
        "student_id": student.id,
        "username": student.username,
        "total_courses": total_courses,
        "total_progress_records": total_progress,
        "completed_lessons": completed_lessons
    }
)

# ========================
# ANNOUNCEMENTS
# ========================

@router.get("/announcements")
def list_announcements(request):

    announcements = list(
        Announcement.objects.values(
            "id",
            "course_id",
            "title",
            "content",
            "created_at"
        )
    )

    return success_response(
        "Announcements retrieved successfully",
        announcements
    )

@router.post("/announcements", auth=JWTAuth())
@require_role(["instructor"])
def create_announcement(
    request,
    data: AnnouncementCreateSchema
):

    course = get_object_or_404(
        Course,
        id=data.course_id
    )

    announcement = Announcement.objects.create(
        course=course,
        title=data.title,
        content=data.content
    )

    return success_response(
    "Announcement created successfully",
    {
        "id": announcement.id,
        "title": announcement.title
    }
)


@router.get("/announcements/{announcement_id}")
def get_announcement(
    request,
    announcement_id: int
):

    announcement = get_object_or_404(
        Announcement,
        id=announcement_id
    )

    return success_response(
    "Announcement retrieved successfully",
    {
        "id": announcement.id,
        "course_id": announcement.course.id,
        "title": announcement.title,
        "content": announcement.content,
        "created_at": announcement.created_at
    }
)

# ========================
# DETAIL COURSE
# ========================
@router.get("/{course_id}")
@ratelimit(key="ip", rate="60/m", block=True)
def get_course(request, course_id: int):

    cache_key = f"course_detail_{course_id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return success_response(
            "Course retrieved from cache",
            {
                "source": "redis_cache",
                "course": cached_data
            }
        )

    course = Course.objects.filter(
        id=course_id
    ).values(
        "id",
        "title",
        "description"
    ).first()

    if not course:
        return error_response(
            "Course not found"
        )

    cache.set(
        cache_key,
        course,
        timeout=300
    )

    return success_response(
        "Course retrieved successfully",
        {
            "source": "database",
            "course": course
        }
    )

# ========================
# UPDATE COURSE
# ========================
@router.patch("/{course_id}", auth=JWTAuth())
@require_role(["instructor"])
def update_course(request, course_id: int, data: CourseUpdateSchema):
    user = request.auth
    course = get_object_or_404(Course, id=course_id)

    if course.instructor != user:
        return error_response("Not your course")

    if data.title is not None:
        course.title = data.title

    if data.description is not None:
        course.description = data.description

    course.save()

    log_activity(
        user_id=user.id,
        action="UPDATE_COURSE",
        detail=f"Course ID {course_id} updated"
    )

    cache.delete("course_list")
    cache.delete(f"course_detail_{course_id}")

    return success_response(
    "Course updated successfully",
    {
        "id": course.id,
        "title": course.title,
        "description": course.description
    }
)


# ========================
# DELETE COURSE
# ========================
@router.delete("/{course_id}", auth=JWTAuth())
@require_role(["admin"])
def delete_course(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)

    log_activity(
        user_id=request.auth.id,
        action="DELETE_COURSE",
        detail=f"Course ID {course_id} deleted"
    )

    course.delete()

    cache.delete("course_list")
    cache.delete(f"course_detail_{course_id}")

    return success_response(
    "Course deleted successfully"
)
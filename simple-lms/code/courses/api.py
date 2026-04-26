from ninja import Router, Schema
from typing import List
from django.shortcuts import get_object_or_404

from .models import Course
from .auth import JWTAuth, require_role

router = Router()


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
# LIST (PUBLIC)
# ========================
@router.get("/", response=List[CourseOutSchema])
def list_courses(request):
    return Course.objects.all()


# ========================
# DETAIL (PUBLIC)
# ========================
@router.get("/{course_id}", response=CourseOutSchema)
def get_course(request, course_id: int):
    return get_object_or_404(Course, id=course_id)


# ========================
# CREATE (INSTRUCTOR ONLY) - FIXED
# ========================
@router.post("/", auth=JWTAuth(), response=CourseOutSchema)
@require_role(["instructor"])
def create_course(request, data: CourseCreateSchema):
    user = request.auth

    course = Course.objects.create(
        title=data.title,
        description=data.description,
        instructor=user
    )

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description
    }


# ========================
# UPDATE (OWNER ONLY)
# ========================
@router.patch("/{course_id}", auth=JWTAuth(), response=CourseOutSchema)
@require_role(["instructor"])
def update_course(request, course_id: int, data: CourseUpdateSchema):
    user = request.auth
    course = get_object_or_404(Course, id=course_id)

    if course.instructor != user:
        return {"error": "Not your course"}

    if data.title is not None:
        course.title = data.title

    if data.description is not None:
        course.description = data.description

    course.save()

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description
    }


# ========================
# DELETE (ADMIN ONLY)
# ========================
@router.delete("/{course_id}", auth=JWTAuth())
@require_role(["admin"])
def delete_course(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    course.delete()

    return {"message": "Deleted successfully"}
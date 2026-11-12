from django.contrib import admin

from tasks.forms import TaskAdminForm
from tasks.models import Tag, Task, TaskAssignment, TaskDependency, TaskType
from tasks.services import propagate_task_completion

admin.site.register(TaskType)
admin.site.register(Tag)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskAdminForm
    readonly_fields = ("is_completed",)
    list_display = admin.ModelAdmin.list_display + (
        "name",
        "project",
        "task_type",
        "priority",
        "deadline",
        "is_completed",
    )


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = admin.ModelAdmin.list_display + ("task", "worker", "is_completed")
    actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return super().get_readonly_fields(request, obj)
        read_only_fields = super().get_readonly_fields(request, obj)
        return read_only_fields + ("task", "worker")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        propagate_task_completion(obj.task)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        propagate_task_completion(obj.task)


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = admin.ModelAdmin.list_display + (
        "dependent_task",
        "prerequisite_task",
    )
    actions = None

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return super().get_readonly_fields(request, obj)
        read_only_fields = super().get_readonly_fields(request, obj)
        return read_only_fields + ("dependent_task", "prerequisite_task")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        propagate_task_completion(obj.dependent_task)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        propagate_task_completion(obj.dependent_task)

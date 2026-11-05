from django.contrib import admin

from tasks.models import Tag, Task, TaskAssignment, TaskDependency, TaskType


admin.site.register(TaskType)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ("is_completed",)
    list_display = admin.ModelAdmin.list_display + ("name", "project", "task_type", "priority", "deadline", "is_completed")


admin.site.register(TaskAssignment)
admin.site.register(Tag)
admin.site.register(TaskDependency)
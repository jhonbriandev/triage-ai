from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name = 'Profile'

class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = BaseUserAdmin.list_display +('get_role',)

    def get_role(self,obj):
        return obj.profile.get_role_display()
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if obj is None:  # None = estás creando un usuario nuevo
            return []
        return super().get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User,UserAdmin)
 
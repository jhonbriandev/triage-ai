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

admin.site.unregister(User)
admin.site.register(User,UserAdmin)
 
from django.contrib import admin
from .models import Ticket, Category, SuggestionAi, Commentary

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id','title','status','priority','category','customer','assigned_agent','created_at','updated_at','suggestion_priority']
    list_filter = ['status','priority','category']
    search_fields = ['title','description']
    
    @admin.display(description='Prioridad Sugerida')
    def suggestion_priority(self, obj):
        #Related name + sugerencia de prioridad
        return obj.suggestion_ai.suggestion_priority

@admin.register(Commentary)
class CommentaryAdmin(admin.ModelAdmin):
    list_display = ['ticket','author','created_at']

@admin.register(SuggestionAi)
class SuggestionAiAdmin(admin.ModelAdmin):
    list_display = ['ticket','suggestion_category','suggestion_priority','generated_summary','suggestion_answer','generation_date','updated_at']
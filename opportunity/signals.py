from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


@receiver(post_save, sender=User)
def add_user_to_group_post_save(sender, instance, created, **kwargs):
    if created:
        group = Group.objects.get(name='Basic')
        instance.groups.add(group)
        instance.save()

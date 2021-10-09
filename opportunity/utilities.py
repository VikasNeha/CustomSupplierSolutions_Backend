def get_user_group(user):
    groups = user.groups.values_list('name', flat=True)
    groups = map(lambda x: x.upper(), groups)
    if 'PAID' in groups:
        return 'PAID'
    else:
        return 'BASIC'

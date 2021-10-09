# from django.apps import AppConfig
#
#
# class OpportunityConfig(AppConfig):
#     name = 'opportunity'


from suit.apps import DjangoSuitConfig
from suit.menu import ParentItem, ChildItem


class SuitConfig(DjangoSuitConfig):
    layout = 'vertical'
    menu = (
        ParentItem('Opportunities', children=[
            ChildItem(model='opportunity.opportunitylisting'),
            ChildItem(model='opportunity.buyerlisting'),
        ]),

        ParentItem('CommonAssets', icon='fa fa-database', children=[
            ChildItem(model='opportunity.productservicecategory'),
            ChildItem(model='opportunity.shiptoservicelocation'),
        ]),

        ParentItem('Users', children=[
            ChildItem(model='auth.user'),
            ChildItem('User groups', 'auth.group'),
        ], icon='fa fa-users'),

    )

    list_per_page = 50

    def ready(self):
        import opportunity.signals
        super(SuitConfig, self).ready()

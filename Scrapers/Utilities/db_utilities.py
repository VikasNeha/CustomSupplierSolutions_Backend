from opportunity.models import *


def get_or_create_productservicecategory(title):
    productservicecategory, _ = ProductServiceCategory.objects.get_or_create(title=title)
    return productservicecategory


def get_or_create_naicscode(code, title=None):
    naicscode, is_created = NAICSCode.objects.get_or_create(code=code)
    if is_created and title:
        naicscode.title = title
        naicscode.save()
    return naicscode


def get_or_create_nigpcode(code, title=None):
    nigpcode, is_created = NIGPCode.objects.get_or_create(code=code)
    if is_created and title:
        nigpcode.title = title
        nigpcode.save()
    return nigpcode


def get_or_create_pcscode(code, title=None):
    pcscode, is_created = PSCCode.objects.get_or_create(code=code)
    if is_created and title:
        pcscode.title = title
        pcscode.save()
    return pcscode


def get_or_create_contact(name=None, email=None, phone=None):
    contact, _ = Contact.objects.get_or_create(name=name, email=email, phone=phone)
    return contact


def get_or_create_buyerlisting(website, buyer_name, buyer_url=None, buyer_duns=None):
    buyerlisting, is_created = BuyerListing.objects.get_or_create(website=website, buyer_name=buyer_name,
                                                                  buyer_url=buyer_url)
    if is_created and buyer_duns:
        buyerlisting.duns = buyer_duns
        buyerlisting.save()
    return buyerlisting


def get_or_create_state(state_code, state_name=None):
    state, is_created = State.objects.get_or_create(code=state_code)
    if is_created and state_name:
        state.name = state_name
        state.save()
    return state


def get_or_create_cities(city_name, state_code=None, state_name=None):
    if state_code:
        state = get_or_create_state(state_code, state_name)
        city, _ = City.objects.get_or_create(name=city_name, state=state)
        return city
    else:
        city, _ = City.objects.get_or_create(name=city_name, state=None)
        return city


def get_or_create_businesstype(business_type):
    businesstype, _ = BusinessType.objects.get_or_create(business_type=business_type)
    return businesstype

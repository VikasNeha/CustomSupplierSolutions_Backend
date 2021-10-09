import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()

from time import sleep

import requests
from dateutil.parser import parse as dateutil_parse
from django.db import transaction

from myLogger import logger

from opportunity.models import *
from Scrapers.Utilities import db_utilities


WEBSITE_NAME = 'SAM.GOV'


def requests_get(*args, **kwargs):
    for i in range(5):
        try:
            r = requests.get(*args, **kwargs)
            return r
        except requests.exceptions.ConnectionError:
            if i >= 4:
                raise
            logger.info('Remote Disconnected Issue, retrying...')
            sleep(0.5)
            continue


def get_or_set_setasidecode(set_aside_code):
    setasidecode, is_created = SetAsideCode.objects.get_or_create(code=set_aside_code)
    if is_created:
        url = f'https://beta.sam.gov/api/prod/locationservices/v1/api/setAside?q={set_aside_code}&active=ALL'
        r = requests_get(url).json()
        setasidecode.title = r['_embedded']['setAsideList'][0]['setAsideName']
        setasidecode.save()

    return setasidecode.title


def get_psc_code(classification_code):
    samgovpsccode, is_created = SamGovPSCCode.objects.get_or_create(code=classification_code)
    if is_created:
        url = f'https://beta.sam.gov/api/prod/locationservices/v1/api/psc?q={classification_code}&active=ALL&advanceSearch=N&searchby=psc'
        r = requests_get(url).json()
        samgovpsccode.title = r['_embedded']['productServiceCodeList'][0]['pscName']
        samgovpsccode.save()

    productservicecategory, _ = ProductServiceCategory.objects.get_or_create(title=samgovpsccode.title)
    return productservicecategory


def get_naics_code(naics_code):
    naicscode, is_created = NAICSCode.objects.get_or_create(code=naics_code)
    if is_created:
        url = f'https://beta.sam.gov/api/prod/locationservices/v1/api/naics?active=ALL&q={naics_code}'
        r = requests_get(url).json()
        naicscode.title = r['_embedded']['nAICSList'][0]['naicsTitle']
        naicscode.save()
    return naicscode


def write_single_opportunity_to_db(record_dict):
    posting_id = record_dict['_id']
    if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=posting_id).exists():
        return False

    opportunitylisting = OpportunityListing(
        website=WEBSITE_NAME,
        posting_id=posting_id,
        posting_date=dateutil_parse(record_dict['publishDate']),
        title=record_dict['title'],
        opportunity_type=record_dict['type']['value'],
        solicitation_number=record_dict['solicitationNumber'],
        posting_url=f'https://beta.sam.gov/opp/{posting_id}/view',
    )

    if record_dict['responseDate']:
        response_date = record_dict['responseDate']
        if response_date.startswith('1021'):
            response_date = response_date.replace('1021', '2021')
        if response_date.rindex('-') > response_date.rindex('T') and response_date.endswith(':00'):
            response_date = response_date[:-3]
        opportunitylisting.submission_deadline = dateutil_parse(response_date)

    opportunitylisting.save()

    # Fetch Details
    url = f'https://beta.sam.gov/api/prod/opps/v2/opportunities/{posting_id}'
    r_details = requests_get(url).json()

    # Buyer
    if record_dict['organizationHierarchy']:
        buyer_website_id = record_dict['organizationHierarchy'][0]['organizationId']
        buyer_name = record_dict['organizationHierarchy'][0]['name']
        agency_type = record_dict['organizationHierarchy'][0]['type']
    else:
        url = f'https://beta.sam.gov/api/prod/federalorganizations/v1/organizations/{r_details["data"]["organizationId"]}'
        r = requests_get(url).json()
        buyer_website_id = r_details["data"]["organizationId"]
        buyer_name = r['_embedded'][0]['org']['l1Name']
        agency_type = None

    buyerlisting = BuyerListing.objects.filter(website=WEBSITE_NAME, buyer_website_id=buyer_website_id).first()
    if buyerlisting is None:
        buyerlisting = BuyerListing(website=WEBSITE_NAME, buyer_website_id=buyer_website_id)
    buyerlisting.buyer_name = buyer_name
    buyerlisting.agency_type = agency_type
    buyerlisting.save()

    opportunitylisting.buyer = buyerlisting

    if 'description' in r_details and len(r_details['description']) > 0:
        opportunitylisting.posting_summary = r_details['description'][0]['body']

    # PSC Code
    if 'classificationCode' in r_details['data']:
        opportunitylisting.product_service_categories.add(get_psc_code(r_details['data']['classificationCode']))

    # NAICS Code
    if 'naics' in r_details['data']:
        for naics in r_details['data']['naics']:
            for code in naics['code']:
                opportunitylisting.naics_codes.add(get_naics_code(code))

    # Place of Performance
    if 'placeOfPerformance' in r_details['data']:
        if r_details['data']['placeOfPerformance']:
            if 'streetAddress' in r_details['data']['placeOfPerformance']:
                opportunitylisting.location = r_details['data']['placeOfPerformance']['streetAddress']

            state_code = None
            if 'state' in r_details['data']['placeOfPerformance']:
                state_code = r_details['data']['placeOfPerformance']['state'].get('code', '').strip()
                if state_code == '':
                    state_code = None

            if 'city' in r_details['data']['placeOfPerformance']:
                city_name = r_details['data']['placeOfPerformance']['city'].get('name', '').strip()
                if city_name != '':
                    opportunitylisting.cities.add(db_utilities.get_or_create_cities(
                        city_name=city_name, state_code=state_code))

            if state_code:
                opportunitylisting.states.add(db_utilities.get_or_create_state(state_code=state_code))

    # Set Aside Code
    if 'setAside' in r_details['data'].get('solicitation', ''):
        set_aside_code = r_details['data']['solicitation']['setAside']
        opportunitylisting.set_aside_type = get_or_set_setasidecode(set_aside_code)

    opportunitylisting.save()

    # Contacts
    if 'pointOfContact' in r_details['data']:
        for poc_dict in r_details['data']['pointOfContact']:
            if poc_dict.get('fullName') in [None, ''] and poc_dict.get('email') in [None, ''] and poc_dict.get('phone') in [None, '']:
                continue
            contact, _ = Contact.objects.get_or_create(
                name=poc_dict.get('fullName'), email=poc_dict.get('email'), phone=poc_dict.get('phone'))
            OpportunityContact.objects.create(
                contact=contact,
                opportunitylisting=opportunitylisting,
                contact_website=WEBSITE_NAME,
                position=poc_dict.get('title')
            )

    # Attachments / Files
    url = f'https://beta.sam.gov/api/prod/opps/v3/opportunities/{posting_id}/resources?excludeDeleted=false&withScanResult=false'
    r = requests_get(url).json()
    if '_embedded' in r:
        for attachment_dict in r['_embedded']['opportunityAttachmentList'][0]['attachments']:
            listingattachment = ListingAttachment(
                opportunitylisting=opportunitylisting,
                attachment_name=attachment_dict.get('name', attachment_dict.get('description'))
            )
            if 'http' in attachment_dict.get('uri', ''):
                attachment_url = attachment_dict['uri']
            else:
                attachment_url = f'https://beta.sam.gov/api/prod/opps/v3/opportunities/resources/files/{attachment_dict["resourceId"]}/download'
            listingattachment.attachment_url = attachment_url
            listingattachment.save()

    return True


def save_opportunities_single_page(results_list):
    new_opportunities_records_list_count = 0
    for i, result_dict in enumerate(results_list):
        # print(i + 1)
        with transaction.atomic():
            res = write_single_opportunity_to_db(result_dict)
            if res:
                new_opportunities_records_list_count += 1
    return new_opportunities_records_list_count


def scrape_all_opportunities():
    logger.info('Fetching All Opportunities...')

    url = 'https://beta.sam.gov/api/prod/sgs/v1/search/'
    params = {
        'index': 'opp',
        'q': '',
        'sort': '-modifiedDate',
        'mode': 'search',
        'is_active': 'true',
        'notice_type': 's,p,o,k',
        'size': '1000'
    }

    new_opportunities_count = 0
    for page_count in range(0, 10):
        logger.info(f'\tPage {page_count + 1}')
        params['page'] = page_count

        r = requests_get(url, params=params).json()

        new_opportunities_count += save_opportunities_single_page(r['_embedded']['results'])

    logger.info('{}: New Opportunities Found - {}'.format(WEBSITE_NAME, new_opportunities_count))


if __name__ == '__main__':
    try:
        scrape_all_opportunities()
    except:
        logger.exception(sys.exc_info())

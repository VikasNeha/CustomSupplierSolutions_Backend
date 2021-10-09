import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()


from dateutil.parser import parse as dateutil_parse
from django.db import transaction
from django.utils.timezone import make_aware
import requests
import lxml.html

from constants import USER_AGENT
from myLogger import logger
from Scrapers.Utilities import db_utilities

from opportunity.models import *


LABAVNORG = 'LABAVN.ORG'

POSTINGTYPE_MAPPINGS = {
    'Request For Proposal': 'RFI',
    'Task Order Solicitation': 'RFI',
    'Request For Interest': 'RFQ',
    'Request For Quote': 'RFQ',
    'Request For Qualification  (on-call/as needed)': 'RFQ',
    'Request For Bid': 'RFQ',
    'Request For Qualification  (pre-qualified)': 'RFQ',
    'Request For Qualification': 'RFQ',
    'Reverse Auction Bid': 'RFQ'
}


def step1_fetch_all_open_results_posting_ids():
    logger.info('LABAVN: Fetching All Open Results...')
    postings_ids = []

    url = 'https://www.labavn.org/index.cfm?fuseaction=contract.opportunity_search_results'
    data = {
        'searchfor': '',
        'categorytype': '',
        'bidstatus': '1,2',
        'contracttype': '',
    }

    s = requests.session()
    s.headers.update({'User-Agent': USER_AGENT})

    page_num = 0
    while True:
        page_num += 1
        logger.info('\tLABAVN: Page {}...'.format(page_num))
        data['page'] = page_num

        r = s.post(url, data=data)
        doc = lxml.html.fromstring(r.content.decode())

        for tr in doc.xpath('//div[@class="table-responsive"]/table/tbody/tr'):
            posting_id = tr.xpath('./td')[2].text.strip()
            if posting_id not in postings_ids:
                postings_ids.append(posting_id)

        if 'disabled' in doc.xpath('//ul[contains(@class, "pagination")]/li')[-1].get('class', ''):
            break
    return postings_ids


def scrape_single_posting_id(posting_id):
    if OpportunityListing.objects.filter(website=LABAVNORG, posting_id=posting_id).exists():
        return False
    url = 'https://www.labavn.org/index.cfm?fuseaction=contract.opportunity_view&recordid={}'.format(posting_id)
    r = requests.get(url, headers={'User-Agent': USER_AGENT})
    doc = lxml.html.fromstring(r.content.decode())

    opportunitylisting = OpportunityListing(
        website=LABAVNORG,
        posting_id=posting_id,
        title=doc.xpath('//h1[@class="page-title"]')[0].text.strip(),
        posting_date=make_aware(
            dateutil_parse(doc.xpath('//td[./b[.="Posted:"]]/following-sibling::td')[0].text.strip())),
        submission_deadline=make_aware(dateutil_parse(
            doc.xpath('//td[./b[.="Bid Due:"]]/following-sibling::td')[0].text.strip())),
        posting_summary=lxml.html.tostring(doc.xpath('//td[./b[.="Description:"]]/following-sibling::td')[0],
                                           pretty_print=True).decode().strip(),
        posting_url=url
    )

    try:
        opportunitylisting.opportunity_amount = doc.xpath('//td[./b[.="Budget:"]]/following-sibling::td')[0].text.strip()
    except IndexError:
        pass

    posting_type = doc.xpath('//td[./b[.="Type:"]]/following-sibling::td')[0].text.strip()
    opportunitylisting.posting_type = POSTINGTYPE_MAPPINGS[posting_type]

    opportunitylisting.save()

    # State/City
    opportunitylisting.states.add(db_utilities.get_or_create_state(state_code='CA'))
    opportunitylisting.cities.add(db_utilities.get_or_create_cities(city_name='Los Angeles', state_code='CA'))

    # Product Service Category
    category_name = doc.xpath('//td[./b[.="Category:"]]/following-sibling::td')[0].text.strip()
    productservicecategory = db_utilities.get_or_create_productservicecategory(category_name)
    opportunitylisting.product_service_categories.add(productservicecategory)

    # Department
    department_name = doc.xpath('//td[./b[.="Dept:"]]/following-sibling::td')[0].text.strip()
    opportunitylisting.buyer = db_utilities.get_or_create_buyerlisting(website=LABAVNORG, buyer_name=department_name)

    # NAICS Codes
    try:
        primary_naics_codes = doc.xpath('//td[./b[.="Prime NAICS:"]]/following-sibling::td')[0].text_content().strip().splitlines()
        primary_naics_codes = [(n.split(':')[0].strip(), n.split(':')[1].strip()) for n in primary_naics_codes]
    except IndexError:
        primary_naics_codes = []

    try:
        sub_naics_codes = doc.xpath('//td[./b[.="Sub NAICS:"]]/following-sibling::td')[0].text_content().strip().splitlines()
        sub_naics_codes = [(n.split(':')[0].strip(), n.split(':')[1].strip()) for n in sub_naics_codes]
    except IndexError:
        sub_naics_codes = []

    try:
        other_naics_codes = doc.xpath('//td[./b[.="NAICS:"]]/following-sibling::td')[0].text_content().strip().splitlines()
        other_naics_codes = [(n.split(':')[0].strip(), n.split(':')[1].strip()) for n in other_naics_codes]
    except IndexError:
        other_naics_codes = []

    naics_codes = primary_naics_codes + sub_naics_codes + other_naics_codes

    for naics_code_tuple in naics_codes:
        code, title = naics_code_tuple
        naicscode = db_utilities.get_or_create_naicscode(code, title)
        opportunitylisting.naics_codes.add(naicscode)

    # Contact
    contact_name = doc.xpath('//td[./b[.="Name:"]]/following-sibling::td')[0].text.strip()
    try:
        contact_email = doc.xpath('//td[./b[.="Email:"]]/following-sibling::td/a')[0].text.strip()
    except IndexError:
        contact_email = None
    try:
        contact_phone = doc.xpath('//td[./b[.="Phone:"]]/following-sibling::td')[0].text
        if contact_phone:
            contact_phone = contact_phone.strip()
    except IndexError:
        contact_phone = None
    opportunitylisting.contact = db_utilities.get_or_create_contact(contact_name, contact_email, contact_phone)

    opportunitylisting.save()

    return True


def main():
    postings_ids = step1_fetch_all_open_results_posting_ids()

    logger.info('LABAVN: Fetching Details of All Results...')
    new_leads_count = 0
    for i, posting_id in enumerate(postings_ids):
        logger.info('LABAVN: {}/{}: {}'.format(i+1, len(postings_ids), posting_id))

        with transaction.atomic():
            res = scrape_single_posting_id(posting_id)
        if res:
            new_leads_count += 1
    logger.info('{}: New Opportunities Found - {}'.format(LABAVNORG, new_leads_count))


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception(sys.exc_info())

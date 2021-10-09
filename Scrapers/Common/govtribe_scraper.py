import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()

import json
from time import sleep

import cfscrape
from dateutil.parser import parse as dateutil_parse
from django.db import transaction
import lxml.html

from constants import USER_AGENT
from myLogger import logger

from opportunity.models import *
from Scrapers.Utilities import db_utilities

WEBSITE_NAME = 'GOVTRIBE.COM'


class GovtribeBrowser:
    def __init__(self):
        logger.info('Preparing Browser...')
        self.s = cfscrape.CloudflareScraper()
        self.s.headers.update({'User-Agent': USER_AGENT})
        self.csrf_token = None
        self.authentication_token = None

    def make_request(self, **kwargs):
        for i in range(5):
            r = self.s.request(**kwargs)
            if '<title>Too Many Requests</title>' in r.content.decode() and r.status_code == 429:
                logger.info('Too Many Requests, retrying...')
                sleep(60)
                continue
            else:
                return r

        return r

    def step1_prepare_tokens(self):
        logger.info('Preparing Tokens...')
        r = self.make_request(method='GET', url='https://govtribe.com/')

        doc = lxml.html.fromstring(r.content.decode())
        self.csrf_token = doc.xpath('//meta[@name="csrf-token"]')[0].get('content')
        self.authentication_token = 'Bearer ' + doc.xpath('//meta[@name="pt"]')[0].get('content')

    def step2_fetch_opportunities(self):
        logger.info('Fetching All Opportunities...')
        headers2 = {
            'Accept': 'application/json, text/plain, */*',
            # 'Accept-Encoding': 'gzip',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRF-TOKEN': self.csrf_token,
            'X-XSRF-TOKEN': self.s.cookies['XSRF-TOKEN'],
            'Authorization': self.authentication_token,
            'Referer': 'https://govtribe.com/opportunity/federal-contract-opportunity',
            'Host': 'govtribe.com',
            'Origin': 'https://govtribe.com',
        }

        url = 'https://govtribe.com/api/opportunity/federal-contract-opportunity/search'

        page_count = 0
        opportunities_scraped = []
        new_opportunities_count = 0

        while True:
            page_count += 1
            logger.info(f'\tPage {page_count}...')
            data = {
                "limit": 100,
                "scope": "FederalContractOpportunityModel",
                "q": None,
                "page": page_count,
                "filters": {
                    "condition": "AND",
                    "rules": [{
                            "id": "subtypes.opportunityType",
                            "operator": "in",
                            "value": ["Pre-Solicitation", "Solicitation", "Special Notice"]
                    }]
                },
                "sorts": [
                    {
                        "key": "postedDate",
                        "direction": "desc"
                    }
                ]
            }

            r = self.make_request(method='POST', url=url, data=json.dumps(data), headers=headers2).json()

            new_opportunities_count += self.write_opportunities_to_db_single_page(r['data'])

            new_opportunities_this_page_count = 0
            for record_dict in r['data']:
                if record_dict['_id'] not in opportunities_scraped:
                    opportunities_scraped.append(record_dict['_id'])
                    new_opportunities_this_page_count += 1

            if len(r['data']) == 0 or not r['meta']['has_more_pages']:
                break

            if new_opportunities_this_page_count == 0:
                break

        logger.info('{}: New Opportunities Found - {}'.format(WEBSITE_NAME, new_opportunities_count))

    def get_contact_phone_number(self, contact_url):
        try:
            r = self.make_request(method='GET', url=contact_url)
            r = r.json()
        except:
            print(r.text)
            print(r.status_code)
            raise
        return r['phoneNumber']

    def write_opportunities_to_db_single_page(self, records_list):
        new_opportunities_records_list_count = 0
        for i, record_dict in enumerate(records_list):
            with transaction.atomic():
                res = self.write_single_opportunity_to_db(record_dict)

                if res:
                    sleep(0.5)
                    new_opportunities_records_list_count += 1
        return new_opportunities_records_list_count

    def write_single_opportunity_to_db(self, record_dict):
        posting_id = record_dict['_id']
        if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=posting_id).exists():
            return False

        opportunitylisting = OpportunityListing(
            website=WEBSITE_NAME,
            posting_id=posting_id,
            posting_summary=record_dict.get('descriptionPlain'),
            title=record_dict['name'],
            # TODO: Fill posting_type=None
            opportunity_type=record_dict['opportunityType'],
            set_aside_type=record_dict['setAsideType'],
            solicitation_number=record_dict['originalSolicitationNumber'],
            posting_date=dateutil_parse(record_dict['postedDate']),
            bidding_open_date=dateutil_parse(record_dict['postedDate']),
            submission_deadline=dateutil_parse(record_dict['dueDate']) if 'dueDate' in record_dict else None,
            location=record_dict['location']['formatted_address'] if 'location' in record_dict and record_dict['location'] is not None else None,
            posting_url=record_dict['showUrl'].replace('/api/', '/')
        )

        opportunitylisting.save()

        r = self.make_request(method='GET', url=record_dict['showUrl']).json()

        record_dict = r

        # Federal Agency -> Buyer Listing
        if record_dict['federalAgency'] is not None:
            federal_agency_id = record_dict['federalAgency']['_id']
            buyerlisting = BuyerListing.objects.filter(website=WEBSITE_NAME, buyer_website_id=federal_agency_id).first()
            if buyerlisting is None:
                buyerlisting = BuyerListing(website=WEBSITE_NAME, buyer_website_id=federal_agency_id)
            buyerlisting.buyer_name = record_dict['federalAgency']['name']
            buyerlisting.buyer_url = record_dict['federalAgency']['showUrl']
            buyerlisting.agency_type = record_dict['federalAgency']['defenseOrCivilian']
            buyerlisting.save()

            opportunitylisting.buyer = buyerlisting

            opportunitylisting.save()

        # Federal People -> Contacts
        for people_dict in record_dict['federalPeople']:
            if OpportunityContact.objects.filter(
                    contact_website_id=people_dict['_id'], opportunitylisting=opportunitylisting).exists():
                continue
            contact_phone = self.get_contact_phone_number(people_dict['showUrl'])

            contact = db_utilities.get_or_create_contact(
                name=people_dict['name'], email=people_dict['emailAddress'], phone=contact_phone)

            opportunitycontact = OpportunityContact(
                contact=contact,
                opportunitylisting=opportunitylisting,
                contact_website=WEBSITE_NAME,
                contact_website_id=people_dict['_id'],
                position=people_dict['position']
            )

            opportunitycontact.save()

        # NAICS Category
        if record_dict['NAICSCategory'] is not None:
            naicscode = db_utilities.get_or_create_naicscode(
                code=record_dict['NAICSCategory']['shortDisplayName'], title=record_dict['NAICSCategory']['name'])
            opportunitylisting.naics_codes.add(naicscode)

        # PSC Category
        if record_dict['PSCCategory'] is not None:
            psc_code = record_dict['PSCCategory']['shortDisplayName']
            psc_title = record_dict['PSCCategory']['longDisplayName']
            psc_title = psc_title[psc_title.index('-') + 1:].strip()

            productservicecategory = ProductServiceCategory.objects.filter(title=psc_title).first()
            if productservicecategory is None:
                productservicecategory = ProductServiceCategory(title=psc_title)
            productservicecategory.code = psc_code
            productservicecategory.save()

            opportunitylisting.product_service_categories.add(productservicecategory)
            opportunitylisting.save()

        opportunitylisting.save()

        if 'externalFiles' in r:
            for file_dict in r['externalFiles']:
                ListingAttachment.objects.create(
                    opportunitylisting=opportunitylisting,
                    attachment_url=file_dict['link'][:file_dict['link'].index('?')],
                    attachment_name=file_dict['name']
                )

            # TODO: Download Files

        return True


if __name__ == '__main__':
    try:
        browser = GovtribeBrowser()
        browser.step1_prepare_tokens()
        browser.step2_fetch_opportunities()
    except:
        logger.exception(sys.exc_info())

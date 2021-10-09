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
import re
import urllib.parse

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
    'RFP - REQUEST FOR PROPOSAL': 'RFI',
    'RFB - REQUEST FOR BID': 'RFQ',
    'RFQ - REQUEST FOR QUOTE': 'RFQ',
    'TOS - TASK ORDER SOLICITATION': 'RFI',
    'RFQ - REQUEST FOR QUALIFICATION': 'RFQ',
    'RFI - REQUEST FOR INTEREST': 'RFQ',
    'RAB - REVERSE AUCTION BID': 'RFQ'
}


class LabavnBrowser:
    def __init__(self):
        logger.info(f'{LABAVNORG}: Peparing Browser...')
        self.s = requests.session()
        self.s.headers.update({'User-Agent': USER_AGENT})
        self.secrets_dict = {}

    def prepare_aura_context(self):
        return json.dumps({
            'mode': 'PROD',
            'fwuid': self.secrets_dict['fwuid'],
            'app': self.secrets_dict['app'],
            'loaded': self.secrets_dict['loaded'],
            'dn': [],
            'globals': {},
            'uad': 'false'
        })

    def step1_fetch_required_secrets(self):
        logger.info(f'{LABAVNORG}: Fetching Secrets...')
        url = 'https://labavn.force.com/LABAVN/s/advanced-search'
        r = self.s.get(url)
        secrets_str = re.search(r'<script src="/LABAVN/s/sfsites(.+?)">', r.text).groups()[0]
        secrets_str = urllib.parse.unquote(secrets_str)
        secrets_str = secrets_str[secrets_str.index('{'):secrets_str.rindex('}') + 1]
        self.secrets_dict = json.loads(secrets_str)

    def step2_fetch_all_open_results_posting_ids(self):
        logger.info(f'{LABAVNORG}: Fetching All Open Results...')

        url = 'https://labavn.force.com/LABAVN/s/sfsites/aura'
        headers2 = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        data = {
            'message': '{"actions":[{"descriptor":"apex://MainSearchController/ACTION$searchForIds","callingDescriptor":"markup://c:AdvancedSearch","params":{"searchText":"","category":"","status":"Open","type":"","department":"","onlineBIP":"","industry":"","postedFrom":null,"postedTo":null,"dueFrom":null,"dueTo":null,"summaryDueFrom":null,"summaryDueTo":null,"outreachDueFrom":null,"outreachDueTo":null,"listLimit":1000}}]}',
            'aura.context': self.prepare_aura_context(),
            'aura.token': 'undefined'
        }

        r = self.s.post(url, headers=headers2, data=data).json()

        for action_dict in r['actions']:
            if 'returnValue' in action_dict and isinstance(action_dict['returnValue'], list):
                postings_ids = [d['Id'] for d in action_dict['returnValue']]
                return postings_ids
        return []

    def step3_fetch_soingle_posting_details(self, posting_id):
        url = 'https://labavn.force.com/LABAVN/s/sfsites/aura?other.OpportunityDetail.getOpportunity=1&other.OpportunityDetail.isUserLoggedIn=1'
        headers2 = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        data = {
            'message': '{"actions":[{"descriptor":"apex://OpportunityDetailController/ACTION$isUserLoggedIn","callingDescriptor":"markup://c:OpportunityDetail","params":{}},{"descriptor":"apex://OpportunityDetailController/ACTION$getOpportunity","callingDescriptor":"markup://c:OpportunityDetail","params":{"recordId":"%s"}}]}' % posting_id,
            'aura.context': self.prepare_aura_context(),
            'aura.token': 'undefined'
        }

        r = self.s.post(url, headers=headers2, data=data).json()

        posting_dict = {}

        for action_dict in r['actions']:
            if 'returnValue' in action_dict and isinstance(action_dict['returnValue'], dict):
                posting_dict = action_dict['returnValue']
                break

        opportunitylisting = OpportunityListing(
            website=LABAVNORG,
            posting_id=posting_id,
            title=posting_dict['Name'],
            posting_type=POSTINGTYPE_MAPPINGS[posting_dict['Type'].upper()],
            posting_summary=posting_dict['Description'],
            posting_date=dateutil_parse(posting_dict['Bid_Post__c']),
            submission_deadline=dateutil_parse(posting_dict['Bid_Due__c']),
            posting_url=f'https://labavn.force.com/LABAVN/s/opportunity-details?id={posting_id}'
        )

        opportunitylisting.save()

        # State/City
        opportunitylisting.states.add(db_utilities.get_or_create_state(state_code='CA'))
        opportunitylisting.cities.add(db_utilities.get_or_create_cities(city_name='Los Angeles', state_code='CA'))

        # NAICS Codes
        naics_codes = self.step3a_get_posting_naics(posting_id)
        for naics_code_tuple in naics_codes:
            code, title = naics_code_tuple
            naicscode = db_utilities.get_or_create_naicscode(code, title)
            opportunitylisting.naics_codes.add(naicscode)

        # Product Service Category
        category_name = posting_dict['Category__c']
        productservicecategory = db_utilities.get_or_create_productservicecategory(category_name)
        opportunitylisting.product_service_categories.add(productservicecategory)

        # Department
        department_name = posting_dict['Account']['Name']
        opportunitylisting.buyer = db_utilities.get_or_create_buyerlisting(
            website=LABAVNORG, buyer_name=department_name)

        opportunitylisting.save()

        # Contact
        contact_name = posting_dict['Contact_Name__c']
        contact_email = posting_dict['Contact_Email__c']
        contact_phone = posting_dict.get('Contact_Phone__c', None)
        contact = db_utilities.get_or_create_contact(contact_name, contact_email, contact_phone)

        opportunitycontact = OpportunityContact(
            contact=contact,
            opportunitylisting=opportunitylisting,
            contact_website=LABAVNORG,
            contact_website_id=contact_email
        )

        opportunitycontact.save()

    def step3a_get_posting_naics(self, posting_id):
        url = 'https://labavn.force.com/LABAVN/s/sfsites/aura?other.OpportunityDetail.getNaics=1'
        headers2 = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        data = {
            'message': '{"actions": [{"descriptor": "apex://OpportunityDetailController/ACTION$getNaics", "callingDescriptor": "UNKNOWN", "params": {"recordId": "%s"}}]}' % posting_id,
            'aura.context': self.prepare_aura_context(),
            'aura.token': 'undefined'
        }

        r = self.s.post(url, headers=headers2, data=data).json()

        for action_dict in r['actions']:
            if 'returnValue' in action_dict and isinstance(action_dict['returnValue'], list):
                naics_codes = [
                    (naics_dict['NAICS_Code__r']['Name'],
                     naics_dict['NAICS_Code__r']['NAICS_Description__c']) for naics_dict in action_dict['returnValue']
                ]
                return naics_codes

        return []


def main():
    browser = LabavnBrowser()
    browser.step1_fetch_required_secrets()
    postings_ids = browser.step2_fetch_all_open_results_posting_ids()

    new_leads_count = 0
    for i, posting_id in enumerate(postings_ids):
        if OpportunityListing.objects.filter(website=LABAVNORG, posting_id=posting_id).exists():
            continue
        logger.info(f'{LABAVNORG}: {i+1}/{len(postings_ids)}: {posting_id}...')
        browser.step3_fetch_soingle_posting_details(posting_id)
        new_leads_count += 1

    logger.info(f'{LABAVNORG}: New Opportunities Found - {new_leads_count}')


if __name__ == '__main__':
    main()

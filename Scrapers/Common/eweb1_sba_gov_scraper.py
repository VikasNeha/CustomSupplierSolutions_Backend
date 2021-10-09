import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()

from datetime import datetime
import tempfile

from dateutil.parser import parse as dateutil_parse
from dateutil.parser import ParserError
from django.core import files
from django.db import transaction
from django.utils.timezone import make_aware
import requests
import lxml.html

from constants import USER_AGENT, tzinfos
from myLogger import logger
from Scrapers.Utilities import db_utilities

from opportunity.models import *


WEBSITE_NAME = 'EWEB1.SBA.GOV'


def step1_fetch_all_state_codes():
    logger.info('{}: Fetching All States Codes...'.format(WEBSITE_NAME))
    url = 'https://eweb1.sba.gov/subnet/client/dsp_Landing1.cfm?Selection=&DspMsg='
    r = requests.get(url, headers={'User-Agent': USER_AGENT})
    doc = lxml.html.fromstring(r.content.decode())
    states_codes = [option.get('value') for option in doc.xpath('//select[@name="StateCD"]/option')[1:]]
    return states_codes


def process_single_listing(posting_id, posting_url):
    if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=posting_id).exists():
        return False
    r = requests.get(posting_url, headers={'User-Agent': USER_AGENT})
    if r.status_code == 500:
        return False
    doc = lxml.html.fromstring(r.content.decode())
    doc.make_links_absolute(r.url)

    posting_id = doc.xpath('//span[contains(., "Solicitation (SOL) /") and contains(., " NSS No.")]/following-sibling::text()')[0].strip()
    if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=posting_id).exists():
        return

    opportunitylisting = OpportunityListing(
        website=WEBSITE_NAME,
        posting_id=posting_id,
        title=posting_id,
        posting_summary=lxml.html.tostring(
            doc.xpath('//tr[./th[contains(., " NSS Brief Description:")]]/following-sibling::tr')[0],
            pretty_print=True).decode().strip(),
        posting_type='RFQ',
        posting_url=posting_url
    )

    if doc.xpath('//tr[./th[contains(., "Performance Start Date")]]/following-sibling::tr/td')[0].text is not None:
        opportunitylisting.contract_start_date = make_aware(dateutil_parse(
            doc.xpath('//tr[./th[contains(., "Performance Start Date")]]/following-sibling::tr/td')[0].text.strip()))
    opportunitylisting.posting_date = make_aware(datetime.utcnow())

    if opportunitylisting.posting_date > make_aware(datetime.utcnow()):
        raise Exception('Posting Date is in Future')

    # Submission Deadline
    submission_deadline = doc.xpath('//tr[./th[contains(., "NSS Closing Date")]]/following-sibling::tr/td')[0].text.strip()
    submission_deadline = submission_deadline.replace('.', '')
    submission_deadline_timezone = doc.xpath('//td[contains(text(), "Time Zone")]')[0].text.strip().split(':')[1].strip()

    try:
        opportunitylisting.submission_deadline = dateutil_parse(
            '{} {}'.format(submission_deadline, submission_deadline_timezone), tzinfos=tzinfos)
    except ParserError:
        if 'AM' in submission_deadline:
            submission_deadline = submission_deadline.replace('AM', '')
        elif 'PM' in submission_deadline:
            submission_deadline = submission_deadline.replace('PM', '')
        else:
            raise
        opportunitylisting.submission_deadline = dateutil_parse(
            '{} {}'.format(submission_deadline, submission_deadline_timezone), tzinfos=tzinfos)

    opportunitylisting.save()

    # Buyer
    buyer_name = doc.xpath('//span[.="Business Name: "]/following-sibling::text()')[0].strip()
    buyer_duns = doc.xpath('//span[.="DUNS:"]/following-sibling::text()')[0].strip()
    buyer_url = doc.xpath('//span[.="Website:"]/following-sibling::text()')[0].strip()
    opportunitylisting.buyer = db_utilities.get_or_create_buyerlisting(WEBSITE_NAME, buyer_name, buyer_url, buyer_duns)

    # Contact
    contact_first_name = doc.xpath('//td[contains(text(), "First Name:")]')[0].text.strip().replace('First Name:', '').strip()
    contact_last_name = doc.xpath('//td[contains(text(), "Last Name:")]')[0].text.strip().replace('Last Name:', '').strip()
    contact_name = '{} {}'.format(contact_first_name, contact_last_name)
    try:
        contact_email = doc.xpath('//td[contains(text(), "Email:")]/a')[0].text
    except:
        contact_email = doc.xpath('//span[.="Email:"]/following-sibling::a[.!=""]')[0].text
    if contact_email:
        contact_email = contact_email.strip()
    contact_phone = doc.xpath('//td[contains(text(), "Phone:")]')[0].text.strip().replace('Phone:', '').strip()
    opportunitylisting.contact = db_utilities.get_or_create_contact(contact_name, contact_email, contact_phone)

    # NAICS Codes
    primary_naics_code = doc.xpath('//tr[./th[.="NAICS Code"]]/following-sibling::tr/td')[0].text.strip().split()[0]
    secondary_naics_codes = [c.strip() for c in doc.xpath(
        '//tr[./th[.="Additional NAICS Code"]]/following-sibling::tr/td')[0].text_content().strip().split(';') if c.strip() not in ['', 'N/A']]
    naics_codes = [primary_naics_code] + secondary_naics_codes
    for naics_code in naics_codes:
        naicscode = db_utilities.get_or_create_naicscode(naics_code)
        opportunitylisting.naics_codes.add(naicscode)

    # States/Cities
    states_cities = doc.xpath(
        '//tr[./th[.="Place of Performance"]]/following-sibling::tr/td')[0].text.strip()
    if ':' in states_cities:
        statecode = states_cities.split(':')[0].strip()
        opportunitylisting.states.add(db_utilities.get_or_create_state(statecode))

        cities = states_cities.split(':')[1].strip().split(',')
        for city in cities:
            if city.strip() != '':
                opportunitylisting.cities.add(db_utilities.get_or_create_cities(city, statecode))

    else:
        states_cities = [c.strip() for c in states_cities.split(',') if c.strip() != '']
        for state_city in states_cities:
            statecode = state_city.split(':')[0].strip()
            try:
                city = state_city.split(':')[1].strip()
                if city == '':
                    city = None
            except IndexError:
                city = None
            opportunitylisting.states.add(db_utilities.get_or_create_state(statecode))
            if city:
                opportunitylisting.cities.add(db_utilities.get_or_create_cities(city, statecode))

    # Attachments
    # logger.info('{}: Downloading Files...'.format(WEBSITE_NAME))
    for ahref in doc.xpath('//tr[./th[contains(., "Files Attached:")]]/following-sibling::tr/td/a'):
        filename = ahref.text.replace('/', '').strip()
        fileurl = ahref.get('href')
        r = requests.get(fileurl, stream=True)
        lf = tempfile.NamedTemporaryFile()
        for block in r.iter_content(1024 * 8):
            if not block:
                break
            lf.write(block)

        # print(filename)
        listingattachment = ListingAttachment(opportunitylisting=opportunitylisting)
        listingattachment.attachment.save(filename, files.File(lf), save=True)
        listingattachment.save()

    # Type of Businesses
    types_of_businesses = doc.xpath('//tr[./th[.="Type of Businesses Being Solicited"]]/following-sibling::tr/td')[0].text
    if types_of_businesses:
        types_of_businesses = types_of_businesses.strip()
        types_of_businesses = types_of_businesses.split(',')
        for type_of_business in types_of_businesses:
            if ',' in type_of_business:
                raise Exception('Comma found in type of business - {}'.format(type_of_business))
            opportunitylisting.business_types_solicited.add(db_utilities.get_or_create_businesstype(type_of_business))

    opportunitylisting.save()

    return True


def process_single_state(state_code):
    url = 'https://eweb1.sba.gov/subnet/client/dsp_solicitation_search_result.cfm?StateCode={}&radioIndx=0'.format(
        state_code)
    r = requests.get(url, headers={'User-Agent': USER_AGENT})
    doc = lxml.html.fromstring(r.content.decode())
    doc.make_links_absolute(r.url)
    trs = doc.xpath('//table[@id="MySort"]/tr')

    new_leads_count_state = 0
    for i, tr in enumerate(trs):
        # logger.info('\t{}: {}: {}/{}'.format(WEBSITE_NAME, state_code, i+1, len(trs)))
        posting_id = tr.xpath('.//a')[0].text.strip()
        posting_url = tr.xpath('.//a')[0].get('href')
        try:
            with transaction.atomic():
                res = process_single_listing(posting_id, posting_url)
            if res:
                new_leads_count_state += 1
        except:
            logger.info('Error Occurred - {}: {}'.format(posting_id, posting_url))
            logger.exception(sys.exc_info())
            # print()
    return new_leads_count_state


def main():
    states_codes = step1_fetch_all_state_codes()

    new_leads_count = 0
    for i, state_code in enumerate(states_codes):
        logger.info('{}: {}/{}: {}'.format(WEBSITE_NAME, i+1, len(states_codes), state_code))
        new_leads_count_state = process_single_state(state_code)
        new_leads_count += new_leads_count_state
    logger.info('{}: New Opportunities Found - {}'.format(WEBSITE_NAME, new_leads_count))


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception(sys.exc_info())

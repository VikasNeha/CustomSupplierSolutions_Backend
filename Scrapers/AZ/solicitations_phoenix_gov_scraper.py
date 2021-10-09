import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()

import tempfile

from dateutil.parser import parse as dateutil_parse
from django.core import files
from django.db import transaction
from django.utils.timezone import make_aware
import requests
import lxml.html

from constants import USER_AGENT
from myLogger import logger
from Scrapers.Utilities import db_utilities

from opportunity.models import *


WEBSITE_NAME = 'SOLICITATIONS.PHOENIX.GOV'


def step1_fetch_all_open_results_posting_urls():
    logger.info('{}: Fetching All Open Results...'.format(WEBSITE_NAME))
    postings_urls = []

    url = 'https://solicitations.phoenix.gov/Solicitations?pageSize=25&selectedSearchType=searchByNumber&sort=DueDate&sortDirection=Descending'
    page_num = 0
    while True:
        page_num += 1
        logger.info('{}: Page {}...'.format(WEBSITE_NAME, page_num))
        params = {'page': page_num}
        # r = requests.get(url, params=params, headers={'User-Agent': USER_AGENT})
        r = requests.get(url, params=params)
        if 'Search returned no results. Please check your search term and try again.' in r.content.decode():
            break
        doc = lxml.html.fromstring(r.content.decode())
        doc.make_links_absolute(r.url)
        for tr in doc.xpath('//table[@summary="List of solicitations"]//tr')[1:]:
            posting_url = tr.xpath('./td/a')[0].get('href')
            if posting_url not in postings_urls:
                postings_urls.append(posting_url)

    return postings_urls


def scrape_single_posting(posting_url):
    r = requests.get(posting_url, headers={'User-Agent': USER_AGENT})
    doc = lxml.html.fromstring(r.content.decode())
    doc.make_links_absolute(r.url)

    posting_id = doc.xpath('//label[.="Solicitation/Project Number"]/following-sibling::p')[0].text.strip()
    if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=posting_id).exists():
        return False

    opportunitylisting = OpportunityListing(
        website=WEBSITE_NAME,
        posting_id=posting_id,
        posting_url=posting_url,
        title=doc.xpath('//h1')[0].text.strip(),
        posting_date=make_aware(
            dateutil_parse(doc.xpath('//strong[.="Updated:"]/following-sibling::text()')[0].strip())),
        submission_deadline=make_aware(
            dateutil_parse(doc.xpath('//label[.="Date Due"]/following-sibling::p')[0].text.strip())),
        posting_type='RFQ'
    )

    try:
        opportunitylisting.posting_summary = doc.xpath(
            '//h2[.="Additional Information"]/following-sibling::p')[0].text_content().strip()
    except IndexError:
        pass

    pre_submission_meeting = doc.xpath(
        '//label[.="Pre-Offer Conference/Pre-Submittal Meeting"]/following-sibling::p')[0].text.strip()

    if pre_submission_meeting not in [None, '']:
        opportunitylisting.pre_submission_meeting = make_aware(dateutil_parse(pre_submission_meeting))

    opportunitylisting.save()

    # State/City
    opportunitylisting.states.add(db_utilities.get_or_create_state(state_code='AZ'))
    opportunitylisting.cities.add(db_utilities.get_or_create_cities(city_name='Phoenix', state_code='AZ'))

    opportunitylisting.save()

    department = doc.xpath('//label[.="Department"]/following-sibling::p')[0].text.strip()
    opportunitylisting.buyer = db_utilities.get_or_create_buyerlisting(website=WEBSITE_NAME, buyer_name=department)

    # Contact
    contact_name = doc.xpath('//label[.="Contract Specialist/Procurement Officer"]/following-sibling::p/a')[0].text.strip()
    contact_email = doc.xpath('//label[.="Contract Specialist/Procurement Officer"]/following-sibling::p/a')[0].get('href').replace('mailto:', '').strip()
    opportunitylisting.contact = db_utilities.get_or_create_contact(contact_name, contact_email)

    # NIGP
    nigp = doc.xpath('//label[.="NIGP"]/following-sibling::p')[0].text.strip()
    nigp_code = nigp.split(' - ')[0]
    nigp_title = nigp.split(' - ')[1]
    nigpcode = db_utilities.get_or_create_nigpcode(nigp_code, nigp_title)
    opportunitylisting.nigp_codes.add(nigpcode)

    opportunitylisting.save()

    # Attachments
    logger.info('{}: Downloading Files...'.format(WEBSITE_NAME))
    for file_ahref in doc.xpath('//h2[.="Associated Files"]/following-sibling::ul/li//a'):
        att_url = file_ahref.get('href')
        r = requests.get(att_url, stream=True)
        file_name = r.headers['Content-Disposition'].split(';')[1].split('=')[1].strip()
        lf = tempfile.NamedTemporaryFile()
        for block in r.iter_content(1024 * 8):
            if not block:
                break
            lf.write(block)

        # print(file_name)
        listingattachment = ListingAttachment(opportunitylisting=opportunitylisting)
        listingattachment.attachment.save(file_name, files.File(lf), save=True)
        listingattachment.save()

    return True


def main():
    postings_urls = step1_fetch_all_open_results_posting_urls()

    logger.info('{}: Fetching Details of All Results...'.format(WEBSITE_NAME))
    new_leads_count = 0
    for i, posting_url in enumerate(postings_urls):
        logger.info('{}: {}/{}: {}'.format(WEBSITE_NAME, i + 1, len(postings_urls), posting_url))

        with transaction.atomic():
            res = scrape_single_posting(posting_url)
        if res:
            new_leads_count += 1
    logger.info('{}: New Opportunities Found - {}'.format(WEBSITE_NAME, new_leads_count))


if __name__ == '__main__':
    try:
        main()
    except:
        logger.exception(sys.exc_info())

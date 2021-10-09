import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()


import lxml.html
import requests
from dateutil.parser import parse as dateutil_parse
from dateutil.parser import ParserError

from constants import USER_AGENT, GRANTWATCH_USERNAME, GRANTWATCH_PASSWORD
from myLogger import logger
from opportunity.models import *


WEBSITE_NAME = 'GRANTWATCH.COM'


class GrantWatchBrowser:
    def __init__(self):
        logger.info('GrantWatchB: Preparing Browser...')
        self.s = requests.session()
        self.s.headers.update({'User-Agent': USER_AGENT})

    def login(self, username, password):
        logger.info('GrantWatch: Logging In...')
        url = 'https://www.grantwatch.com/join-login.php?vw=login'
        self.s.get(url)

        url = 'https://www.grantwatch.com/join-login.php'
        data = {
            'email': username,
            'password': password,
            'action': 'login',
            'hid_gid': ''
        }
        r = self.s.post(url, data=data)
        if 'join-login.php' in r.url:
            logger.info('\tGrantWatch: LOGIN FAILED!')
            return False

        logger.info('\tGrantWatch: Login Successful!')
        return True

    def scrape_single_opportunity(self, grant_id):
        if OpportunityListing.objects.filter(website=WEBSITE_NAME, posting_id=grant_id).exists():
            return False

        url = f'https://www.grantwatch.com/grant/{grant_id}/'

        logger.info(f'\tGrantWatch: Scraping {url}')
        r = self.s.get(url)
        doc = lxml.html.fromstring(r.content.decode())
        doc.make_links_absolute(r.url)

        opportunitylisting = OpportunityListing(
            website=WEBSITE_NAME,
            posting_id=grant_id,
            posting_type='GRANT',
            opportunity_type='GRANT',
            posting_url=url,
            title=' '.join(doc.xpath('//div[@class="grntdetboxmain"]/h4')[0].text_content().strip().split())
        )

        deadline = doc.xpath(
            '//div[contains(@class, "ddlinedtgwhmdetnew") and contains(., "Deadline Date")]/following-sibling::div')[
            0].text_content().strip()
        if 'ONGOING' in deadline.upper():
            opportunitylisting.is_deadline_ongoing = True
        else:
            deadline = deadline.replace('Central Time', 'CT')
            try:
                opportunitylisting.submission_deadline = dateutil_parse(deadline)
            except ParserError:
                if '/' in deadline:
                    deadline = deadline.split('/')[0].strip()
                opportunitylisting.submission_deadline = dateutil_parse(deadline)

        # Description
        description = []

        for desc_div in doc.xpath('//div[@class="grntdetboxmainlst"]'):
            heading = desc_div.xpath('./div[contains(@class, "ddlinedtgwhmdetnew")]/h3')[0].text_content().strip()

            if 'share it' in heading.lower() or 'deadline date' in heading.lower() or \
                    'grantwatch id' in heading.lower() or 'eligibility' in heading.lower():
                continue

            try:
                text = lxml.html.tostring(desc_div.xpath('./div[contains(@class, "grndetpgboxtext")]')[0],
                                          pretty_print=True).decode().strip()
            except IndexError:
                continue

            description.append(f'<strong>{heading}</strong>')
            description.append(text)

        posting_summary = '<br/>'.join(description)
        opportunitylisting.posting_summary = posting_summary

        opportunitylisting.save()

        # Attachments
        attachments_ahrefs = doc.xpath(
            '//div[contains(@class, "ddlinedtgwhmdetnew") and contains(., "Attached Files")]/following-sibling::div//a')
        for ahref in attachments_ahrefs:
            listingattachment = ListingAttachment(
                opportunitylisting=opportunitylisting,
                attachment_name=ahref.text_content().strip(),
                attachment_url=ahref.get('href')
            )

            listingattachment.save()

        return True

    def scrape_single_opportunity_single_page(self, doc):
        for grant_div in doc.xpath('//div[@class="grnhomegbox"]'):
            grant_id = grant_div.xpath('./div[@class="gridgwhm"]/span')[0].text.strip()
            self.scrape_single_opportunity(grant_id)

    def scrape_all_opportunities(self):
        logger.info('GrantWatch: Scraping All Opportunities...')
        # url = 'https://www.grantwatch.com/all-grants.php'
        url = 'https://www.grantwatch.com/new-grants.php'

        page_count = 0
        while True:
            page_count += 1
            logger.info(f'\tPage {page_count}')
            r = self.s.get(url)
            doc = lxml.html.fromstring(r.content.decode())
            doc.make_links_absolute(r.url)

            self.scrape_single_opportunity_single_page(doc)

            current_page_href = doc.xpath('//ul[contains(@class, "pagination")]/li[@class="active"]/a')[0].get('href')
            last_page_href = doc.xpath('//ul[contains(@class, "pagination")]/li/a')[-1].get('href')

            if current_page_href == last_page_href:
                break

            url = doc.xpath(
                '//ul[contains(@class, "pagination")]/li[@class="active"]/following-sibling::li/a')[0].get('href')


if __name__ == '__main__':
    try:
        grantwatchbrowser = GrantWatchBrowser()
        if grantwatchbrowser.login(GRANTWATCH_USERNAME, GRANTWATCH_PASSWORD):
            grantwatchbrowser.scrape_all_opportunities()
            # grantwatchbrowser.scrape_single_opportunity('186927')
    except:
        logger.exception(sys.exc_info())

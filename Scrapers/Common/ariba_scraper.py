import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
root_path = os.path.join(root_path, os.pardir, os.pardir)

sys.path.insert(0, os.path.join(root_path, 'OpportunityURL'))
sys.path.insert(0, root_path)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpportunityURL.settings")
django.setup()

import string
import time
from urllib.parse import urlparse, parse_qs

from dateutil.parser import parse as dateutil_parse
from django.db import transaction
from django.utils.timezone import make_aware
import requests
import lxml.html

from constants import USER_AGENT, ARIBA_USERNAME, ARIBA_PASSWORD
from myLogger import logger

from opportunity.models import *


ARIBA = 'ARIBA'
awrs = [c for c in string.ascii_lowercase]
tzinfos = {"MDT": "UTC-6", "MST": "UTC-7"}


class AribaBrowser:
    def __init__(self):
        logger.info('Ariba: Preparing Browser...')
        self.s = requests.session()
        self.s.headers.update({'User-Agent': USER_AGENT})
        self.awssk = None
        self.main_url = None
        self.last_response = None
        self.referer_url = None
        self.awr = 1

        # self.s.proxies.update({'http': 'http://127.0.0.1:8888', 'https': 'http://127.0.0.1:8888'})
        # self.s.verify = False

    def increment_awr(self):
        if isinstance(self.awr, int):
            self.awr = 'a' if self.awr == 9 else self.awr + 1
        else:
            self.awr = 10 if self.awr == 'z' else awrs[awrs.index(self.awr)+1]

    def login(self, username, password):
        logger.info('Ariba: Opening Login Page...')
        url = 'https://service.ariba.com/Discovery.aw'
        r = self.s.get(url)
        self.increment_awr()
        self.main_url = 'https://service.ariba.com%s' % urlparse(r.url).path
        self.awssk = parse_qs(urlparse(r.url).query)['awssk'][0]
        self.referer_url = r.url
        doc = lxml.html.fromstring(r.content.decode())

        headers2 = {
            'Referer': self.referer_url,
            'Content-type': 'text/html',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        params = {
            'awr': self.awr,
            'awssk': self.awssk,
            'awsn': '_tkajod',
            'awst': 0,
            'awsl': 0,
            'awii': 'xmlhttp'
        }
        self.s.cookies.update({'awscreenstats': '1920x1080'})
        r = self.s.get(self.main_url, headers=headers2, params=params)
        self.increment_awr()
        doc = lxml.html.fromstring(r.content.decode())

        logger.info('Ariba: Logging In...')
        form = doc.xpath('//form[@name="loginForm"]')[0]
        url = 'https://service.ariba.com/Authenticator.aw/ad/login/SSOActions'
        headers2 = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Referer': self.referer_url,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://service.ariba.com'
        }
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            'clientTime': int(time.time() * 1000),
            'clientTimezone': '',
            'Password': password,
            'UserName': username,
            'timezone': '-330',
            'timezoneApr': '',
            'timezoneAug': '-330',
            'timezoneFeb': '-330',
            'timezoneMar': '',
            'timezoneOffset': '19800000:19800000'
        })
        self.last_response = self.s.post(url, headers=headers2, data=data)
        self.increment_awr()
        doc = lxml.html.fromstring(self.last_response.content.decode())

        if doc.xpath('//title')[0].text.strip().upper() == 'ARIBA DISCOVERY':
            logger.info('\tAriba: Login Sucessful!')
            return True
        else:
            logger.info('\tAriba: Login FAILED!')
            return False

    def open_all_leads_page(self):
        logger.info('Ariba: Opeaning All Leads Page...')
        self.awr = 5
        params = {'awr': self.awr, 'awssk': self.awssk}
        headers2 = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.referer_url
        }
        doc = lxml.html.fromstring(self.last_response.content.decode())
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            '_jnbhs': 3,
            'awii': 'xmlhttp',
            'awr': self.awr,
            'awrv': 'AW5',
            'awsl': 0,
            'awsn': '%s,%s' % (doc.xpath('//a[@_mid="QuoteMarketplaceMain"]')[0].get('id'),
                               doc.xpath('//a[@bh="PMI" and contains(., "All Leads")]')[0].get('id')),
            'awssk': self.awssk,
            'awst': 0
        })

        r = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()
        if 'redirectRefresh' not in r.content.decode():
            raise Exception('Ariba: Exception: All Leads Page didnt open!')
        r = self.s.get(self.main_url, headers=headers2, params={'awh': 'r', 'awssk': self.awssk, 'awrdt': 1})

        logger.info('Ariba: Filtering only Open Postings...')
        params = {'awr': self.awr, 'awssk': self.awssk}
        doc = lxml.html.fromstring(r.content.decode())
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            '_jnbhs': 0,
            'awii': 'xmlhttp',
            'awr': self.awr,
            'awrv': 'AW5',
            'awsl': 0,
            'awsn': doc.xpath('//a[@bh="HL" and .="Open"]')[0].get('id'),
            'awssk': self.awssk,
            'awst': 0,
            'PageErrorPanelIsMinimized': 'false'
        })
        r = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()

        logger.info('Ariba: All Leads Sorting By Date Most Recent...')
        params = {'awr': self.awr, 'awssk': self.awssk}
        doc = lxml.html.fromstring(r.content.decode())
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            '_jnbhs': 3,
            'awsn': '_jnbhs',
            'awr': self.awr,
            'awst': 0,
            'awsl': 0,
            'awssk': self.awssk,
            'awrv': 'AW5',
            'awii': 'xmlhttp'
        })
        self.last_response = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()

    def back_to_search_results(self):
        doc = lxml.html.fromstring(self.last_response.content.decode())
        params = {'awr': self.awr, 'awssk': self.awssk}
        headers2 = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.referer_url
        }
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            'awr': self.awr,
            '_d_cpsb': ' Ask Buyer a question...',
            'awii': 'xmlhttp',
            'awrv': 'AW5',
            'awsl': '0',
            'awsn': doc.xpath('//a[@bh="HL" and contains(., "Back to Search Results")]')[0].get('id'),
            'awssk': self.awssk,
            'awst': 0
        })

        r = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()

        if 'redirectRefresh' not in r.content.decode():
            raise Exception('Ariba: Exception: Single Lead Page didnt open!')
        self.last_response = self.s.get(self.main_url, headers=headers2,
                                        params={'awh': 'r', 'awssk': self.awssk, 'awrdt': 1})

    def scrape_single_lead(self, result_aid):
        doc = lxml.html.fromstring(self.last_response.content.decode())
        params = {'awr': self.awr, 'awssk': self.awssk}
        headers2 = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.referer_url
        }
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            '_jnbhs': 3,
            'awii': 'xmlhttp',
            'awr': self.awr,
            'awrv': 'AW5',
            'awsl': '0',
            'awsn': result_aid,
            'awssk': self.awssk,
            'awst': 164
        })

        r = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()
        if 'redirectRefresh' not in r.content.decode():
            raise Exception('Ariba: Exception: Single Lead Page didnt open!')
        self.last_response = self.s.get(self.main_url, headers=headers2, params={'awh': 'r', 'awssk': self.awssk})
        doc = lxml.html.fromstring(self.last_response.content.decode())

        if len(doc.xpath('//ul[@class="anrf-NTUI-postTerritoriesList"]/following-sibling::div[@class="expandLink"]')) > 0:
            params = {'awr': self.awr, 'awssk': self.awssk}
            form = doc.xpath('//form')[0]
            data = {}
            for input_elem in form.xpath('.//input[@type="hidden"]'):
                data[input_elem.get('name')] = input_elem.get('value')
            data.update({
                'awr': self.awr,
                '_d_cpsb': ' Ask Buyer a question...',
                'awii': 'xmlhttp',
                'awrv': 'AW5',
                'awsl': '0',
                'awsn': doc.xpath('//ul[@class="anrf-NTUI-postTerritoriesList"]/following-sibling::div[@class="expandLink"]/a')[0].get('id'),
                'awssk': self.awssk,
                'awst': 0
            })
            self.last_response = self.s.post(self.main_url, headers=headers2, params=params, data=data)
            self.increment_awr()
            doc = lxml.html.fromstring(self.last_response.content.decode())

        with transaction.atomic():
            res = save_opprotunity_to_db(doc)

        try:
            print(doc.xpath('//title')[0].text)
        except:
            print(doc.xpath('//span[@class="postingHeaderTitle"]')[0].text_content().strip())

        return res

    def scrape_leads_single_page(self):
        doc = lxml.html.fromstring(self.last_response.content.decode())
        result_aids = [ahref.get('id') for ahref in doc.xpath('//a[@class="QuoteSearchResultTitle"]')]

        new_leads_on_page_count = 0
        for result_aid in result_aids:
            res = self.scrape_single_lead(result_aid)

            if res == 'EXISTS':
                return res, new_leads_on_page_count
            new_leads_on_page_count += 1
            self.back_to_search_results()
        return 'SUCCESS', new_leads_on_page_count

    def search_results_next_page(self):
        doc = lxml.html.fromstring(self.last_response.content.decode())
        params = {'awr': self.awr, 'awssk': self.awssk}
        headers2 = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.referer_url
        }
        form = doc.xpath('//form')[0]
        data = {}
        for input_elem in form.xpath('.//input[@type="hidden"]'):
            data[input_elem.get('name')] = input_elem.get('value')
        data.update({
            'awr': self.awr,
            '_jnbhs': 3,
            'awii': 'xmlhttp',
            'awrv': 'AW5',
            'awsl': 0,
            'awsn': doc.xpath('//div[@id="pagination"]/div[@id="next"]/a')[0].get('id'),
            'awssk': self.awssk,
            'awst': 0
        })

        self.last_response = self.s.post(self.main_url, headers=headers2, params=params, data=data)
        self.increment_awr()

    def scrape_all_leads(self):
        logger.info('Ariba: Scraping All Leads...')
        page_num = 0

        new_leads_count = 0
        while True:
            page_num += 1
            logger.info('\tAriba: Scraping All Leads (Page {})...'.format(page_num))
            res, new_leads_on_page_count = self.scrape_leads_single_page()
            new_leads_count += new_leads_on_page_count
            if res == 'EXISTS':
                break

            doc = lxml.html.fromstring(self.last_response.content.decode())
            if len(doc.xpath('//div[@id="pagination"]/div[@id="next"]/a')) == 0:
                break
            self.search_results_next_page()

        logger.info('Ariba: New Opportunities Found - {}'.format(new_leads_count))


def save_opprotunity_to_db(doc):
    posting_id = doc.xpath('//td[./span[contains(., "Posting ID")]]/following-sibling::td')[0].text.strip().split('(')[0]

    if OpportunityListing.objects.filter(website=ARIBA, posting_id=posting_id).exists():
        return 'EXISTS'

    # print(lxml.html.tostring(doc, pretty_print=True))

    opportunitylisting = OpportunityListing(
        website=ARIBA,
        posting_id=posting_id,
        posting_date=make_aware(
            dateutil_parse(
                doc.xpath('//div[@class="ADPostingSubSectionText" and contains(., "Posted On")]')[0].text.replace(
                    'Posted On:', '').strip())),
        bidding_open_date=make_aware(
            dateutil_parse(
                doc.xpath(
                    '//div[@class="ADPostingSubSectionText" and contains(., "Open for bidding on")]')[0].text.replace(
                    'Open for bidding on:', '').strip())),
        submission_deadline=dateutil_parse(
            doc.xpath('//div[@class="ADPostingSubSectionText" and contains(., "Response Deadline")]')[0].text.replace(
                'Response Deadline:', '').strip(),
            tzinfos=tzinfos),
        opportunity_amount=doc.xpath('//span[@class="postingProjectAmount"]')[0].text_content().strip(),
        posting_url=doc.xpath('//td[./span[contains(., "Public Posting")]]/following-sibling::td//a')[0].get('href'),
    )

    try:
        opportunitylisting.title = doc.xpath('//span[@class="postingHeaderTitle"]/span')[0].get('title')
    except IndexError:
        opportunitylisting.title = doc.xpath('//span[@class="postingHeaderTitle"]')[0].text.strip()

    try:
        opportunitylisting.contract_length = doc.xpath(
            '//td[./span[contains(., "Contract Length")]]/following-sibling::td')[0].text.strip()
    except IndexError:
        pass

    posting_type = doc.xpath('//td[./span[contains(., "Posting Type")]]/following-sibling::td')[0].text.strip()
    posting_type = posting_type.replace('(ERP)', '').strip()
    if posting_type.upper() == 'REQUEST FOR QUOTATION':
        opportunitylisting.posting_type = 'RFQ'
    elif posting_type.upper() == 'REQUEST FOR INFORMATION':
        opportunitylisting.posting_type = 'RFI'
    else:
        raise Exception('ARIBA: Unknown Posting Type: {}'.format(posting_type))

    try:
        opportunitylisting.posting_summary = lxml.html.tostring(
            doc.xpath(
                '//div[@class="ADSubSectionSmallerFont" and contains(., "Posting Summary")]/following-sibling::div')[0],
            pretty_print=True).decode().strip()
    except IndexError:
        pass

    # Buyer
    try:
        buyer_url = doc.xpath('//td[./span[contains(., "Company Public Profile")]]/following-sibling::td//a')[0].get('href')
    except IndexError:
        buyer_url = None
    buyer_name = doc.xpath('//span[contains(@class, "buyerCompanyName")]')[0].text.strip()

    buyer, _ = BuyerListing.objects.get_or_create(website=ARIBA, buyer_name=buyer_name, buyer_url=buyer_url)

    opportunitylisting.buyer = buyer
    opportunitylisting.save()

    # Product/Service Category
    for li in doc.xpath('//div[@class="ADSubSectionSmallerFont" and contains(., "Product and Service Categories")]/following-sibling::div/ul/li'):
        product_service_category = li.text.strip()
        productservicecategory, _ = ProductServiceCategory.objects.get_or_create(title=product_service_category)
        opportunitylisting.product_service_categories.add(productservicecategory)

    # Ship To Service Locations
    count = 0
    for li in doc.xpath('//div[@class="ADSubSectionSmallerFont" and contains(., "Ship-to or Service Locations")]/following-sibling::div/ul/li'):
        shipto_service_location = li.text.strip()
        shiptoservicelocation, _ = ShiptoServiceLocation.objects.get_or_create(location_name=shipto_service_location)
        opportunitylisting.shipto_service_locations.add(shiptoservicelocation)
        count += 1
    if count == 0:
        shipto_service_location = ' '.join(doc.xpath('//div[@class="ADSubSectionSmallerFont" and contains(., "Ship-to or Service Locations")]/following-sibling::div')[0].text_content().strip().split())
        shiptoservicelocation, _ = ShiptoServiceLocation.objects.get_or_create(location_name=shipto_service_location)
        opportunitylisting.shipto_service_locations.add(shiptoservicelocation)

    opportunitylisting.save()

    return 'SUCCESS'


if __name__ == '__main__':
    try:
        aribabrowser = AribaBrowser()
        aribabrowser.login(ARIBA_USERNAME, ARIBA_PASSWORD)
        aribabrowser.open_all_leads_page()
        aribabrowser.scrape_all_leads()
    except:
        logger.exception(sys.exc_info())

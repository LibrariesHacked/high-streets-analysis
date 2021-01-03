import csv
import requests
import re
from bs4 import BeautifulSoup

POSTCODE_RE = '(([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2}))'
URL = 'https://www.waterstones.com/bookshops/viewall/page/'
DATA_OUTPUT = 'waterstones.csv'


def getPage(url):
  html = requests.get(url)
  soup = BeautifulSoup(html.text, 'html.parser')
  return soup


def run():

  with open(DATA_OUTPUT, 'w', encoding='utf8', newline='') as out_csv:
    writer = csv.writer(out_csv, delimiter=',',
                        quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['postcode'])
    page = 1
    page_data = getPage(URL + str(page))

    while (len(page_data.find_all('a', {"class": "shop-address"})) > 0):
      addresses = page_data.find_all('a', {"class": "shop-address"})

      for address in addresses:
        address_str = address.string
        postcode = ''

        postcode_match = re.compile(POSTCODE_RE).search(address_str)
        if postcode_match:
          postcode = postcode_match.group(1)
        if 'WN1 1 BH' in address_str:
          postcode = 'WN1 1BH'

        if postcode != '':
          writer.writerow([postcode])

      page = page + 1
      page_data = getPage(URL + str(page))


run()

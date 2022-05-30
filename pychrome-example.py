#!/usr/bin/env python3
"""
Extensive example script for using pychrome.

In order to use this script, you have to start Google Chrome/Chromium
with remote debugging as follows:
    google-chrome --remote-debugging-port=9222 --enable-automation

You can also run in headless mode, which doesn't require a graphical
user interface by supplying --headless.
"""
import pprint
from typing import List

import pychrome
import csv
import json
from urllib.parse import urlparse
from urllib.parse import parse_qs
from adblockparser import AdblockRules
import numpy as np
import matplotlib.pyplot as plt

no_of_Reponse = 0
no_of_HSTS = 0
no_response_list = []
no_hsts = []
no_urls = []

total_blocked_url = 0
blocked_list = []

def read_raw_rules():
    # Reading from file
    raw_rules = []
    with open("easylist.txt", 'r', encoding="utf-8") as file:
        for line in file:
            raw_rules.append(line)
    return raw_rules


def read_from_input_txt() -> List[str]:
    # Reading from file
    rows = []
    with open("input_urls.txt", 'r') as file:
        for line in file:
            rows.append(line)
    return rows

def write_to_file(page_url: str, ga_enabled: bool, anonymize_ip: bool):
    with open("output.csv", 'a') as csvfile:
        # creating a csv writer object
        csvwriter = csv.writer(csvfile)

        # writing the fields
        csvwriter.writerow([page_url, ga_enabled, anonymize_ip])

def update_hsts_list(page_url: str):
    global no_of_Reponse
    global no_of_HSTS
    global no_response_list
    global no_hsts
    global no_urls

    global total_blocked_url
    global blocked_list

    no_urls.append(page_url)
    no_response_list.append(no_of_Reponse)
    no_hsts.append(no_of_HSTS)
    blocked_list.append(total_blocked_url)


def plot_hsts_bar(page_url: str):
    global no_response_list
    global no_hsts
    global no_urls
    y = no_urls
    x1 = no_hsts
    x2 = no_response_list
    
    # plot bars in stack manner
    b1 = plt.barh(y, x1, color='r')
    b2 = plt.barh(y, x2, left=x1, color='b')
    plt.legend([b1, b2], ["HSTS enabled", "HSTS not included"], loc="upper right")
    plt.xlabel('# of HTTP requests')
    plt.ylabel('URLs')
    plt.show()

def plot_blocked_bar(page_url: str):
    global no_urls
    global blocked_list
    x = no_urls
    y = blocked_list
    
    plt.bar(x, y)
    
    plt.xlabel("URLs")
    plt.ylabel("# of blocked requests")  
    # plt.title(" Vertical bar graph")
    plt.show()



class Crawler:
    def __init__(self, debugger_url='http://127.0.0.1:9222'):
        # Create a browser instance which controls Google Chrome/Chromium.
        self.browser = pychrome.Browser(url=debugger_url)
        self.ga_enabled = False
        self.anonymize_ip = False

    def crawl_page(self, url, rules):
        # Initialize _is_loaded variable to False. It will be set to True
        # when the loadEventFired event occurs.
        self._is_loaded = False
        self.ga_enabled = False
        self.anonymize_ip = False
        self.rules = rules

        # Create a tab
        self.tab = self.browser.new_tab()

        # Set callbacks for request in response logging.
        self.tab.Network.requestWillBeSent = self._event_request_will_be_sent
        self.tab.Network.responseReceived = self._event_response_received
        self.tab.Page.loadEventFired = self._event_load_event_fired

        # Start our tab after callbacks have been registered.
        self.tab.start()

        # Enable network notifications for all request/response so our
        # callbacks actually receive some data.
        self.tab.Network.enable()

        # Enable page domain notifications so our load_event_fired
        # callback is called when the page is loaded.
        self.tab.Page.enable()

        # Navigate to a specific page
        self.tab.Page.navigate(url=url, _timeout=15)

        # We wait for our load event to be fired (see `_event_load_event_fired`)
        while not self._is_loaded:
            self.tab.wait(1)

        # Wait some time for events, after the page has been loaded to look
        # for further requests from JavaScript
        self.tab.wait(10)

        # Run a JavaScript expression on the page.
        # If Google Analytics is included in the page, this expression will tell you
        # whether the site owner's wanted to enable anonymize IP. The expression will
        # fail with a JavaScript exception if Google Analytics is not in use.
        result = self.tab.Runtime.evaluate(expression="ga.getAll()[0].get('anonymizeIp')")
        print(result)
        val = result['result']
        key = 'value' in val
        if  key:
            self.ga_enabled = True
            print("AnonymizeIp enabled")
        else:
            if result['result']['type'] == "undefined":
                self.ga_enabled = True
                print("Google analytics is enabled but anonymizeIp is not used")
            else:
                self.ga_enabled = False
                print("Google analytics is not used")

        # Stop the tab
        self.tab.stop()

        # Close tab
        self.browser.close_tab(self.tab)

    def _event_request_will_be_sent(self, request, **kwargs):
        """Will be called when a request is about to be sent.

        Those requests can still be blocked or intercepted and modified.
        This example script does not use any blocking or intercepting.

        Note: It does not say anything about the request being sucessful,
        there can still be connection issues.
        """
        global total_blocked_url
        print("Request: ")
        url = request['url']
        if self.rules.should_block(url):
            total_blocked_url = total_blocked_url + 1
        print(total_blocked_url)

    def _event_response_received(self, response, **kwargs):
        """Will be called when a response is received.

        This includes the originating request which resulted in the
        response being received.
        """

        # with open("response.json", "w") as outfile:
        #     json.dump(response, outfile)

        print("Response: ")
        # # pprint.pprint(response)
        # responseList.append(response)
        # with open("response.json", "w") as outfile:
        #     json.dump(responseList, outfile)
        global no_of_Reponse
        global no_of_HSTS
        no_of_Reponse = no_of_Reponse + 1
        
        dict_http_response_header = response['headers']
        key = 'strict-transport-security' in dict_http_response_header
        if key:
            no_of_HSTS = no_of_HSTS + 1
        
        print("total http response: ")
        print(no_of_Reponse)
        
        print("total HSTS: ")
        print(no_of_HSTS)


    def _event_load_event_fired(self, timestamp, **kwargs):
        """Will be called when the page sends an load event.

        Note that this only means that all resources are loaded, the
        page may still processes some JavaScript.
        """
        self._is_loaded = True

    def check_anonymize_ip(self, request):
        url = request['url']
        try:
            parsed_url = urlparse(url)
            aip = parse_qs(parsed_url.query)['aip'][0]
            if int(aip) == 1:
                self.ga_enabled = True
                self.anonymize_ip = True
        except Exception:
            print("aip is not present in the current url ", url)

    # def check_advertising_tracker(self, request):
    #     url = request['url']
    #     print("should block advertising tracker ", self.rules.should_block(url))

    # def check_non_advertising_tracker(self, request):
    #     url = request['url']
    #     print("should block non advertising tracker ", self.rules.should_block(url))

def main():
    c = Crawler()

    urls = read_from_input_txt()
    raw_rules = read_raw_rules()
    rules = AdblockRules(raw_rules)

    global no_of_Reponse
    global no_of_HSTS
    global total_blocked_url 
    # Crawling for each url and check if google analytics is enabled
    for url in urls:
        try:
            no_of_Reponse = 0
            no_of_HSTS = 0
            total_blocked_url = 0
            c.crawl_page(url, rules)
            write_to_file(page_url=url, ga_enabled=c.ga_enabled, anonymize_ip=c.anonymize_ip)
            update_hsts_list(page_url=url)
        except Exception as ex:
            print(ex)
            pass
    plot_hsts_bar(page_url=url)
    plot_blocked_bar(page_url=url)

if __name__ == '__main__':
    main()

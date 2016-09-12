# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import codecs
import logging
import mechanize
import os
import re
import sys
import time
from urllib2 import HTTPError
import urlparse


# The URL of the front page of the Mailman archive.
MAILMAN_ARCHIVE_URL = 'https://lists.w3.org/Archives/Public/public-restrictedmedia/'

# The directory to save all the message files in.
# Relative to the location of this script.
SAVE_DIRECTORY = 'messages'


logging.basicConfig(level=logging.INFO)

class Textifier(object):

    mailman_archive_url = None
    save_path = None

    def __init__(self, config):
        """
        Set up config variables, create the directory to save messages in.

        config should have:
            mailman_archive_url
            save_directory
        """

        # Ensure the URL ends in a slash:
        url = config['mailman_archive_url']
        if not url.endswith('/'):
            url += '/'
        self.mailman_archive_url = url

        self.save_path = os.path.join(
                                os.path.dirname(os.path.realpath(__file__)),
                                config['save_directory'])

        try:
            os.mkdir(self.save_path)
        except OSError, e:
            if os.path.exists(self.save_path):
                self.error("The '%s' directory already exists. Please move or rename it and try again." % config['save_directory'])
            else:
                self.error("Something went wrong when trying to create the '%s' directory: %s" % (config['save_directory'], str(e)))


    def textify(self):
        "Call this to run everything!"

        month_urls = self.scrapeIndex(self.mailman_archive_url)

        message_urls = []
        for url in month_urls:
            new_urls = self.scrapeMonth(url)
            message_urls = message_urls + new_urls
            time.sleep(0.5) # Play nice, wait half a second.

        for url in message_urls:
            self.scrapeMessage(url)
            time.sleep(0.5) # Play nice, wait half a second.

    def scrapeIndex(self, url):
        source = self.fetchPage(url)
        soup = BeautifulSoup(source, 'html.parser')

        month_urls = []

        for row in soup.table.find_all('tr'):
            try:
                path = row.find_all('td')[0].a.get('href')
                month_urls.append( urlparse.urljoin(url, path) )
            except IndexError:
                pass # First row only has <th>s.

        return month_urls

    def scrapeMonth(self, url):
        source = self.fetchPage(url)
        soup = BeautifulSoup(source, 'html.parser')

        message_urls = []

        # Messages are listed in this structure:
        #<div class="messages-list">
        #    <ul>
        #        <li><a></a>Name of day
        #            <ul>
        #                <li><a href="0001.html">Subject</a></li>
        #                <li><a href="0000.html">Subject</a></li>
        #            </ul>
        #        </li>
        #        ...
        #    </ul>
        #</div>
        for day in soup.find(class_='messages-list').find_all('li'):
            for message in day.find_all('li'):
                path = message.a.get('href')
                message_urls.append( urlparse.urljoin(url, path) )

        return message_urls

    def scrapeMessage(self, url):

        url_parts = urlparse.urlsplit(url).path.split('/')
        # Get '2016Mar' from 'http://.../2016Mar/0002.html':
        month = url_parts[-2:-1][0]
        # Get '0002.html' from 'http://.../2016Mar/0002.html':
        filename = url_parts[-1:][0]
        # Change '0002.html' to '0002.txt':
        save_filename = '%s.txt' % os.path.splitext(filename)[0]
        # End up with '2016Mar_0002.html':
        save_filename = '%s_%s' % (month, save_filename)

        source = self.fetchPage(url)
        soup = BeautifulSoup(source, 'html.parser')

        message = soup.find(class_='mail')

        headers = message.find(class_='headers')
        headers = headers.get_text()
        headers = headers.strip()
        headers = re.sub('\n+', '\n', headers)

        body = message.find(id='body')
        body = body.get_text()

        # Looks for a link like:
        # <map id="navbar">
        #   <ul class="links">
        #       <a href="0002.html">In reply to</a>
        # And gets the '0002.html', and adds a line like this to headers:
        # Reply-To: 2016Mar_0002.txt
        for a in soup.find(id='navbar').find(class_='links').find_all('a'):
            if a.get_text() == 'In reply to':
                # e.g. '0002.html':
                href = a.get('href')
                # e.g. '2016Mar_0002.txt':
                reply_to_filename = '%s_%s.txt' % (
                                            month, os.path.splitext(href)[0])
                headers = '%s\nReply-To: %s' % (headers, reply_to_filename)
                break

        txt = "%s\n%s" % (headers, body)

        file = codecs.open(
                        os.path.join(self.save_path, save_filename),
                        'w',
                        encoding='utf-8')
        file.write(txt)
        file.close()

    def fetchPage(self, url):
        "Used for fetching all the remote pages."

        self.message("Fetching " + url)
        fp = None
        try:
            fp = mechanize.urlopen(url)
            source = fp.read()
        except HTTPError as e:
            self.error("Failed to fetch %s, HTTP status %s" % \
                                                    (e.filename, str(e.code)),
                        fatal=False)
            return None
        finally:
            if fp:
                fp.close()

        return source

    def message(self, text):
        "Output debugging info."
        logging.info(text)

    def error(self, text, fatal=True):
        logging.warning(text)
        if fatal:
            exit()


if __name__ == '__main__':
    textifier = Textifier({
        'mailman_archive_url': MAILMAN_ARCHIVE_URL,
        'save_directory': SAVE_DIRECTORY,
    })
    textifier.textify()


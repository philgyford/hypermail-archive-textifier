#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import codecs
import logging
import os
import re
import requests
import sys
import time

try:
    # Python 2
    from urlparse import urljoin, urlsplit
except ImportError:
    # Python 3
    from urllib.parse import urljoin, urlsplit


# The URL of the front page of the Mailman archive.
MAILMAN_ARCHIVE_URL = 'https://lists.w3.org/Archives/Public/public-restrictedmedia/'

# The directory to save all the message files in.
# Relative to the location of this script.
SAVE_DIRECTORY = 'messages'


logging.basicConfig(level=logging.INFO)

class Textifier(object):

    mailman_archive_url = None
    save_path = None

    # Will map original message directory/filenames like '2013Aug/0002.html' to
    # Message-IDs.
    name_to_id = {}

    # For every message that needs an In-Reply-To added to it at the end of
    # the process, map from Message-ID to '2013Aug/0002.html'
    replies = {}

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
        except OSError as e:
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

        self.addReplies()

    def scrapeIndex(self, url):
        """
        Returns a list of URLs for month archives, in chronological order.
        """
        month_urls = ['https://lists.w3.org/Archives/Public/public-restrictedmedia/2013Jul/']

        #source = self.fetchPage(url)

        #if source is not None:
            #soup = BeautifulSoup(source, 'html.parser')


            #for row in soup.table.find_all('tr'):
                #try:
                    #path = row.find_all('td')[0].a.get('href')
                    #month_urls.append( urljoin(url, path) )
                #except IndexError:
                    #pass # First row only has <th>s.

        return list(reversed(month_urls))

    def scrapeMonth(self, url):
        """
        Returns a list of URLs of individual messages, in chronological order.
        """
        message_urls = []

        source = self.fetchPage(url)

        if source is not None:
            soup = BeautifulSoup(source, 'html.parser')


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
                    message_urls.append( urljoin(url, path) )

        return list(reversed(message_urls))

    def scrapeMessage(self, url):
        """
        Fetches and saves a single message.
        """

        # Get ['2016Mar', '0002.html'] from 'http://.../2016Mar/0002.html':
        url_parts = urlsplit(url).path.split('/')
        month = url_parts[-2:-1][0]
        filename = url_parts[-1:][0]
        # For putting the Message Id in self.name_to_id:
        message_name = '%s/%s' % (month, filename)

        source = self.fetchPage(url)
        if source is None:
            return # Couldn't fetch the page.

        soup = BeautifulSoup(source, 'html.parser')

        # The message, including headers:
        message = soup.find(class_='mail')

        headers = message.find(class_='headers')

        # Get the Message-ID for putting in self.name_to_id:
        message_id_text = headers.find(id='message-id').get_text()
        m = re.search('<(.*?)>', message_id_text)
        message_id = m.group(1)
        # Store for future reference:
        self.name_to_id[message_name] = message_id

        # Tidy the header text for saving:
        headers = headers.get_text()
        headers = headers.strip()
        headers = re.sub('\n+', '\n', headers)

        # Get the body of the message:
        body = message.find(id='body')
        body = body.get_text()


        # Work out in-reply-to headers:

        # Looks for a link like:
        # <map id="navbar">
        #   <ul class="links">
        #       <a href="0002.html">In reply to</a>
        # Uses that to find the Message-ID of the message this is in reply to.
        # And adds an In-Reply-To line to the headers.
        for a in soup.find(id='navbar').find(class_='links').find_all('a'):
            if a.get_text() == 'In reply to':
                reply_to_link = a.get('href')

                # Two things might happen here...
                #
                # Either the link is to a Message-ID, in which case we can
                # add the In-Reply-To header right now.
                #
                # Or the link is a filename ('0002.html') in which case,
                # we need to save the fact this Message-ID is in reply to
                # that filename.

                if reply_to_link.startswith('http'):
                    # Probably like 'https://www.w3.org/mid/CAEnTvdCE9nprxRAikQmyAp19XkNZG=z-vUErs8c4Ho_y6DD0GA@mail.gmail.com'

                    reply_to_id = urlsplit(reply_to_link).path.split('/')[-1:][0]
                    headers = 'In-Reply-To: <%s>\n%s' % (reply_to_id, headers)

                else:
                    # Link is probably like '0002.html'
                    # Make name like '2016Mar/0002.html':
                    reply_to_name = '%s/%s' % (month, reply_to_link)
                    # Store which filename we're replying to, for adding later.
                    self.replies[message_id] = reply_to_name

                break

        txt = "%s\n%s" % (headers, body)

        save_filename = '%s.txt' % message_id
        path = os.path.join(self.save_path, save_filename)
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(txt)
            f.close()

    def addReplies(self):
        """
        We will have populated self.replies and self.name_to_id.
        Use these to work out which messages need 'In-Reply-To' lines
        adding to them, and do that.

        Why is this done separately?
        Because if a message just says it's in reply to '0002.html' we can't
        get the ID of that message at the time. So we go through ALL of the
        messages, save them, and store the info mapping filename to ID.

        THEN once all messages have been saved, we have enough info to go
        back and map from these filenames to IDs, and add the header lines.
        """
        self.message("Adding In-Reply-To header lines to files")

        # Go through each message that's a reply.
        # Get its ID and the message_name of what it's replying to:
        for (message_id, message_name) in self.replies.items():

            # Get the Message-ID from the name (like '2016/Mar/0002.html'):
            reply_to_id = self.name_to_id[message_name]

            filename = '%s.txt' % message_id
            path = os.path.join(self.save_path, filename)

            with codecs.open(path, 'r+', encoding='utf-8') as f:
                txt = f.read()
                line = 'In-Reply-To: <%s>' % reply_to_id
                txt = '%s\n%s' % (line, txt)
                f.seek(0)
                f.write(txt)
                f.truncate()

    def fetchPage(self, url):
        """
        Used for fetching all the remote pages.
        Returns the contents of the page, or None if something goes wrong.
        """

        self.message("Fetching " + url)

        try:
            r = requests.get(url)
            r.raise_for_status() # Raises an exception on HTTP error.
            return r.text
        except requests.exceptions.RequestException as e:
            self.error("Failed to fetch: %s" % (str(e)), fatal=False)
            return None

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


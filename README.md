# Hypermail archive textifier

Scrapes a Hypermail archive web page and saves all of the messages into individual plaintext files.


## Usage

1. Install the required modules using [pip](https://pip.pypa.io/en/stable/):

        $ pip install -r requirements.txt

2. In `textify.py` set the URL of the archive you want to scrape.

3. Run the script:

        $ python textify.py

The script pauses for half a second between fetching each message, so as not to hammer the archive's servers, so it may take a while.


## Results

All being well you will end up with a `messages` directory in the same directory as the script. This will contain one text file per message. e.g.:

    messages/
    ├── 2012Aug_0000.txt
    ├── 2012Aug_0001.txt
    ├── 2012Aug_0002.txt
    ├── 2012Jul_0000.txt
    ├── 2012Jul_0001.txt

And so on.

Each text file will contain the message headers included on the web archive, followed by at least one blank line, followed by the message. e.g.:

	From: Bob Ferris <robert.ferris.notreally@gmail.com>
	Date: Fri, 12 Dec 2014 13:08:02 -0700
	Message-ID: <DWNMhERiP=002TZKWquSebUfKExx=N4KoibUrbeFCrkRd-W0KKww@mail.gmail.com>
	To: public-testlist@example.org

	Hello,

	Here's the start of an example email.

If the archive page indicated that the email was a reply to an earlier email, the header information will have an extra `Reply-To` line, containing the local directory name and filename of the replied-to message. e.g.:

	From: Bob Ferris <robert.ferris.notreally@gmail.com>
	Date: Fri, 12 Dec 2014 13:08:02 -0700
	Message-ID: <DWNMhERiP=002TZKWquSebUfKExx=N4KoibUrbeFCrkRd-W0KKww@mail.gmail.com>
	To: public-testlist@example.org
	Reply-To: 2014Dec/0023.txt

	Hello,

	Here's the start of an example email.


## Caveats

This has only been run on one archive ( https://lists.w3.org/Archives/Public/public-restrictedmedia/ ) and others, with different versions of Hypermail might not work. For example, their HTML might different, breaking the scraping of the pages that this script does.


# greg

A command-line podcast aggregator, written in python. It basically exposes some
of the functionality of the excellent
[feedparser](http://pypi.python.org/pypi/feedparser).

## Installation

Use [pip](https://pip.pypa.io/en/stable/):

`pip install --user greg`

If you run [Arch Linux](https://archlinux.org/), there is also an [AUR
package](https://aur.archlinux.org/packages/greg-git/).

## Configuration

To edit the configuration for greg, copy the system-wide [greg.conf](https://github.com/manolomartinez/greg/blob/master/greg/data/greg.conf) file to your local config folder:

```
mkdir -p ~/.config/greg && cp `greg retrieveglobalconf` ~/.config/greg/greg.conf
```

Then open and edit `~/.config/greg/greg.conf` in a text editor. The configuration file is self-explanatory.

## Usage

Let's start by adding a feed (RSS or Atom versions will do):

    greg add PhilosophyBites http://philosophybites.com/atom.xml

The `add` command expects a name and a url of an RSS or Atom feed. You will use this name to refer to the feed whenever you interact with it.

If you were to run `greg sync` now, it would download the latest episode of the podcast to the default directory (which is `~/Podcasts`; you can change how many episodes are dowloaded in the first sync, and the download directory, in the config file; see below). But maybe we just want to check out what this podcast is all about, so we download a list of available entries:

    greg check -f PhilosophyBites

(the `-f` flag means that "PhilosophyBites" is the name of a feed. `greg check` also accepts urls directly, using the `-u` flag.)

This will give you the following kind of info:


    0: Tom Sorell on Surveillance (2013-01-25T13:43:46+00:00)
    1: John Campbell on Schizophrenia (2013-01-08T12:41:27+00:00)
    2: Kendall Walton on Photography (2012-12-23T12:33:09+00:00)
    3: Twitter Competition: Who's Your Favourite Philosopher? (2012-12-11T07:24:51+00:00)
    4: Alan Ryan on Freedom and Its History (2012-12-08T11:16:45+00:00)
    5: Nigel Warburton at Blackwell's Bookshop, Oxford 7pm Wed. Dec. 5th (2012-12-01T11:19:09+00:00)
    6: Who's Your Favourite Philosopher? (2012-11-30T18:33:56+00:00)
    7: Peter Adamson on Avicenna's Flying Man Thought Experiment (2012-11-26T15:57:18+00:00)
    8: Links to Past Episodes (2012-12-01T11:53:03+00:00)
    9: Tim Bayne on the Unity of  Consciousness (2012-11-11T22:20:17+00:00)
    10: Galen Strawson on the Sense of Self (2012-05-05T12:56:05+01:00)
    11: Liane Young on Mind and Morality (2012-10-27T12:39:22+01:00)
    12: Gary L. Francione on Animal Abolitionism (2012-10-13T13:48:32+01:00)
    13: Richard Sorabji on Mahatma Gandhi as Philosopher (2012-09-28T13:18:08+01:00)
    14: Tim Crane on Non-Existence (2012-09-15T18:50:32+01:00)
    15: Michael Tye on Pain (2012-08-31T20:51:01+01:00)
    16: Daniel Dennett on Free Will Worth Wanting (2012-08-18T08:58:24+01:00)
    17: Pat Churchland on What Neuroscience Can Teach Us About Morality (2012-08-03T22:52:12+01:00)
    18: Rae Langton on Hate Speech (2012-07-28T20:14:27+01:00)
    19: Molly Crockett on Brain Chemistry and Moral-Decision Making (originally on Bioethics Bites) (2012-07-22T21:14:35+01:00)

Interesting stuff. We'll download a couple of episodes, just to make sure that
it's really worth it:

    greg download 1, 5-7

and Greg says

    Downloading John Campbell on Schizophrenia -- John_Campbell_on_Schizophrenia.mp3
    Done
    Downloading John Campbell on Schizophrenia -- John_Campbell_on_Berkeleys_Puzzle_1.mp3
    Done
    Downloading Who's Your Favourite Philosopher? -- Whos_Your_Favourite_Philosopher_.mp3
    Done
    Downloading Peter Adamson on Avicenna's Flying Man Thought Experiment -- Peter_Adamson_on_Avicennas_Flying_Man.mp3
    Done
    Downloading Peter Adamson on Avicenna's Flying Man Thought Experiment -- AdamsonMixSes.MP3
    Done
    Downloading Peter Adamson on Avicenna's Flying Man Thought Experiment -- Peter_Adamson_on_Plotinus_on_Evil.mp3
    Done

As you can see, `greg download` accepts a range of episodes of the kind `a, b,
c-f, h, ...`. The numbers make reference to the numbers at the beginning of
each entry provided by `greg check`. `check` creates a persistent file
(`feeddump` in the data directory, `~/.local/share/greg/data by` default, but
you can change that in the config file, or passing a different path with the
`--datadirectory` flag), so `download` will keep on working, and referring to
the last `check` ever done.

All of these podcasts will be downloaded to the default download directory for
the feed (if you used the `-f` flag) or the general default download directory
(again, `~/Podcasts` if you don't tell Greg otherwise. We'll learn how to
change that soon), inside a subdirectory named after the podcast (we can change
that default too.) After listening to them we decide that this podcast is well
worth our time, and keep it, or we decide that it's not, and

    greg remove PhilosophyBites

If we keep it, we might want to start `sync`ing from, say, the 30th of April,
2013, on. So we edit the feed information

    greg edit PhilosophyBites -d 2013-4-30

We may also use the `now` keyword to instruct greg to start syncing from now
on:

    greg edit PhilosophyBites -d now

`-d` or `--downloadfrom` change the date after which Greg should start
downloading episodes when it syncs. Currently, the only two things one can
`edit` in a feed are the download-from date and `--url` -- but many more things
can be changed by editing the config file. `greg edit -h` will give help you
with the `edit` options and syntax -- likewise for the rest of Greg
subcommands.

All right. Let's add a second feed:

    greg add History http://podcast.ulcc.ac.uk/accounts/kings/Philosophy_podcasts.xml

If you want to keep track of the feeds you have added, you can ask Greg:

    greg info

which returns

    PhilosophyBites
    ---------------
        url: http://philosophybites.com/atom.xml
        Next sync will download from: 30 Apr 2013 00:00:00.

    History
    -------
        url: http://podcast.ulcc.ac.uk/accounts/kings/Philosophy_podcasts.xml

Let us add another feed:

    greg add MusicaAntigua http://www.rtve.es/api/programas/23353/audios.rss

This is a great program on ancient music at the Spanish public radio. The thing
is, these guys do not tag their episodes, which is bad for most portable media
players. Greg uses [EyeD3](https://github.com/nicfit/eyeD3) (as an optional
dependency) to tag podcasts, if one so wishes. By default, it uses the podcast
name for the *artist* tag, and the entry title for the *title* tag. To enable
tagging for MusicaAntigua, copy the system-wide config file locally. (see
[Configuration](#configuration) above)

Then, add a section for MusicaAntigua:

    [MusicaAntigua]

    Tag = yes

In fact, you can fill out any tag however you see fit. For example,

    tag_genre = Ancient Music
    tag_comment = {date}

will fill the *genre* tag with the string "Ancient Music", and the *comment*
tag with the download date.

Let's add a video podcast

    greg add TEDTalks http://feeds.feedburner.com/TEDTalks_video

By default, Greg only donwloads audio files (in fact, files that have "audio"
as part of their type). In order to download the right file in TEDTalks, then,
you need to change that in the config file. Again, add a section:

    [TEDTalks]

    mime = video

You could also have a couple of types there, as in `mime = audio, video`; or
any other type, `mime = torrent`, or whatever.

Another useful thing that you can change in the config file is the download
handler; Greg by default uses [requests](https://github.com/psf/requests), but
you can use whatever you want.

I, for example, have

    downloadhandler = wget {link} -P {directory}

in my local `greg.conf`. You can do all sorts of nice things with this. For
example, when `check`ing a podcast, you don't need to download it, but maybe
just stream it, like this:

    greg download 0 --downloadhandler "mplayer {link}"

If you want to ensure that the downloaded files are in chronological order, you
can use placeholders to add the date at the beginning, like this:

    downloadhandler = wget {link} -O {directory}/{date}_{filename}

One last thing: if you subscribe to a very active feed, and you are only
interested in some of the entries, you can filter the feed. For example, if you
only want to watch TED talks about Google, say, you can add the following line
to the `[TEDTalks]` section:

    filter = "Google" in "{title}"

(You need the quotes around {title} if the string you are filtering by has
spaces, for example; they are strictly unnecessary here.)

For information about the {placeholders}, take a look at
[greg.conf](https://github.com/manolomartinez/greg/blob/master/greg/data/greg.conf).
In `greg.conf` you can also change the download directory, and some other
things. It should be self-explanatory.

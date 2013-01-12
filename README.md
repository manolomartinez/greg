greg
====

A command-line podcast aggregator. It basically exposes some of the functionality of the excellent [feedparser](http://pypi.python.org/pypi/feedparser).

# Usage

Let's start by adding a feed (RSS or Atom versions will do):

    greg add PhilosophyBites http://philosophybites.com/atom.xml

The `add` command expects a name and a url of an RSS or Atom feed. You will use this name to refer to the feed whenever you interact with it.

If you were to run `greg sync` now, it would download every available episode of the podcast to the default directory (which is `~/Podcasts`). But maybe we just want to check out what this podcast is all about, so we download a list of available entries:

    greg check PhilosophyBites
   
This will give you the following kind of info:


    0: Twitter Competition: Who's Your Favourite Philosopher? (2012-12-11T07:24:51+00:00)
    1: Alan Ryan on Freedom and Its History (2012-12-08T11:16:45+00:00)
    2: Nigel Warburton at Blackwell's Bookshop, Oxford 7pm Wed. Dec. 5th (2012-12-01T11:19:09+00:00)
    3: Who's Your Favourite Philosopher? (2012-11-30T18:33:56+00:00)
    4: Peter Adamson on Avicenna's Flying Man Thought Experiment (2012-11-26T12:54:02+00:00)
    5: Links to Past Episodes (2012-12-01T11:53:03+00:00)
    6: Tim Bayne on the Unity of  Consciousness (2012-11-11T22:20:17+00:00)
    7: Galen Strawson on the Sense of Self (2012-05-05T12:56:05+01:00)
    8: Liane Young on Mind and Morality (2012-10-27T12:39:22+01:00)
    9: Gary L. Francione on Animal Abolitionism (2012-10-13T13:48:32+01:00)
    10: Richard Sorabji on Mahatma Gandhi as Philosopher (2012-09-28T13:18:08+01:00)
    11: Tim Crane on Non-Existence (2012-09-15T18:50:32+01:00)
    12: Michael Tye on Pain (2012-08-31T20:51:01+01:00)
    13: Daniel Dennett on Free Will Worth Wanting (2012-08-18T08:58:24+01:00)
    14: Pat Churchland on What Neuroscience Can Teach Us About Morality (2012-08-03T22:52:12+01:00)
    15: Rae Langton on Hate Speech (2012-07-28T20:14:27+01:00)
    16: Molly Crockett on Brain Chemistry and Moral-Decision Making (originally on Bioethics Bites) (2012-07-22T21:14:35+01:00)
    17: Huw Price on Backward Causation (2012-07-15T19:06:15+01:00)
    18: Hanna Pickard on Responsibility and Personality Disorder (originally on Bioethics Bites) (2012-07-07T19:17:26+01:00)
    19: Jonathan Dancy on Moral Particularism (2012-06-29T10:37:58+01:00)

Interesting stuff. We'll download a couple of episodes, just to make sure that it's really worth it:

    greg download 1, 5-7

and Greg says

    Downloading Alan Ryan on Freedom and Its History
    Done
    Downloading Links to Past Episodes
    Downloading Tim Bayne on the Unity of  Consciousness
    Done
    Downloading Galen Strawson on the Sense of Self

As you can see, `greg download` accepts a range of episodes of the kind `a, b, c-f, h, ...`. The numbers make reference to the numbers at the beginning of each entry provided by `greg check`. `check` creates a persistent file (`~/.local/share/greg/feeddump`), so `download` will keep on working, and referring to the last `check` ever done.

All of these podcasts will be downloaded to the download directory (again, `~/Podcasts` by default. We'll learn how to change that soon.) After listening to them we decide that this podcast is well worth our time, and keep it, or we decide that it's not, and

    greg remove PhilosophyBites

If we keep it, we might want to start sync'ing from, say, the 1st of November, 2012, on. So we edit the feed information

    greg edit PhilosophyBites -d 01/11/12

`-d` or `--downloadfrom` change the date after which Greg should start downloading episodes when it syncs. Currently, the only two things one can `edit` in a feed are the download-from date and `--url`. `greg edit -h` will give help you with the `edit` options and syntax -- likewise for the rest of Greg subcommands.

All right. Let's add a second feed:

    greg add History http://feeds.feedburner.com/historyofphilosophy?format=xml

If you want to keep track of the feeds you have added, you can ask Greg:

    greg info

which returns

    PhilosophyBites
    ---------------
        url: http://philosophybites.com/atom.xml
        Next sync will download from: 01 Nov 2012 00:00:00.

    History
    -------
        url: http://feeds.feedburner.com/historyofphilosophy?format=xml

Let us add a final feed:

    greg add MusicaAntigua http://www.rtve.es/api/programas/23353/audios.rss

This is a great program on ancient music at the Spanish public radio. The thing is, these guys do not tag their episodes, which is bad for most portable media players. Greg uses [stagger](http://pypi.python.org/pypi/stagger/0.4.2) (as an optional dependency) to tag podcasts, if one so wishes. It uses the podcast name for the *artist* tag, and the entry title for the *title* tag. To enable tagging for MusicaAntigua, copy the system-wide config file locally:

    cp /etc/greg.conf ~/.config/greg/greg.conf

and add a section for MusicaAntigua:

    [MusicaAntigua]

    Tag = yes

In `greg.conf` you can also change the download directory, and some other things. It should be self-explanatory.

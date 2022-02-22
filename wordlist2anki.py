# inspired by https://github.com/DanonX2/A-Vocabulary.com-Vocab-List-TO-Anki-Deck-Converter

import bs4
import requests
import json
import sys
import os.path
import genanki
import sqlite3

__doc__ = """
usage: wordlist2anki.py wordlist

creates output.apkg for import into anki
"""


class Word:
    def __init__(self):
        self.word = ""
        self.pos = ""
        self.definition = ""
        self.description = ""
        self.wordfamily = []
        self.ipa = ""


def worddef_web(word: str) -> Word:
    """
    obtain word pos, definition, description and word family from vocabulary.com and ipa from dictionary.com
    """

    url = f"https://www.vocabulary.com/dictionary/{word}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")

    _ = [x.strip() for x in soup.find(
        'div', class_='definition').text.split('\r\n') if x.strip() != '']
    pos = _[0]
    definition = _[1]

    _ = soup.find('p', class_='short')
    description = ('' if _ is None else _.text)

    family = soup.find('vcom:wordfamily')['data']
    fp = json.loads(family)
    _ = sorted([(x['word'], x.get('parent', ''), x['type'], x['ffreq']) for x in fp if x.get(
        'parent', word) == word and x.get('hw', False) == True], key=lambda x: x[3], reverse=True)
    wordfamily = [x[0] for x in _]

    # ipa
    url = f"https://www.dictionary.com/browse/{word}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    _ = soup.find('span', class_='pron-ipa-content')
    ipa = _.text if _ is not None else ''

    w = Word()
    w.word = word
    w.pos = pos
    w.definition = definition
    w.description = description
    w.wordfamily = wordfamily
    w.ipa = ipa
    return w


def worddef_db(conn: sqlite3.Connection, word: str) -> Word:
    c = conn.cursor()
    c.execute("SELECT * FROM words WHERE word = ?", (word,))
    _ = c.fetchone()
    if _ is None:
        return None
    else:
        w = Word()
        w.word = _[0]
        w.pos = _[1]
        w.definition = _[2]
        w.description = _[3]
        w.wordfamily = json.loads(_[4])
        w.ipa = _[5]
        return w


def save_worddef(word: Word):
    conn = sqlite3.connect('vocab.db')
    c = conn.cursor()
    wordfamily = json.dumps(word.wordfamily)
    c.execute("INSERT INTO words VALUES (?, ?, ?, ?, ?, ?)",
              (word.word, word.pos, word.definition, word.description, wordfamily, word.ipa))
    conn.commit()
    conn.close()


def build_db():
    conn = sqlite3.connect('vocab.db')
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS words (word TEXT, pos TEXT, definition TEXT, description TEXT, wordfamily TEXT, ipa TEXT)')
    conn.commit()
    conn.close()


def times33(s):
    h = 0
    for c in s:
        h = (h * 33 + ord(c)) & 0xffffffff
    return h


if __name__ == '__main__':

    if not os.path.exists('vocab.db'):
        build_db()
    conn = sqlite3.connect('vocab.db')

    wordlist = []
    wordlistfile = sys.argv[1]
    with open(wordlistfile) as fh:
        for line in fh:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('#'):
                continue
            wordlist.append(line)

    items = []

    for word in wordlist:
        w = worddef_db(conn, word)
        if w is None:
            w = worddef_web(word)
            save_worddef(w)
            print(word, w.pos, w.definition, w.description,
                  w.wordfamily, w.ipa, sep='\n')

        items.append((f"{word}",
                      w.definition,
                      w.description.replace(word, '____').replace(
                          word.capitalize(), '____'),
                      ' - '.join(w.wordfamily),
                      w.ipa))

    model_name = 'Vocabulary.com 3'
    my_model = genanki.Model(
        times33(model_name),
        model_name,
        fields=[
            {'name': 'word'},
            {'name': 'definition'},
            {'name': 'description'},
            {'name': 'wordfamily'},
            {'name': 'ipa'}
        ],
        templates=[
            {
                'name': 'Forward Card',
                'qfmt': '{{word}} {{ipa}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{definition}}<br><br>{{description}}<br><br>{{wordfamily}}'
            },
            {
                'name': 'Reverse Card',
                'qfmt': '{{definition}}<br><br>{{description}}',
                'afmt': '{{FrontSide}}<hr>{{word}} {{ipa}}<br><br>{{wordfamily}}'
            }
        ])

    wordlist_base = os.path.basename(wordlistfile)
    # remove extension
    deck_name = wordlist_base[:wordlist_base.rfind('.')]

    my_deck = genanki.Deck(times33(deck_name), deck_name)

    for i in items:
        my_deck.add_note(genanki.Note(
            model=my_model,
            fields=i))

    genanki.Package(my_deck).write_to_file(f'{deck_name}.apkg')

    conn.close()

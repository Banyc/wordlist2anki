#!/Users/florian/anaconda3/bin/python

# inspired by https://github.com/DanonX2/A-Vocabulary.com-Vocab-List-TO-Anki-Deck-Converter

import bs4
import requests
import json
import sys
import os.path
import genanki

__doc__ = """
usage: wordlist2anki.py wordlist

creates output.apkg for import into anki
"""



"""
obtain word pos, definition, description and word family from vocabulary.com and ipa from dictionary.com
"""
def worddef(word):

    url = f"https://www.vocabulary.com/dictionary/{word}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")

    _ = [x.strip() for x in soup.find('div', class_ = 'definition').text.split('\r\n') if x.strip() != '']
    pos = _[0]
    definition = _[1]

    _ = soup.find('p', class_ = 'short')
    description = ('' if _ is None else _.text)

    family = soup.find('vcom:wordfamily')['data']
    fp = json.loads(family)
    _ = sorted([(x['word'], x.get('parent', ''),x['type'], x['ffreq']) for x in fp if x.get('parent',word) == word and x.get('hw', False) == True], key = lambda x: x[3], reverse = True)
    wordfamily = [x[0] for x in _]

    # ipa
    url = f"https://www.dictionary.com/browse/{word}"
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    _ = soup.find('span', class_ = 'pron-ipa-content')
    ipa = _.text if _ is not None else ''

    return (word, pos, definition, description, wordfamily, ipa)



if __name__ == '__main__':

    wordlist =[]
    wordlistfile = sys.argv[1]
    with open(wordlistfile) as fh:
        for line in fh:
            wordlist.append(line.strip())

    items = []
            
    for word in wordlist:
        if word == '':
            continue
        if word.startswith('#'):
            continue
        word, pos, definition, description, wordfamily, ipa = worddef(word)
        
        
        print(word, pos, definition, description, wordfamily, ipa, sep='\n')

        items.append((f"{word} ({pos})",
                      definition,
                      description.replace(word, '____').replace(word.capitalize(), '____'),
                      ' - '.join(wordfamily),
                      ipa))

    
    model_name = 'Vocabulary.com 3'
    my_model = genanki.Model(
        hash(model_name),
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

    my_deck = genanki.Deck(hash(wordlistfile), wordlistfile)

    for i in items:
        my_deck.add_note(genanki.Note(
            model=my_model,
            fields=i))

    genanki.Package(my_deck).write_to_file(f'{wordlistfile}.apkg')
            

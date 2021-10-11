import re
import sys
import os

whitespace = re.compile('^\s*$')

def get_pairs(lines):
    return [line.replace('\n', '').split(';') for line in lines]

def drawer():
    first = True
    def draw_box(length, text, comment):
        nonlocal first
        if first:
            first = False
            print('-'*length)
        print('|' + text + ' '*(length - len(text) - 2) + '|', end='')
        print(comment)
        print('-'*length)
    return draw_box

draws = drawer()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python {} <file>'.format(__file__))
    else:
        file = sys.argv[1]
        if not os.path.isfile(file):
            raise FileNotFoundError

        with open(file, 'r') as f:
            lines = [line for line in f if not whitespace.match(line)]

        pairs = get_pairs(lines)
        longest = max(*pairs, key=lambda x: len(x[0]))
        ascii_length = len(longest[0]) + 2

        for text, comment in pairs:
            draws(ascii_length, text, comment)

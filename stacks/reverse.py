import sys
import os

def reverse_lines(fname):
    with open(fname, 'r') as file:
        lines = [line for line in file]

    reverse = [line for line in reversed(lines)]
    with open(fname, 'w') as file:
        file.write(''.join(reverse))

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('Usage: python {} <file>'.format(__file__))
    else:
        file = sys.argv[1]
        if not os.path.isfile(file):
            raise FileNotFoundError

        reverse_lines(file)

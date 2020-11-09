import re
import string
from itertools import chain
from typing import AnyStr, Callable, Dict, List, Pattern, Sequence, Tuple, Union
from sre_constants import _NamedIntConstant

# The * and + characters in a regular expression
# match up to any number of repeats in theory,
# (and actually 65535 repeats in python) but you
# probably don't want that many repeats in your
# generated strings. This sets an upper-bound on
# repeats generated from + and * characters.
STAR_PLUS_LIMIT = 100

Operation = Tuple[_NamedIntConstant, Union['Operation',  # type: ignore
                                           Sequence['Operation'], Tuple[int, int, Sequence['Operation']]], Tuple[int, int, int, Sequence['Operation']]]


class Xeger(object):

    '''Inspired by the Java library Xeger: http://code.google.com/p/xeger/
    This class adds functionality to Rstr allowing users to generate a
    semi-random string from a regular expression.'''

    def __init__(self):
        super(Xeger, self).__init__()
        self._cache: Dict[int, str] = dict()
        self._categories: Dict[str, Callable[[], str]] = {
            'category_digit': lambda: self._alphabets['digits'],
            'category_not_digit': lambda: self._alphabets['nondigits'],
            'category_space': lambda: self._alphabets['whitespace'],
            'category_not_space': lambda: self._alphabets['nonwhitespace'],
            'category_word': lambda: self._alphabets['word'],
            'category_not_word': lambda: self._alphabets['nonword'],
        }
# Callable[[Union[int, Tuple[int, int], Operation]], Union[str, Sequence[str], Sequence[bool]]]
        self._cases: Dict[str, Callable[[Union[int, Sequence[Operation], Sequence[int], str, Sequence[Sequence[Operation]], Operation]], Union[str, Sequence[bool], Sequence[str]]]] = {
            'literal': lambda x: chr(x),
            'not_literal': lambda x: self._random.choice(string.printable.replace(chr(x), '')),
            'at': lambda x: '',
            'in': lambda x: self._handle_in(x),
            'any': lambda x: self.printable(1, exclude='\n'),
            'range': lambda x: [chr(i) for i in range(x[0], x[1] + 1)],
            'category': lambda x: self._categories[x](),
            'branch': lambda x: ''.join(self._handle_state(i) for i in self._random.choice(x[1])),
            'subpattern': lambda x: self._handle_group(x),
            'assert': lambda x: ''.join(self._handle_state(i) for i in x[1]),
            'assert_not': lambda x: '',
            'groupref': lambda x: self._cache[x],
            'min_repeat': lambda x: self._handle_repeat(*x),
            'max_repeat': lambda x: self._handle_repeat(*x),
            'negate': lambda x: [False],
        }

    def xeger(self, string_or_regex: Union[Pattern[AnyStr], str]):
        try:
            pattern = string_or_regex.pattern
        except AttributeError:
            pattern = string_or_regex

        parsed = re.sre_parse.parse(pattern)
        result = self._build_string(parsed)
        self._cache.clear()
        return result

    def _build_string(self, parsed: Sequence[Operation]) -> str:
        newstr = [self._handle_state(item) for item in parsed]

        return ''.join(newstr)

    def _handle_state(self, state: Operation) -> Union[str, Sequence[str], Sequence[bool]]:
        opcode, value = state
        opcode = str(opcode).lower()
        if opcode == 'category':
            value = value.name.lower()
        return self._cases[opcode](value)

    def _handle_group(self, value: Sequence[Sequence[Operation]]) -> str:
        result = ''.join(self._handle_state(i) for i in value[-1])
        if value[0]:
            self._cache[value[0]] = result
        return result

    def _handle_in(self, value: Sequence[Operation]) -> str:
        candidates: List[Union[str, bool]] = list(
            chain(*(self._handle_state(i) for i in value)))
        if candidates[0] is False:
            candidates: List[str] = candidates[1:]
            candidates = list(set(
                string.printable).difference(candidates))
            return self._random.choice(candidates)
        else:
            return self._random.choice(candidates)

    def _handle_repeat(self, start_range: int, end_range: int, value: Sequence[Operation]) -> str:
        result: List[str] = []
        end_range = min(end_range, STAR_PLUS_LIMIT)
        times: int = self._random.randint(start_range, end_range)
        for _ in range(times):
            result.append(''.join(self._handle_state(i) for i in value))
        return ''.join(result)

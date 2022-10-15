import functools
import re

get_indent_size_at = lambda s, start: len(re.compile(r' *').match(s, start).group())
remove_suffix = lambda text, suffix: text[:-len(suffix)] if text.endswith(suffix) else text
zip_dicts = lambda d1, d2: {k: (v1, v2) for k, v1 in d1.items() if (v2 := d2.get(k)) is not None}
# returns a list mapping from zero-based line number to zero-based offset in the string
index_lines = lambda text: [match.start() for match in re.finditer(r'^', text, flags=re.MULTILINE)]

# applied one after the other, in order
TYPE_CLEANUPS = [
	# we add ' | None' later if necessary
	lambda s: remove_suffix(s, ', optional'),
	lambda s: remove_suffix(s, ' | None'),
	lambda s: re.sub(r'^Optional\[(.+)\]$', r'\1', s),
	lambda s: re.sub(r'^\(([^)]+)\)$', r'\1', s), # removes surrounding parens
	lambda s: re.sub(r"^'([^)]+)'$", r'\1', s), # removes surrounding quotes
	lambda s: re.sub(r':?\bclass ?:`~?\.?([^`]+)`', r'\1', s), # replace :class: syntax with the name inside
	# normalize some stuff
	lambda s: s.replace('numpy', 'np').replace('np.array', 'np.ndarray'),
	lambda s: re.sub(r'\btyping\.', '', s), # prefer unqualified names from `typing`
	lambda s: re.sub(r'\b(List|Dict|Tuple|Type)\b', lambda m: m.group().lower(), s),
	lambda s: re.sub(r'\bstring\b', 'str', s),
	lambda s: re.sub(r'\bBoolean\b', 'bool', s),
	# wrong usages of Callable
	lambda s: s.replace('Callable[[...]', 'Callable[...'),
	lambda s: re.sub(r'Callable\[(\w+),', lambda m: f'Callable[[{m.group(1)}],', s),
	# wrong usages of List
	lambda s: re.sub(r'\b(list\[\w+), \.\.\.\]', r'\1]', s),
	# replace all ways of specifying unions with pipe operators
	lambda s: s.replace(' or ', ', '),
	lambda s: re.sub(r' ?\| ?', ' | ', s),
	lambda s: re.sub(r'^([\w., ]+)$', lambda m: ' | '.join(map(str.strip, m.group(1).split(','))), s),
	lambda s: re.sub(r'\bUnion\[([\w., ]+)\]', lambda m: ' | '.join(map(str.strip, m.group(1).split(','))), s),
	lambda s: s.replace('float | int', 'float').replace('int | float', 'float'), # according to manim's "add typings" guidelines
]

cleanup_type = lambda s: functools.reduce(lambda t, c: c(t), TYPE_CLEANUPS, s)

from __future__ import annotations

import ast
import dataclasses
import functools
import re
import typing

from utils import get_indent_size_at

if typing.TYPE_CHECKING:
	from file import File


@dataclasses.dataclass
class Func:
	file: File
	func: ast.FunctionDef
	# node that may hold the docstring for the func
	node_with_docstring: typing.Optional[ast.AST] = None

	def __post_init__(self) -> None:
		# default is func itself
		if self.node_with_docstring is None:
			self.node_with_docstring = self.func

	def __str__(self) -> str:
		return f'{self.__class__.__name__}({self.func.name} @ {self.file.name}:{self.func.lineno})'

	@functools.cached_property
	def has_docstring(self) -> bool:
		return ast.get_docstring(self.node_with_docstring, clean=False) is not None

	@functools.cached_property
	def docstring(self) -> typing.Optional[str]:
		if not self.has_docstring:
			return None
		# read directly from the file and not from the ast, because the ast parses the string node and resolves escapes,
		# which is a problem when we try to modify the file based on it
		return self.file.contents[self.docstring_position]

	@functools.cached_property
	def docstring_position(self) -> typing.Optional[slice]:
		if not self.has_docstring:
			return None
		docstring_node = self.node_with_docstring.body[0]
		pos = self.file.line_offsets[docstring_node.lineno - 1] + docstring_node.col_offset
		endpos = self.file.line_offsets[docstring_node.end_lineno - 1] + docstring_node.end_col_offset
		if self.file.contents[pos] == 'r': # raw string
			pos += 1
		assert self.file.contents[pos:pos+3] == '"""', str(self)
		assert self.file.contents[endpos-3:endpos] == '"""', str(self)
		return slice(pos+3, endpos-3)

	def find_docstring_section(self, title: str) -> typing.Optional[tuple[slice, slice, slice]]:
		if not self.has_docstring:
			return None
		section_header_regex = re.compile(rf'^ *{title}\n *-+\n+', flags=re.MULTILINE)
		section_header = section_header_regex.search(self.file.contents, self.docstring_position.start, self.docstring_position.stop)
		if section_header is None:
			# section not found
			return None
		section_header_position = slice(*section_header.span())
		indent_size = get_indent_size_at(self.file.contents, section_header_position.start)
		section_end_regex = re.compile(rf'(?<=\n)(\n*)( {{,{indent_size}}}(\w[ \w]*\n *-+\n|\.\. [\w-]+::|To create a tuple)| *$)|, an integer')
		section_end = section_end_regex.search(self.file.contents, section_header_position.stop, self.docstring_position.stop).start()
		section_position = slice(section_header_position.stop, section_end)
		section_footer_position = slice(*re.compile(r'\n*').match(self.file.contents, section_end).span())
		return (section_header_position, section_position, section_footer_position)

	@functools.cached_property
	def doc_args(self) -> dict[str, DocArg]:
		if not self.has_docstring:
			return {}
		parameters_section = self.find_docstring_section('Parameters')
		if parameters_section is None:
			return {}
		_, section_position, _ = parameters_section

		param_indent = get_indent_size_at(self.file.contents, section_position.start)
		param_regex = re.compile(rf'^ {{{param_indent}}}\**(\w+) ?:?(?: (.+))?$', flags=re.MULTILINE)
		params = list(param_regex.finditer(self.file.contents, section_position.start, section_position.stop))

		doc_args = {}
		param_section_end = re.compile('').match(self.file.contents, section_position.stop, section_position.stop)
		for match, next_match in zip(params, params[1:] + [param_section_end]):
			name = match.group(1)
			assert name not in doc_args, f'[{self}] duplicate arg {name} in docstring'
			doc_args[name] = DocArg(
				func=self,
				type=match.group(2),
				annotation_position=slice(match.end(1), match.end()),
				name_position=slice(match.start(1), match.end(1)),
				position=slice(match.start(), next_match.start()),
			)
		return doc_args

	def rename_doc_arg(self, name, new_name):
		assert new_name not in self.doc_args
		self.doc_args[name].rename_in_docstring(new_name)
		self.doc_args[new_name] = self.doc_args.pop(name)

	def delete_doc_arg(self, name) -> None:
		self.doc_args[name].delete_from_docstring()
		self.doc_args.pop(name)

		# if there are no more doc args, delete the section header as well
		if not self.doc_args:
			section_header_position, _, section_footer_position = self.find_docstring_section('Parameters')
			self.file.register_modification(section_header_position, '')
			self.file.register_modification(section_footer_position, '')

	@functools.cached_property
	def func_args(self) -> dict[str, FuncArg]:
		args = self.func.args
		args = [
			*zip(args.posonlyargs + args.args, [None]*(len(args.posonlyargs + args.args) - len(args.defaults)) + args.defaults),
			*([(args.vararg, None)] if args.vararg else []),
			*zip(args.kwonlyargs, args.kw_defaults),
			*([(args.kwarg, None)] if args.kwarg else []),
		]

		func_args = {}
		for arg, default in args:
			if arg.annotation:
				func_args[arg.arg] = FuncArg(
					func=self,
					type=ast.unparse(arg.annotation),
					annotation_position=slice(-1, -1), # NOTE: this is complicated to calculate but we never need it
					default=default,
				)
			else:
				assert arg.lineno == arg.end_lineno and arg.col_offset + len(arg.arg) == arg.end_col_offset
				pos = self.file.line_offsets[arg.end_lineno - 1] + arg.end_col_offset
				func_args[arg.arg] = FuncArg(
					func=self,
					type=None,
					annotation_position=slice(pos, pos),
					default=default,
				)
		return func_args


@dataclasses.dataclass
class DocArg:
	func: Func
	type: typing.Optional[str]
	annotation_position: slice
	name_position: slice
	position: slice

	def delete_annotation(self) -> None:
		self.func.file.register_modification(self.annotation_position, '')

	def rename_in_docstring(self, new_name) -> None:
		self.func.file.register_modification(self.name_position, new_name)

	def delete_from_docstring(self) -> None:
		self.func.file.register_modification(self.position, '')


@dataclasses.dataclass
class FuncArg:
	func: Func
	type: typing.Optional[str]
	annotation_position: slice
	default: typing.Optional[ast.AST]

	def set_annotation(self, type: str) -> None:
		self.func.file.register_modification(self.annotation_position, f': {type}')

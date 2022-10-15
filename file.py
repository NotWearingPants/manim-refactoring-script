from __future__ import annotations

import ast
import bisect
import dataclasses
import functools
import pathlib
import typing

from func import Func
from special_cases import CIRCULAR_IMPORTS
from utils import index_lines


@dataclasses.dataclass
class File:
	path: pathlib.Path
	relative_path: pathlib.Path
	modifications: list[tuple[slice, str]] = dataclasses.field(init=False, default_factory=list)
	to_import: set[str] = dataclasses.field(init=False, default_factory=set)

	def __hash__(self) -> int:
		return hash(self.name)

	@functools.cached_property
	def name(self) -> str:
		return self.relative_path.as_posix()

	@functools.cached_property
	def module_name(self) -> typing.Optional[str]:
		if self.relative_path.parts[0] != 'manim':
			return None
		return '.'.join(self.relative_path.with_suffix('').parts)

	@functools.cached_property
	def contents(self) -> str:
		contents = self.path.read_text('utf8')
		# camera.py:386 function `reset` has an extra pair of quotes at end of docstring, delete it here before parsing
		contents = contents.replace('""" ""', '"""')
		return contents

	@functools.cached_property
	def line_offsets(self) -> list[int]:
		return index_lines(self.contents)

	# represents the change `contents[start:stop] = replacement`
	# the modification is postponed to avoid affecting offsets which were already calculated
	def register_modification(self, position: slice, replacement: str) -> None:
		assert position.start <= position.stop and position.step is None
		modification = (position, replacement)
		index = bisect.bisect(self.modifications, modification)
		assert index == len(self.modifications) or position.stop <= self.modifications[index][0].start
		assert index == 0 or self.modifications[index-1][0].stop <= position.start
		self.modifications.insert(index, modification)

	# flush the registered modifications
	def apply_modifications(self) -> None:
		if not self.modifications:
			return
		contents = self.contents
		# applied in reverse order to not mess up offsets
		for position, replacement in reversed(self.modifications):
			contents = contents[:position.start] + replacement + contents[position.stop:]
		# write the contents to the file
		newline = '\r\n' if b'\r\n' in self.path.read_bytes() else '\n'
		with self.path.open('w', encoding='utf8', newline=newline) as f:
			f.write(contents)
		# update the contents in memory
		self.contents = contents
		self.modifications.clear()
		# delete the cached properties that rely on the contents
		_ = (self.line_offsets, self.ast, self.functions, self.exports, self.imports, self.offset_for_adding_imports)
		del self.line_offsets, self.ast, self.functions, self.exports, self.imports, self.offset_for_adding_imports

	@functools.cached_property
	def ast(self) -> ast.Module:
		return ast.parse(self.contents, self.name)

	@functools.cached_property
	def functions(self) -> list[Func]:
		funcs = []

		for node in ast.walk(self.ast):
			if isinstance(node, ast.FunctionDef):
				funcs.append(Func(self, node))

			# some __init__ functions list their parameters in the class docstring
			elif isinstance(node, ast.ClassDef):
				cls = node
				class_docstring = ast.get_docstring(cls)
				if class_docstring and 'Parameters' in class_docstring:
					for node2 in ast.walk(cls):
						if isinstance(node2, ast.FunctionDef) and node2.name == '__init__':
							func = node2
							assert ast.get_docstring(func) is None
							funcs.append(Func(self, func, node_with_docstring=cls))

		return funcs

	@functools.cached_property
	def exports(self) -> set[str]:
		# the names of all the classes define in this file
		return {node.name for node in ast.walk(self.ast) if isinstance(node, ast.ClassDef)}

	@functools.cached_property
	def imports(self) -> set[str]:
		imports = set()

		for node in ast.walk(self.ast):
			if not isinstance(node, (ast.Import, ast.ImportFrom)):
				continue
			if isinstance(node, ast.ImportFrom) and node.module == '__future__':
				continue
			if isinstance(node, ast.ImportFrom) and node.names[0].name == '*':
				# `from typing import *` appears in the code so we take advantage of it
				if node.module == 'typing':
					imports |= set(dir(typing))
				# ignore all other star imports
				continue

			# add the names that this import adds to the global scope
			imports |= {n.asname or n.name.split('.')[0] for n in node.names}

		return imports

	@functools.cached_property
	def offset_for_adding_imports(self) -> int:
		last_import_line = max(
			node.end_lineno
			for node in ast.iter_child_nodes(self.ast)
			if isinstance(node, (ast.Import, ast.ImportFrom))
		)
		# the offset of the first line after the last import
		return self.line_offsets[last_import_line]

	def add_imports_for_expression(self, expression: str) -> str:
		expression = ast.parse(expression)

		# find all the names used in the annotation that we need to import
		builtin_names = set(__builtins__ if isinstance(__builtins__, dict) else dir(__builtins__))
		already_imported = builtin_names | self.imports | self.exports | self.to_import
		to_import = {node.id for node in ast.walk(expression) if isinstance(node, ast.Name)}
		to_import -= already_imported

		class SimplifyImports(ast.NodeTransformer):
			# in some cases `foo.bar` is used and `foo` is not imported but `bar` is,
			# so switch the annotation to use `bar` directly
			def visit_Attribute(self, node):
				if isinstance(node.value, ast.Name) and node.attr in (already_imported | to_import):
					if node.value.id in to_import:
						to_import.remove(node.value.id)
					return ast.Name(node.attr)

				self.generic_visit(node)
				return node

			# if `typing` is imported, use it instead of adding more imports
			def visit_Name(self, node):
				if node.id not in already_imported and 'typing' in (already_imported | to_import) and node.id in dir(typing):
					if node.id in to_import:
						to_import.remove(node.id)
					return ast.Attribute(ast.Name('typing'), node.id)

				return node

		# simplify imports and update the expression accordingly
		SimplifyImports().visit(expression)
		expression = ast.unparse(expression)

		# add to the set of the current file
		if to_import:
			self.to_import |= to_import

		# return the updated expression
		return expression

	def register_imports_modification(self, all_files: list[File]) -> None:
		if not self.to_import:
			return

		# map from name to the name of the module it's defined at
		name_to_defining_module = {
			export: file.module_name
			for file in all_files
			if file.module_name
			for export in file.exports
		}
		name_to_defining_module = {name: 'typing' for name in dir(typing)} | name_to_defining_module
		# map from name to an import statement that imports it
		name_to_import_stmt = {
			name: f'from {module} import {name}\n'
			for name, module in name_to_defining_module.items()
		}
		name_to_import_stmt |= {'np': 'import numpy as np\n'}

		# if we need to guard cyclic imports, import TYPE_CHECKING
		if any((self.name, name) in CIRCULAR_IMPORTS for name in self.to_import):
			type_checking_flag = self.add_imports_for_expression('TYPE_CHECKING')

		# separate the imports by whether or not they cause a cyclic import
		names_to_import = set()
		names_to_guard = set()
		for name in self.to_import:
			if (self.name, name) in CIRCULAR_IMPORTS:
				names_to_guard.add(name)
			else:
				names_to_import.add(name)

		# build a string of imports to add
		imports = ''
		# add the normal imports
		for name in sorted(names_to_import):
			imports += name_to_import_stmt[name]
		# add the guarded imports
		if names_to_guard:
			imports += f'if {type_checking_flag}:\n'
			for name in sorted(names_to_guard):
				imports += '    ' + name_to_import_stmt[name]

		# add the imports to the file
		self.register_modification(slice(self.offset_for_adding_imports, self.offset_for_adding_imports), imports)

		self.to_import.clear()

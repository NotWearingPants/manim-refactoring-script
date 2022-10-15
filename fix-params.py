from __future__ import annotations
import argparse

import ast
import pathlib

from file import File
from func import Func
from special_cases import NAME_REPLACEMENTS, SPECIAL_CASES_FOR_COMPARING_TYPES, SPECIAL_CASES_FOR_CONVERTING_TYPES
from utils import cleanup_type, get_indent_size_at, zip_dicts


# marker to add for further investigation (for grepping later)
MAGIC_MARKER = 'TODO TYPEHINTS'

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('manim_root', type=pathlib.Path)
	args = parser.parse_args()
	assert (args.manim_root / 'README.md').is_file(), 'The given folder is not the root of a manim repo'

	# load and parse all files
	print('Loading...')
	files = [File(file, file.relative_to(args.manim_root)) for file in args.manim_root.glob('**/*.py')]
	print(f'\tTotal files: {len(files)}')
	funcs = [func for file in files for func in file.functions]
	print(f'\tTotal functions: {len(funcs)}')
	print(f'\tTotal parameters: {sum(len(f.func_args) for f in funcs)}')
	funcs_with_docstring = [f for f in funcs if f.has_docstring]
	print(f'\tTotal functions with a docstring: {len(funcs_with_docstring)}')
	funcs_with_params_in_docstring = [f for f in funcs_with_docstring if f.doc_args]
	print(f'\tTotal functions with parameters in their docstring: {len(funcs_with_params_in_docstring)}')
	print(f'\tTotal parameters in docstrings: {sum(len(f.doc_args) for f in funcs_with_params_in_docstring)}')
	funcs_with_param_types_in_docstring = [f for f in funcs_with_params_in_docstring if any(arg.type for arg in f.doc_args.values())]
	print(f'\tTotal functions with parameter types in their docstring: {len(funcs_with_param_types_in_docstring)}')
	print(f'\tTotal parameter types in docstrings: {sum(1 for f in funcs_with_params_in_docstring for arg in f.doc_args.values() if arg.type)}')

	# fix the functions
	print('Fixing...')
	fix_unknown_args(funcs_with_params_in_docstring)
	fix_args_with_redundant_types(funcs_with_param_types_in_docstring)
	fix_args_with_no_type_annotation(funcs_with_param_types_in_docstring)

	# apply the changes
	print('Writing...')
	for f in files:
		f.register_imports_modification(files)
	files_modified = len([f.apply_modifications() for f in files if f.modifications])
	print(f'\tTotal files modified: {files_modified}')
	print('Done.')


# args which are only mentioned in the docstring but no such arg exists in the function => put a marker
def fix_unknown_args(funcs: list[Func]):
	fixed = 0
	marked = 0
	for f in funcs:
		# is only in docstring but not in the function
		for name, doc_arg in list(f.doc_args.items()):
			if name not in f.func_args:
				new_name = NAME_REPLACEMENTS.get((f.file.name, f.func.name, name))

				if new_name is not None:
					if new_name:
						f.rename_doc_arg(name, new_name)
					else:
						f.delete_doc_arg(name)

					fixed += 1
				else:
					# add a marker in a comment on the next line for further investigation
					indent = get_indent_size_at(f.file.contents, doc_arg.position.start)
					f.file.register_modification(
						slice(doc_arg.annotation_position.stop, doc_arg.annotation_position.stop),
						f'\n{" " * (indent + 4)}# {MAGIC_MARKER}',
					)

					marked += 1

	print(f'\tFixed {fixed} unknown args, marked {marked} unknown args for inspection')


# args have a type both in the docstring and in a type annotation => delete the type in the docstring
def fix_args_with_redundant_types(funcs: list[Func]):
	fixed = 0
	for f in funcs:
		for name, (func_arg, doc_arg) in zip_dicts(f.func_args, f.doc_args).items():
			# has a type both in the docstring and in a type annotation
			if func_arg.type and doc_arg.type:
				# clean both the type in the annotation and in the docstring
				clean_doc_arg = cleanup_type(doc_arg.type)
				clean_func_arg = cleanup_type(func_arg.type)
				# verify the types are identical or in the other cases we know
				assert (
					clean_doc_arg == clean_func_arg or
					(f.file.name, f.func.name, name, clean_func_arg, clean_doc_arg) in SPECIAL_CASES_FOR_COMPARING_TYPES
				), f'[{f}][arg {name}] {func_arg.type} VS {doc_arg.type} CLEANED TO {clean_func_arg} VS {clean_doc_arg}'
				# delete the type in the docstring
				doc_arg.delete_annotation()

				fixed += 1

	print(f'\tFixed {fixed} args with redundant types')


# args which have a type in the docstring and no type annotation => convert the docstring type to an annotation and delete it
def fix_args_with_no_type_annotation(funcs: list[Func]):
	fixed = 0
	for f in funcs:
		for name, (func_arg, doc_arg) in zip_dicts(f.func_args, f.doc_args).items():
			# has a type in the docstring but no type annotation
			if not func_arg.type and doc_arg.type:
				# kwargs should not be annotated
				if name != 'kwargs':
					# clean up the type from the docstring
					replacement = cleanup_type(doc_arg.type)
					# special cases
					replacement = SPECIAL_CASES_FOR_CONVERTING_TYPES.get((f.file.name, f.func.name, name, replacement), replacement)

					# if the replacement is empty don't add an annotation
					if replacement:
						# add `| None` if this argument has a default which is `None`
						if isinstance(func_arg.default, ast.Constant) and func_arg.default.value is None:
							replacement = f'{replacement} | None'

						# add imports for the type annotation in the current file
						replacement = f.file.add_imports_for_expression(replacement)

						# add the type annotation
						func_arg.set_annotation(replacement)

				# delete the type in the docstring
				doc_arg.delete_annotation()

				fixed += 1

	print(f'\tFixed {fixed} args with no type annotation')


if __name__ == '__main__':
	main()

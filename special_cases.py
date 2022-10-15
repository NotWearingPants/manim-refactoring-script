NAME_REPLACEMENTS = {
	# wrong names, perhaps the name was changed and the docstring wasn't updated
	('manim/utils/hashing.py', 'get_json', 'dict_config'): 'obj',
	('manim/scene/vector_space_scene.py', 'vector_to_coords', 'integer_label'): 'integer_labels',
	('manim/scene/vector_space_scene.py', 'get_transposed_matrix_transformation', 'matrix'): 'transposed_matrix',
	('manim/scene/vector_space_scene.py', 'apply_transposed_matrix', 'matrix'): 'transposed_matrix',
	('manim/scene/vector_space_scene.py', 'apply_inverse_transpose', 'matrix'): 't_matrix',
	('manim/scene/scene_file_writer.py', 'write_frame', 'frame'): 'frame_or_renderer',
	('manim/mobject/types/vectorized_mobject.py', '__init__', 'tolerance_point_for_equality'): 'tolerance_for_point_equality',
	('manim/cli/init/commands.py', 'update_cfg', 'cfg'): 'cfg_dict',
	('manim/cli/new/group.py', 'update_cfg', 'cfg'): 'cfg_dict',
	# copy-paste error from the `shift_func` function above, but the description is correct
	('manim/mobject/vector_field.py', 'scale_func', 'shift_vector'): 'scalar',
	# don't know how that was mixed-up, but the description is correct
	('manim/mobject/opengl/opengl_vectorized_mobject.py', 'set_fill', 'family'): 'recurse',
	# names to delete because they don't exist entirely
	('manim/camera/three_d_camera.py', '__init__', 'args'): '',
	('manim/mobject/geometry/shape_matchers.py', '__init__', 'Line'): '',
	('manim/mobject/graphing/number_line.py', '_create_label_tex', 'label_constructor'): '',
	('manim/mobject/table.py', 'create', 'run_time'): '',
	('manim/mobject/vector_field.py', 'get_vector', 'kwargs'): '',
	('manim/renderer/cairo_renderer.py', 'update_frame', 'background'): '',
	('manim/utils/testing/frames_comparison.py', 'frames_comparison', 'module_name'): '',
	('manim/utils/testing/frames_comparison.py', 'frames_comparison', 'test_name'): '',
	('tests/utils/GraphicalUnitTester.py', '__init__', 'config_scene'): '',
}

# the cases we couldn't automatically verify,
# they seem fine (it's okay if the left one is better, it's the one we keep)
SPECIAL_CASES_FOR_COMPARING_TYPES = [
	('manim/_config/utils.py', 'digest_parser', 'parser', 'configparser.ConfigParser', 'ConfigParser'),
	('manim/animation/creation.py', '__init__', 'mobject', 'VMobject | OpenGLVMobject | OpenGLSurface', 'VMobject'),
	('manim/camera/camera.py', 'display_image_mobject', 'image_mobject', 'AbstractImageMobject', 'ImageMobject'),
	('manim/mobject/geometry/polygram.py', '__init__', 'color', 'Color', 'Colors'),
	('manim/mobject/types/vectorized_mobject.py', 'set_points_as_corners', 'points', 'Sequence[float]', 'Iterable[float]'),
	('manim/scene/three_d_scene.py', 'move_camera', 'added_anims', 'Iterable[Animation]', 'list'),
	('manim/scene/three_d_scene.py', 'move_camera', 'frame_center', 'Mobject | Sequence[float]', 'list | tuple | np.ndarray'),
	('manim/scene/three_d_scene.py', 'set_camera_orientation', 'frame_center', 'Mobject | Sequence[float]', 'list | tuple | np.ndarray')  ,
	# the types of `angle` and `axis` are swapped, we'll fix this later
	('manim/mobject/types/vectorized_mobject.py', 'rotate_sheen_direction', 'angle', 'np.ndarray', 'float'),
	('manim/mobject/types/vectorized_mobject.py', 'rotate_sheen_direction', 'axis', 'float', 'np.ndarray'),
]

# specific cases checked manually
SPECIAL_CASES_FOR_CONVERTING_TYPES = {
	# string which is either 'left' or 'right'
	('manim/scene/vector_space_scene.py', 'get_vector_label', 'direction', '{"left"}'): 'str',
	# `type`, not a list of `type`
	('manim/utils/testing/frames_comparison.py', '_make_test_comparing_frames', 'renderer_class', '[type]'): 'type',
	# should be a class inheriting from `Scene` and not an instance
	('tests/helpers/graphical_units.py', 'set_test_scene', 'scene_object', 'Scene'): 'type[Scene]',
	('tests/utils/GraphicalUnitTester.py', '__init__', 'scene_class', 'Scene'): 'type[Scene]',
	# `*args` tagged as a tuple, mypy expects `*args` to be tagged with the type of a single element
	('manim/scene/scene.py', 'compile_animations', 'args', 'tuple[Animation]'): 'Animation',
	# `*args` tagged as `Mobjects`, the plural of `Mobject`
	('manim/scene/three_d_scene.py', 'add_fixed_in_frame_mobjects', 'mobjects', 'Mobjects'): 'Mobject',
	('manim/scene/three_d_scene.py', 'remove_fixed_orientation_mobjects', 'mobjects', 'Mobjects'): 'Mobject',
	('manim/scene/three_d_scene.py', 'remove_fixed_in_frame_mobjects', 'mobjects', 'Mobjects'): 'Mobject',
	# list of mobjects tagged as a single `Mobject`
	('manim/camera/camera.py', 'capture_mobjects', 'mobjects', 'Mobject'): 'Iterable[Mobject]',
	('manim/camera/camera.py', 'get_mobjects_to_display', 'mobjects', 'Mobject'): 'Iterable[Mobject]',
	('manim/utils/family.py', 'extract_mobject_family_members', 'mobjects', 'Mobject'): 'Iterable[Mobject]',
	# list of mobjects with no type
	('manim/renderer/cairo_renderer.py', 'update_frame', 'mobjects', 'list'): 'Iterable[Mobject]',
	# background image as numpy array
	('manim/camera/camera.py', '__init__', 'background', 'optional'): 'np.ndarray',
	# `gain` value for sound (passed to the `pydub` package)
	('manim/scene/scene_file_writer.py', 'add_audio_segment', 'gain_to_background', 'optional'): 'float',
	('manim/scene/scene_file_writer.py', 'add_sound', 'gain', 'optional'): 'float',
	# callback types
	('manim/camera/camera.py', 'make_background_from_func', 'coords_to_colors_func', 'function'): 'Callable[[np.ndarray], np.ndarray]',
	('manim/camera/camera.py', 'set_background_from_func', 'coords_to_colors_func', 'function'): 'Callable[[np.ndarray], np.ndarray]',
	('manim/camera/three_d_camera.py', 'add_fixed_orientation_mobjects', 'center_func', 'func'): 'Callable[[], np.ndarray]',
	('manim/scene/scene.py', 'wait_until', 'stop_condition', 'function'): 'Callable[[], bool]',
	('manim/scene/vector_space_scene.py', 'get_moving_mobject_movement', 'func', 'function'): 'Callable[[np.ndarray], np.ndarray]',
	('manim/scene/vector_space_scene.py', 'get_vector_movement', 'func', 'function'): 'Callable[[np.ndarray], np.ndarray]',
	('manim/scene/vector_space_scene.py', 'apply_nonlinear_transformation', 'function', 'Function'): 'Callable[[np.ndarray], np.ndarray]',
	('manim/scene/vector_space_scene.py', 'apply_function', 'function', 'Function'): 'Callable[[np.ndarray], np.ndarray]',
	# string args which actually accept `Path` objects as well
	('tests/utils/logging_tester.py', 'logs_comparison', 'control_data_file', 'str'): 'str | os.PathLike',
	('tests/utils/logging_tester.py', 'logs_comparison', 'log_path_from_media_dir', 'str'): 'str | os.PathLike',
	# crazy type for a dict of VMobjects causing trouble
	('manim/mobject/types/vectorized_mobject.py', '__init__', 'mapping_or_iterable', 'Union[Mapping, Iterable[tuple[Hashable, VMobject]]]'):
		'Union[Mapping[Hashable, VMobject], Iterable[Tuple[Hashable, VMobject]]]',
	('manim/mobject/types/vectorized_mobject.py', 'add', 'mapping_or_iterable', 'Union[Mapping, Iterable[tuple[Hashable, VMobject]]]'):
		'Union[Mapping[Hashable, VMobject], Iterable[Tuple[Hashable, VMobject]]]',
	# was changed to support opengl but the docstring wasn't updated
	('manim/scene/scene_file_writer.py', 'write_frame', 'frame_or_renderer', 'np.ndarray'): 'np.ndarray | OpenGLRenderer',
}

# imports that if added will cause a cycle, so we will guard them with `if TYPE_CHECKING`
# these were found by running the tests and getting circular-import errors
CIRCULAR_IMPORTS = [
	('manim/utils/hashing.py', 'Scene'),
	('manim/scene/scene_file_writer.py', 'OpenGLRenderer'),
	('manim/renderer/cairo_renderer.py', 'Scene'),
]

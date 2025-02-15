import builtins as __builtin__
import ctypes
import gc
import inspect
from collections import defaultdict
from contextlib import contextmanager
from ctypes import (
    c_int,
    c_int64,
    c_int32,
    c_void_p,
    pythonapi,
)
from functools import wraps

__all__ = 'curse', 'curses', 'reverse'

Py_ssize_t = c_int64 if ctypes.sizeof(c_void_p) == 8 else c_int32

# dictionary holding references to the allocated function resolution
# arrays to type objects
tp_as_dict = {}
# container to cfunc callbacks
tp_func_dict = {}


class PyObject(ctypes.Structure):
    def incref(self):
        self.ob_refcnt += 1

    def decref(self):
        self.ob_refcnt -= 1


class PyFile(ctypes.Structure):
    pass


PyObject_p = ctypes.py_object
Inquiry_p = ctypes.CFUNCTYPE(c_int, PyObject_p)
# return type is void* to allow ctypes to convert python integers to
# plain PyObject*
UnaryFunc_p = ctypes.CFUNCTYPE(ctypes.py_object, PyObject_p)
BinaryFunc_p = ctypes.CFUNCTYPE(ctypes.py_object, PyObject_p, PyObject_p)
TernaryFunc_p = ctypes.CFUNCTYPE(
    ctypes.py_object, PyObject_p, PyObject_p, PyObject_p
)
LenFunc_p = ctypes.CFUNCTYPE(Py_ssize_t, PyObject_p)
SSizeArgFunc_p = ctypes.CFUNCTYPE(ctypes.py_object, PyObject_p, Py_ssize_t)
SSizeObjArgProc_p = ctypes.CFUNCTYPE(c_int, PyObject_p, Py_ssize_t, PyObject_p)
ObjObjProc_p = ctypes.CFUNCTYPE(c_int, PyObject_p, PyObject_p)

FILE_p = ctypes.POINTER(PyFile)


def get_not_implemented():
    namespace = {}
    name = "_Py_NotImplmented"
    # noinspection PyProtectedMember
    not_implemented = ctypes.cast(
        pythonapi._Py_NotImplementedStruct, ctypes.py_object)

    pythonapi.PyDict_SetItem(
        ctypes.py_object(namespace),
        ctypes.py_object(name),
        not_implemented
    )
    return namespace[name]


# address of the _Py_NotImplementedStruct singleton
NotImplementedRet = get_not_implemented()


class PyNumberMethods(ctypes.Structure):
    _fields_ = [
        ('nb_add', BinaryFunc_p),
        ('nb_subtract', BinaryFunc_p),
        ('nb_multiply', BinaryFunc_p),
        ('nb_remainder', BinaryFunc_p),
        ('nb_divmod', BinaryFunc_p),
        ('nb_power', BinaryFunc_p),
        ('nb_negative', UnaryFunc_p),
        ('nb_positive', UnaryFunc_p),
        ('nb_absolute', UnaryFunc_p),
        ('nb_bool', Inquiry_p),
        ('nb_invert', UnaryFunc_p),
        ('nb_lshift', BinaryFunc_p),
        ('nb_rshift', BinaryFunc_p),
        ('nb_and', BinaryFunc_p),
        ('nb_xor', BinaryFunc_p),
        ('nb_or', BinaryFunc_p),
        ('nb_int', UnaryFunc_p),
        ('nb_reserved', c_void_p),
        ('nb_float', UnaryFunc_p),

        ('nb_inplace_add', BinaryFunc_p),
        ('nb_inplace_subtract', BinaryFunc_p),
        ('nb_inplace_multiply', BinaryFunc_p),
        ('nb_inplace_remainder', BinaryFunc_p),
        ('nb_inplace_power', TernaryFunc_p),
        ('nb_inplace_lshift', BinaryFunc_p),
        ('nb_inplace_rshift', BinaryFunc_p),
        ('nb_inplace_and', BinaryFunc_p),
        ('nb_inplace_xor', BinaryFunc_p),
        ('nb_inplace_or', BinaryFunc_p),

        ('nb_floor_divide', BinaryFunc_p),
        ('nb_true_divide', BinaryFunc_p),
        ('nb_inplace_floor_divide', BinaryFunc_p),
        ('nb_inplace_true_divide', BinaryFunc_p),

        ('nb_index', BinaryFunc_p),

        ('nb_matrix_multiply', BinaryFunc_p),
        ('nb_inplace_matrix_multiply', BinaryFunc_p),
    ]


class PySequenceMethods(ctypes.Structure):
    _fields_ = [
        ('sq_length', LenFunc_p),
        ('sq_concat', BinaryFunc_p),
        ('sq_repeat', SSizeArgFunc_p),
        ('sq_item', SSizeArgFunc_p),
        ('was_sq_slice', c_void_p),
        ('sq_ass_item', SSizeObjArgProc_p),
        ('was_sq_ass_slice', c_void_p),
        ('sq_contains', ObjObjProc_p),
        ('sq_inplace_concat', BinaryFunc_p),
        ('sq_inplace_repeat', SSizeArgFunc_p),
    ]


class PyMappingMethods(ctypes.Structure):
    pass


class PyTypeObject(ctypes.Structure):
    pass


class PyAsyncMethods(ctypes.Structure):
    pass


PyObject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', ctypes.POINTER(PyTypeObject)),
]

# noinspection SpellCheckingInspection
PyTypeObject._fields_ = [
    # varhead
    ('ob_base', PyObject),
    ('ob_size', Py_ssize_t),
    # declaration
    ('tp_name', ctypes.c_char_p),
    ('tp_basicsize', Py_ssize_t),
    ('tp_itemsize', Py_ssize_t),
    ('tp_dealloc', ctypes.CFUNCTYPE(None, PyObject_p)),
    ('printfunc',
     ctypes.CFUNCTYPE(c_int, PyObject_p, FILE_p, c_int)),
    ('getattrfunc', ctypes.CFUNCTYPE(PyObject_p, PyObject_p, ctypes.c_char_p)),
    ('setattrfunc',
     ctypes.CFUNCTYPE(c_int, PyObject_p, ctypes.c_char_p, PyObject_p)),
    ('tp_as_async', ctypes.CFUNCTYPE(PyAsyncMethods)),
    ('tp_repr', ctypes.CFUNCTYPE(PyObject_p, PyObject_p)),
    ('tp_as_number', ctypes.POINTER(PyNumberMethods)),
    ('tp_as_sequence', ctypes.POINTER(PySequenceMethods)),
    ('tp_as_mapping', ctypes.POINTER(PyMappingMethods)),
    ('tp_hash', ctypes.CFUNCTYPE(c_int64, PyObject_p)),
    ('tp_call',
     ctypes.CFUNCTYPE(PyObject_p, PyObject_p, PyObject_p, PyObject_p)),
    ('tp_str', ctypes.CFUNCTYPE(PyObject_p, PyObject_p)),
    ('tp_getattro', c_void_p),  # Type not declared yet
    ('tp_setattro', c_void_p),  # Type not declared yet
    ('tp_as_buffer', c_void_p),  # Type not declared yet
    ('tp_flags', c_void_p),  # Type not declared yet
    ('tp_doc', c_void_p),  # Type not declared yet
    ('tp_traverse', c_void_p),  # Type not declared yet
    ('tp_clear', c_void_p),  # Type not declared yet
    ('tp_richcompare', c_void_p),  # Type not declared yet
    ('tp_weaklistoffset', c_void_p),  # Type not declared yet
    ('tp_iter', c_void_p),  # Type not declared yet
    ('iternextfunc', c_void_p),  # Type not declared yet
    ('tp_methods', c_void_p),  # Type not declared yet
    ('tp_members', c_void_p),  # Type not declared yet
    ('tp_getset', c_void_p),  # Type not declared yet
    ('tp_base', c_void_p),  # Type not declared yet
    ('tp_dict', c_void_p),  # Type not declared yet
    ('tp_descr_get', c_void_p),  # Type not declared yet
    ('tp_descr_set', c_void_p),  # Type not declared yet
    ('tp_dictoffset', c_void_p),  # Type not declared yet
    ('tp_init', c_void_p),  # Type not declared yet
    ('tp_alloc', c_void_p),  # Type not declared yet
    ('tp_new',
     ctypes.CFUNCTYPE(PyObject_p, PyObject_p, PyObject_p, c_void_p)),
    # More struct fields follow but aren't declared here yet ...
]

# redundant dict of pointee types, because ctypes doesn't allow us
# to extract the pointee type from the pointer
PyTypeObject_as_types_dict = {
    'tp_as_async': PyAsyncMethods,
    'tp_as_number': PyNumberMethods,
    'tp_as_sequence': PySequenceMethods,
    'tp_as_mapping': PyMappingMethods,
}


def patchable_builtin(klass):
    refs = gc.get_referents(klass.__dict__)
    assert len(refs) == 1
    return refs[0]


@wraps(__builtin__.dir)
def __filtered_dir__(obj=None):
    name = hasattr(obj, '__name__') and obj.__name__ or obj.__class__.__name__
    if obj is None:
        # Return names from the local scope of the calling frame,
        # taking into account indirection added by __filtered_dir__
        calling_frame = inspect.currentframe().f_back
        return sorted(calling_frame.f_locals.keys())
    return sorted(set(__dir__(obj)).difference(__hidden_elements__[name]))


# Switching to the custom dir impl declared above
__hidden_elements__ = defaultdict(list)
__dir__ = dir
__builtin__.dir = __filtered_dir__

# build override information for dunder methods
# noinspection SpellCheckingInspection
as_number = ('tp_as_number', [
    ("add", "nb_add"),
    ("sub", "nb_subtract"),
    ("mul", "nb_multiply"),
    ("mod", "nb_remainder"),
    ("pow", "nb_power"),
    ("neg", "nb_negative"),
    ("pos", "nb_positive"),
    ("abs", "nb_absolute"),
    ("bool", "nb_bool"),
    ("inv", "nb_invert"),
    ("invert", "nb_invert"),
    ("lshift", "nb_lshift"),
    ("rshift", "nb_rshift"),
    ("and", "nb_and"),
    ("xor", "nb_xor"),
    ("or", "nb_or"),
    ("int", "nb_int"),
    ("float", "nb_float"),
    ("iadd", "nb_inplace_add"),
    ("isub", "nb_inplace_subtract"),
    ("imul", "nb_inplace_multiply"),
    ("imod", "nb_inplace_remainder"),
    ("ipow", "nb_inplace_power"),
    ("ilshift", "nb_inplace_lshift"),
    ("irshift", "nb_inplace_rshift"),
    ("iadd", "nb_inplace_and"),
    ("ixor", "nb_inplace_xor"),
    ("ior", "nb_inplace_or"),
    ("floordiv", "nb_floor_divide"),
    ("div", "nb_true_divide"),
    ("ifloordiv", "nb_inplace_floor_divide"),
    ("idiv", "nb_inplace_true_divide"),
    ("index", "nb_index"),
    ("matmul", "nb_matrix_multiply"),
    ("imatmul", "nb_inplace_matrix_multiply"),
])

# noinspection SpellCheckingInspection
as_sequence = ("tp_as_sequence", [
    ("len", "sq_length"),
    ("concat", "sq_concat"),
    ("repeat", "sq_repeat"),
    ("getitem", "sq_item"),
    ("setitem", "sq_ass_item"),
    ("contains", "sq_contains"),
    ("iconcat", "sq_inplace_concat"),
    ("irepeat", "sq_inplace_repeat"),
])

as_async = ("tp_as_async", [
    ("await", "am_await"),
    ("aiter", "am_aiter"),
    ("anext", "am_anext"),
])

override_dict = {}
for override in [as_number, as_sequence, as_async]:
    tp_as_name = override[0]
    for dunder, impl_method in override[1]:
        override_dict["__{}__".format(dunder)] = (tp_as_name, impl_method)

# divmod isn't a dunder, still make it overridable
override_dict['divmod()'] = ('tp_as_number', "nb_divmod")
override_dict['__str__'] = ('tp_str', "tp_str")
override_dict['__new__'] = ('tp_new', "tp_new")


def _is_dunder(func_name):
    return func_name.startswith("__") and func_name.endswith("__")


# noinspection PyProtectedMember,PyUnboundLocalVariable
def _curse_special(klass, attr, func):
    """
    Curse one of the "dunder" methods, i.e. methods beginning with __ which have
    a precial resolution code path
    """
    assert callable(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        This wrapper returns the address of the resulting object as a
        python integer which is then converted to a pointer by ctypes
        """
        try:
            return func(*args, **kwargs)
        except NotImplementedError:
            return NotImplementedRet

    nonlocal tp_as_name, impl_method
    tp_as_name, impl_method = override_dict[attr]

    # get the pointer to the correct tp_as_* structure
    # or create it if it doesn't exist
    type_obj = PyTypeObject.from_address(id(klass))
    if tp_as_name in PyTypeObject_as_types_dict:
        struct_ty = PyTypeObject_as_types_dict[tp_as_name]
        tp_as_ptr = getattr(type_obj, tp_as_name)
        if not tp_as_ptr:
            # allocate new array
            tp_as_obj = struct_ty()
            tp_as_dict[(klass, attr)] = tp_as_obj
            tp_as_new_ptr = ctypes.cast(ctypes.addressof(tp_as_obj),
                                        ctypes.POINTER(struct_ty))

            setattr(type_obj, tp_as_name, tp_as_new_ptr)
        tp_as = tp_as_ptr[0]

        # find the C function type
        for field_name, field_type in struct_ty._fields_:
            if field_name == impl_method:
                cfunc_t = field_type

        cfunc = cfunc_t(wrapper)
        tp_func_dict[(klass, attr)] = cfunc

        setattr(tp_as, impl_method, cfunc)
    else:
        # find the C function type
        for field_name, field_type in PyTypeObject._fields_:
            if field_name == impl_method:
                cfunc_t = field_type

        if not (klass, attr) in tp_as_dict:
            tp_as_dict[(klass, attr)] = ctypes.cast(
                getattr(type_obj, impl_method), cfunc_t)

        # override function call
        cfunc = cfunc_t(wrapper)
        tp_func_dict[(klass, attr)] = cfunc
        setattr(type_obj, impl_method, cfunc)


# noinspection PyUnboundLocalVariable,PyProtectedMember
def _revert_special(klass, attr):
    nonlocal tp_as_name, impl_method
    tp_as_name, impl_method = override_dict[attr]
    type_obj = PyTypeObject.from_address(id(klass))
    tp_as_ptr = getattr(type_obj, tp_as_name)
    if tp_as_ptr:
        if tp_as_name in PyTypeObject_as_types_dict:
            tp_as = tp_as_ptr[0]

            struct_ty = PyTypeObject_as_types_dict[tp_as_name]
            for field_name, field_type in struct_ty._fields_:
                if field_name == impl_method:
                    cfunc_t = field_type

            setattr(tp_as, impl_method,
                    ctypes.cast(c_void_p(None), cfunc_t))
        else:
            if not (klass, attr) in tp_as_dict:
                # we didn't save this pointer
                # most likely never cursed
                return

            cfunc = tp_as_dict[(klass, attr)]
            setattr(type_obj, impl_method, cfunc)


def curse(klass, attr, value, hide_from_dir=False):
    # noinspection PyUnresolvedReferences, SpellCheckingInspection
    """Curse a built-in `klass` with `attr` set to `value`

        This function monkey-patches the built-in python object `attr` adding a
        new attribute to it. You can add any kind of argument to the `class`.

        It's possible to attach methods as class methods, just do the following:

          >>> def myclassmethod(cls):
          ...     return cls(1.5)
          >>> curse(float, "myclassmethod", classmethod(myclassmethod))
          >>> float.myclassmethod()
          1.5

        Methods will be automatically bound, so don't forget to add a self
        parameter to them, like this:

          >>> def hello(self):
          ...     return self * 2
          >>> curse(str, "hello", hello)
          >>> "yo".hello()
          "yoyo"
        """
    if _is_dunder(attr):
        _curse_special(klass, attr, value)
        return

    dikt = patchable_builtin(klass)

    old_value = dikt.get(attr, None)
    old_name = '_c_%s' % attr  # do not use .format here, it breaks py2.{5,6}

    # Patch the thing
    dikt[attr] = value

    if old_value:
        hide_from_dir = False  # It was already in dir
        dikt[old_name] = old_value

        try:
            dikt[attr].__name__ = old_value.__name__
        except (AttributeError, TypeError):  # py2.5 will raise `TypeError`
            pass
        try:
            dikt[attr].__qualname__ = old_value.__qualname__
        except AttributeError:
            pass

    pythonapi.PyType_Modified(ctypes.py_object(klass))

    if hide_from_dir:
        __hidden_elements__[klass.__name__].append(attr)


def reverse(klass, attr):
    """Reverse a curse in a built-in object

    This function removes *new* attributes. It's actually possible to remove
    any kind of attribute from any built-in class, but just DON'T DO IT :)

    Good:

      >>> curse(str, "blah", "bleh")
      >>> assert "blah" in dir(str)
      >>> reverse(str, "blah")
      >>> assert "blah" not in dir(str)

    Bad:

      >>> reverse(str, "strip")
      >>> " blah ".strip()
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
      AttributeError: 'str' object has no attribute 'strip'

    """
    if _is_dunder(attr):
        _revert_special(klass, attr)
        return

    dikt = patchable_builtin(klass)
    del dikt[attr]

    pythonapi.PyType_Modified(ctypes.py_object(klass))


def curses(klass, name):
    # noinspection PyUnresolvedReferences, SpellCheckingInspection
    """Decorator to add decorated method named `name` the class `klass`

    So you can use it like this:

        >>> @curses(dict, 'banner')
        ... def dict_banner(self):
        ...     l = len(self)
        ...     print('This dict has {0} element{1}'.format(
        ...         l, l is 1 and '' or 's')
        >>> {'a': 1, 'b': 2}.banner()
        'This dict has 2 elements'
    """

    def wrapper(func):
        curse(klass, name, func)
        return func

    return wrapper


@contextmanager
def cursed(obj, attr, val, hide_from_dir=False):
    curse(obj, attr, val, hide_from_dir)
    try:
        yield
    finally:
        reverse(obj, attr)

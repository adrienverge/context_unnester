context_unnester
================

`contextlib.nested` is deprecated since Python 2.7 and incompatible with
Python 3. Still, it is used in a wide number of Python projects.

context_unnester helps removing its usage, by automatically fixing the code.
This script:
* detects `contextlib.nested` occurences and replaces them by appropriate
  `with` syntax,
* removes imports of `contextlib` when they are not needed anymore,
* tries to make the replaced code PEP8-compatible.

Usage
-----

```
usage: context_unnester.py [-h] PATH [PATH ...]

positional arguments:
  PATH        Path to source that needs to be fixed

optional arguments:
  -h, --help  show this help message and exit
```
  
Examples of code rewriting
--------------------------

```python
# before:
import contextlib
with contextlib.nested(A(), B(), C()):
    do_stuff()
# after:
with A(), B(), C():
    do_stuff()
```

```python
# before:
import contextlib
with contextlib.nested(A(), B(), C()) as (a, _, c):
    do_stuff(1, a, c)
# after:
with A() as a, B(), C() as c:
    do_stuff(1, a, c)
```

```python
# before:
import contextlib
with contextlib.nested(A(), B(), C()) as abc:
    do_stuff(42, abc)
# after:
with A() as a, B() as b, C() as c:
    abc = (a, b, c)
    do_stuff(42, abc)
```

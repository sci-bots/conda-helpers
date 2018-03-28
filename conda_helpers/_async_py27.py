from __future__ import absolute_import, print_function, unicode_literals
from functools import partial
import io
import itertools as it
import subprocess as sp
import sys

import colorama as _C
import trollius as asyncio


@asyncio.coroutine
def _read_stream(stream, callback=None):
    while True:
        data = yield asyncio.From(stream.read(1))
        if data:
            if callback is not None:
                callback(data)
        else:
            break


@asyncio.coroutine
def run_command(cmd, *args, **kwargs):
    '''
    .. versionchanged:: 0.18
        Display wait indicator if ``verbose`` is set to ``None`` (default).
    '''
    shell = kwargs.pop('shell', True)
    verbose = kwargs.pop('verbose', True)
    if isinstance(cmd, list):
        cmd = sp.list2cmdline(cmd)
    _exec_func = (asyncio.subprocess.create_subprocess_shell
                  if shell else asyncio.subprocess.create_subprocess_exec)
    process = yield asyncio.From(_exec_func(cmd, *args,
                                            stdout=asyncio.subprocess.PIPE,
                                            stderr=asyncio.subprocess.PIPE))
    stdout_ = io.StringIO()
    stderr_ = io.StringIO()

    message = (_C.Fore.MAGENTA + 'Executing:', _C.Fore.WHITE + cmd)
    waiting_indicator = it.cycle(r'\|/-')

    def dump(output, data):
        text = data.decode('utf8')
        if verbose:
            print(text, end='')
        elif verbose is None:
            print('\r' + next(waiting_indicator), *message, end='',
                  file=sys.stderr)
        output.write(text)

    yield asyncio.From(asyncio.wait([_read_stream(process.stdout,
                                                  partial(dump, stdout_)),
                                     _read_stream(process.stderr,
                                                  partial(dump, stderr_))]))

    if verbose is None:
        print('\r' + _C.Fore.GREEN + 'Finished:', message[1], file=sys.stderr)

    return_code = yield asyncio.From(process.wait())
    raise asyncio.Return(return_code, stdout_.getvalue(), stderr_.getvalue())

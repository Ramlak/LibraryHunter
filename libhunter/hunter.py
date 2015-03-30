from __future__ import print_function

__author__ = 'Kalmar'
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from capstone import *


def cut(buff, start, end):
    p = buff.find(start)
    q = buff.find(end, p + len(start))
    if p == -1 or q == -1:
        return "Description not found"
    return buff[p:q]


class WrongFile(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FunctionNotFound(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Hunter(object):
    file_bytes = None
    lib = None
    dynsym = None
    mode = None
    description = None

    def __init__(self, lib):
        self.file_bytes = lib.read()
        self.description = cut(self.file_bytes, "GNU C", "\n")
        lib.seek(0)
        self.lib = ELFFile(lib)
        self.mode = 32 if "32" in self.lib.header.e_ident['EI_CLASS'] else 64
        if self.lib.header.e_type != 'ET_DYN':
            raise WrongFile("Not a shared object file")
        self.dynsym = self.lib.get_section_by_name(b'.dynsym')
        if not isinstance(self.dynsym, SymbolTableSection):
            raise WrongFile("No .dynsym section")

    def find_function_address_by_name(self, name):
        symbol = self.dynsym.get_symbol_by_name(name)
        if not symbol:
            raise FunctionNotFound("Function not found: "+name)
        return symbol.entry.st_value

    def find_main_return_address(self):
        exit_addr = self.dynsym.get_symbol_by_name("exit")
        start_main = self.dynsym.get_symbol_by_name("__libc_start_main")
        if not exit_addr:
            raise FunctionNotFound("No exit? 0_o")
        if not start_main:
            raise FunctionNotFound("No __libc_start_main 0_o")
        code = self.file_bytes[start_main.entry.st_value:start_main.entry.st_value+start_main.entry.st_size]
        CS_MODE = CS_MODE_32 if self.mode == 32 else CS_MODE_64
        md = Cs(CS_ARCH_X86, CS_MODE)
        disassemble = [i for i in md.disasm(code, start_main.entry.st_value)]
        ct = 0
        for i in disassemble:
            if i.mnemonic == 'call':
                try:
                    if int(i.op_str, 16) == exit_addr.entry.st_value:
                        return disassemble[ct-1].address
                except ValueError:
                    pass
            ct += 1
        raise FunctionNotFound("Return address could not be specified")

    def get_all_non_null_symbols(self):
        result = []
        for sym in self.dynsym.iter_symbols():
            if sym.entry.st_value != 0 and sym.name != "":
                result.append([sym.name, sym.entry.st_value])
        return result

    def get_description(self):
        return str(self.description)

    def get_bits_mode(self):
        return str(self.mode)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("usage: {} <libpath> <funcname>")
        exit()

    try:
        hunt = Hunter(open(sys.argv[1], "rb"))
        print("{}:\t\t".format(sys.argv[2]) + hex(hunt.find_function_address_by_name(sys.argv[2])))
        print("main return:\t" + hex(hunt.find_main_return_address()).strip("L"))
        print(hunt.get_description())
        print(hunt.get_bits_mode() + " bits")
    except Exception as e:
        print(e)
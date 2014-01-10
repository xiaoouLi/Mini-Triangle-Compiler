#calc_eval.py

from byteplay import *
from types import CodeType, FunctionType
from pprint import pprint

import scanner
import parser
import ast

import struct
import marshal
import time
import sys


class CodeGenError(Exception):
    """ Code Generator Error """

    def __init__(self, ast):
        self.ast = ast

    def __str__(self):
        return 'Error:  Error at ast node: %s' % (str(self.ast))

class RepeatDeclarationError(Exception):
    def __init__(self,name,level):
        self.name = name
        self.level = level

    def __str__(self):
        return 'Error:  %s is already declared! (level%s)' %(str(self.name),str(self.level))

class NonexistError(Exception):
    def __init__(self,name,level):
        self.name = name
        self.level = level
    def __str__(self):
        return 'Error: %s at level%s is not exist! You have to declare it first!' %(str(self.name),str(self.level))

class UnChangableError(Exception):
    def __init__(self,name,level):
        self.name = name
        self.level = level

    def __str__(self):
        return 'Error:  %s is a const! You cannot change its value! (level%s)' %(str(self.name),str(self.level))

class EmptyStackError(Exception):
    def __str__(self):
        return 'Error:  Stack cannot be empty!'

class NoAssignmentError(Exception):
    def __init__(self,name,level):
        self.name = name
        self.level = level

    def __str__(self):
        return 'Error:  local variable %s referenced before assignment!!! (level%s)' %(str(self.name),str(self.level))

class CodeGen(object):

    def __init__(self, tree):
        self.tree = tree
        self.env = []  # env = [{'x':('x0',Integer,True),'y':('y0',Integer, False)},{'x':'x1'},{'z':'z2'}]
        self.code = []
        self.level = -1
        self.stackSize = 0

    def add_env(self,vname,vtype):
        self.env[self.level][vname] = [vname+str(self.level),vtype,False]


    def lookup_env(self,name):
        """return env list of certain level"""

        for e in self.env[::-1]:
            if name in e:
                return e
        raise NonexistError(name,self.level)

    def level_varname(self,name):
        """ return varname of certain level"""
        return self.lookup_env(name)[name][0]

    def vartype(self,name):
        """ return vartype of certain var of certain level"""
        return self.lookup_env(name)[name][1]

    def var_info(self,name):
        """ return varname declared type of certain level"""
        return self.lookup_env(name)[name]

    def generate(self):

        if type(self.tree) is not ast.Program:
            raise CodeGenError(self.tree)
        if type(self.tree.command) is not ast.LetCommand:
            raise CodeGenError(self.tree.command, ast.LetCommand)

        self.gen_command(self.tree.command)

        if self.stackSize == 0 :
            self.code.append((LOAD_CONST, None))
            self.code.append((RETURN_VALUE, None))
        elif self.stackSize < 0 :
            raise EmptyStackError()
        else:
            self.code.append((RETURN_VALUE, None))

        pprint(self.code)

        code_obj = Code(self.code, [], [], False, False, False, 'gencode', '', 0, '')
        code = code_obj.to_code()
        func = FunctionType(code, globals(), 'gencode')
        return func


    def gen_command(self, tree):

        if type(tree) is ast.AssignCommand:
            self.gen_assign_command(tree)
        elif type(tree) is ast.CallCommand:
            self.gen_call_command(tree)
        elif type(tree) is ast.SequentialCommand:
            self.gen_seq_command(tree)
        elif type(tree) is ast.IfCommand:
            self.gen_if_command(tree)
        elif type(tree) is ast.WhileCommand:
            self.gen_while_command(tree)
        elif type(tree) is ast.LetCommand:
            self.gen_let_command(tree)
        else:
            raise CodeGenError(tree)


    def gen_expression(self, tree):
        if type(tree) is ast.IntegerExpression:
            self.code.append((LOAD_CONST, tree.value))
            self.stackSize = self.stackSize + 1
            return tree.value

        elif type(tree) is ast.VnameExpression:
            varname = self.level_varname(tree.variable.identifier)
            # self.lookup_env(tree.variable.identifier)[tree.variable.identifier][0]

            if self.var_info(tree.variable.identifier)[2] :
                self.code.append((LOAD_FAST, varname))
                self.stackSize = self.stackSize + 1
            else:
                raise NoAssignmentError(tree.variable.identifier,self.level)

        elif type(tree) is ast.UnaryExpression:
            self.gen_expression(tree.expression)

            if tree.operator == '-':
                self.code.append((UNARY_NEGATIVE, None))
            elif tree.operator == '+':
                self.code.append((UNARY_POSITIVE, None))
            else:
                raise CodeGenError(tree)

        elif type(tree) is ast.BinaryExpression:
            self.gen_expression(tree.expr1)
            self.gen_expression(tree.expr2)

            op = tree.oper
            if op == '+' :
                self.code.append((BINARY_ADD,None))
            elif op == '-':
                self.code.append((BINARY_SUBTRACT,None))
            elif op == '*':
                self.code.append((BINARY_MULTIPLY,None))
            elif op == '/':
                self.code.append((BINARY_DIVIDE,None))
            elif op == '\\':
                self.code.append((BINARY_MODULO,None))
            elif op == '>':
                self.code.append((COMPARE_OP, '>'))
            elif op == '<':
                self.code.append((COMPARE_OP, '<'))
            elif op == '=':
                self.code.append((COMPARE_OP, '=='))
            else:
                raise CodeGenError(tree)
            self.stackSize = self.stackSize - 1
        else:
            raise CodeGenError(tree)


    def gen_declaration(self, tree):

        if type(tree) is ast.VarDeclaration:
            if tree.identifier in self.env[self.level]:
                raise RepeatDeclarationError(tree.identifier,self.level)
            self.add_env(tree.identifier,tree.type_denoter.identifier)
        elif type(tree) is ast.ConstDeclaration:
            self.add_env(tree.identifier,'const')
            self.gen_expression(tree.expression)
            self.code.append((STORE_FAST,self.level_varname(tree.identifier)))
            self.stackSize = self.stackSize - 1
            self.var_info(tree.identifier)[2] = True
        elif type(tree) is ast.SequentialDeclaration:
            self.gen_declaration(tree.decl1)
            self.gen_declaration(tree.decl2)
        else:
            raise CodeGenError(tree)

    def gen_assign_command(self, tree):
        self.gen_expression(tree.expression)
        varname = self.level_varname(tree.variable.identifier)
        if self.vartype(tree.variable.identifier) == 'const':
            raise UnChangableError(varname,self.level)
        self.code.append((STORE_FAST, varname))
        self.var_info(tree.variable.identifier)[2] = True
        self.stackSize = self.stackSize - 1

    def gen_call_command(self, tree):
        func = tree.identifier

        if func == 'putint':
            self.gen_expression(tree.expression)
            self.code.append((PRINT_ITEM, None))
            self.stackSize = self.stackSize - 1



        elif func == 'getint' and type(tree.expression) is ast.VnameExpression:
            name = tree.expression.variable.identifier
            varname = self.level_varname(name)

            self.code.append((LOAD_GLOBAL,'input'))
            self.code.append((CALL_FUNCTION, 0))
            self.stackSize = self.stackSize + 1

            if self.vartype(name) == 'const':
                raise UnChangableError(name,self.level)
            self.code.append((STORE_FAST, varname))
            self.var_info(name)[2] = True
            self.stackSize = self.stackSize - 1
        else:
            raise CodeGenError(tree)

    def gen_seq_command(self, tree):
        self.gen_command(tree.command1)
        self.gen_command(tree.command2)

    def gen_if_command(self, tree):
        expr = tree.expression
        cmd1 = tree.command1
        cmd2 = tree.command2

        label_else = Label()
        label_end = Label()

        self.gen_expression(expr)
        self.code.append((POP_JUMP_IF_FALSE, label_else))
        self.stackSize = self.stackSize - 1
        self.gen_command(cmd1)
        self.code.append((JUMP_FORWARD, label_end))
        self.code.append((label_else, None))
        self.gen_command(cmd2)
        self.code.append((label_end, None))

    def gen_while_command(self, tree):
        expr = tree.expression
        cmd  = tree.command

        label_loop = Label()
        label_condition = Label()
        label_end = Label()
        self.code.append((SETUP_LOOP, label_loop))
        self.code.append((label_condition, None))
        self.gen_expression(expr)
        self.code.append(((POP_JUMP_IF_FALSE, label_end)))
        self.stackSize = self.stackSize - 1
        self.gen_command(cmd)
        self.code.append((JUMP_ABSOLUTE, label_condition))
        self.code.append((label_end, None))
        self.code.append((POP_BLOCK, None))
        self.code.append((label_loop, None))

    def gen_let_command(self, tree):
        self.env.append({})
        self.level = self.level + 1

        self.gen_declaration(tree.declaration)
        self.gen_command(tree.command)

        self.env.pop()
        self.level = self.level - 1

def write_pyc_file(code, name):
    pyc_file = str(name[0:-3]) + '.pyc'
    print pyc_file
    with open(pyc_file,'wb') as pyc_f:
        magic = 0x03f30d0a
        pyc_f.write(struct.pack(">L",magic))
        pyc_f.write(struct.pack(">L",time.time()))
        marshal.dump(code.func_code, pyc_f)

if __name__ == '__main__':

    args = sys.argv[1:]
    fname = args

    f = file(fname[0],'r')
    proglist = f.readlines()
    f.close()
    prog = ''.join(proglist)

    scanner_obj = scanner.Scanner(prog)

    try:
        tokens = scanner_obj.scan()
    except scanner.ScannerError as e:
        print e

    parser_obj = parser.Parser(tokens)

    try:
        tree = parser_obj.parse()
    except parser.ParserError as e:
        print e
        print 'Not Parsed!'

    cg = CodeGen(tree)
    try:
        code = cg.generate()

        write_pyc_file(code, fname[0])
    except CodeGenError as e:
        print e
    except NoAssignmentError as e:
        print e
    except EmptyStackError as e:
        print e
    except UnChangableError as e:
        print e


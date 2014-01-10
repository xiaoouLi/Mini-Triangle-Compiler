#!/usr/bin/env python
#
# Scanner for a calculator interpreter

import scanner as scanner
import ast as ast


class ParserError(Exception):
    """ Parser error exception.

        pos: position in the input token stream where the error occurred.
        type: bad token type
        """

    def __init__(self, pos, type):
        self.pos = pos
        self.type = type

    def __str__(self):
        return '(Found bad token %s at %d)' % (scanner.TOKENS[self.type], self.pos)


class Parser(object):
    """Implement a parser for the following grammar:

        Program ::=  single-Command

        Command ::=  (single-Command';')*

        single-Command ::=  V-name ':=' Expression ';'
        |   Identifier '(' Expression ')' ';'
        |   if Expression then single-Command
        else single-Command
        |   while Expression do single-Command
        |   let Declaration in single-Command
        |   begin Command end
        |   return expression ';'

        Expression ::=  primary-Expression (Operator primary-Expression)*

        primary-Expression ::=  Integer-Literal
        |   V-name
        |   Operator primary-Expression
        |   '(' Expression ')'
        |   Identifier ( * empty | '(' expression ')')

        V-name ::=  Identifier

        Declaration ::=  (single-Declaration';')*

        single-Declaration ::=  const Identifier ~ Expression
        |   var Identifier : Type-denoter

        Type-denoter ::=  Identifier

        """

    def __init__(self, tokens):
        self.tokens = tokens
        self.curindex = 0
        self.curtoken = tokens[0]
        self.returnflag = 0

    def parse(self):
        e1 = self.parse_program()

        return e1

    def parse_program(self):
        """ Program ::=  single-Command EOT """
        e1 = self.parse_singlecommand()
        self.token_accept(scanner.TK_EOT)

        return ast.Program(e1)

    def parse_sequentialcommand(self):
        """Command ::= (single-Command)+"""
        e1 = self.parse_singlecommand()
        token = self.token_current()
        while token.type in [scanner.TK_IDENTIFIER,scanner.TK_IF,scanner.TK_WHILE,scanner.TK_LET,scanner.TK_BEGIN,scanner.TK_RETURN]:

            e2 = self.parse_singlecommand()
            e1 = ast.SequentialCommand(e1, e2)
            token = self.token_current()
        return e1

    def parse_singlecommand(self):
        """ single-Command  ::=  V-name ':=' Expression ';'
            |   Identifier '(' Expression ')' ';'
            |   if Expression then single-Command
            else single-Command
            |   while Expression do single-Command
            |   let Declaration in single-Command
            |   begin Command end
            |   return expression ';' """

        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            lookahead_token = self.lookahead()
            if lookahead_token.type == scanner.TK_BECOMES:
                e1 = self.parse_assigncommand()

            elif lookahead_token.type == scanner.TK_LPAREN:
                e1 = self.parse_callcommand()
            else:
                self.token_accept_any()
                raise ParserError(self.curtoken.pos, self.curtoken.type)
        elif token.type == scanner.TK_IF:
            e1 = self.parse_ifcommand()
        elif token.type == scanner.TK_WHILE:
            e1 = self.parse_whilecommand()
        elif token.type == scanner.TK_LET:
            e1 = self.parse_letcommand()
        elif token.type == scanner.TK_BEGIN:
            self.token_accept(scanner.TK_BEGIN)
            e1 = self.parse_sequentialcommand()
            self.token_accept(scanner.TK_END)
        elif token.type == scanner.TK_RETURN:
            e1 = self.parse_returncommand()
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return e1

    def parse_assigncommand(self):
        """single-com -> vname := expression ';'"""
        e1 = self.parse_vname()
        self.token_accept(scanner.TK_BECOMES)
        e2 = self.parse_binaryexpr()
        self.token_accept(scanner.TK_SEMICOLON)

        return ast.AssignCommand(e1, e2)


    def parse_argumentexpression(self):
        """ ArgumentExpression -> BinaryExpression """
        e1 = self.parse_binaryexpr()

        return e1

    def parse_sequentialargumentexpression(self):
        """ SequentialArgumentExpression -> ArgumentExpression ( ',' ArgumentExpression )*"""

        e1 = self.parse_argumentexpression()
        token = self.curtoken

        while token.type == scanner.TK_COMMA:
            self.token_accept(scanner.TK_COMMA)
            e2 = self.parse_argumentexpression()
            e1 = ast.SequentialArgumentExpression(e1,e2)
            token = self.curtoken

        return e1

    def parse_callcommand(self):
        """single-com -> identifier (expr) ';' """
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            self.token_accept(scanner.TK_LPAREN)
            if self.curtoken.type is not scanner.TK_RPAREN:
                e1 = self.parse_sequentialargumentexpression()
                self.token_accept(scanner.TK_RPAREN)
                self.token_accept(scanner.TK_SEMICOLON)
                return ast.ArgumentCallCommand(token.val, e1)
            else:
                self.token_accept(scanner.TK_RPAREN)
                self.token_accept(scanner.TK_SEMICOLON)
                return ast.CallCommand(token.val)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)


    def parse_ifcommand(self):
        """ single-com -> if expr then single-command else single-command"""
        self.token_accept(scanner.TK_IF)
        e1 = self.parse_binaryexpr()
        self.token_accept(scanner.TK_THEN)
        e2 = self.parse_singlecommand()
        self.token_accept(scanner.TK_ELSE)
        e3 = self.parse_singlecommand()

        return ast.IfCommand(e1, e2, e3)

    def parse_whilecommand(self):
        """ single-com -> while expr do single-c """
        self.token_accept(scanner.TK_WHILE)
        e1 = self.parse_binaryexpr()
        self.token_accept(scanner.TK_DO)
        e2 = self.parse_singlecommand()

        return ast.WhileCommand(e1, e2)

    def parse_letcommand(self):
        """ single-com -> let declaration in single-c """
        self.token_accept(scanner.TK_LET)
        e1 = self.parse_sequentialdeclaration()
        self.token_accept(scanner.TK_IN)
        e2 = self.parse_singlecommand()

        return ast.LetCommand(e1, e2)

    def parse_returncommand(self):
        """ single-com -> return expression ';' """
        self.returnflag = 1
        self.token_accept(scanner.TK_RETURN)
        e1 = self.parse_binaryexpr()
        self.token_accept(scanner.TK_SEMICOLON)
        return ast.ReturnCommand(e1)


    def parse_integerexpr(self):
        """ priexpr -> integer-literal """
        token = self.curtoken
        if token.type == scanner.TK_INTLITERAL:
            self.token_accept_any()
            return ast.IntegerExpression(token.val)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

    def parse_vnameexpr(self):
        """ priexpr -> v-name """
        e1 = self.parse_vname()

        return ast.VnameExpression(e1)



    def parse_unaryexpr(self):
        """ expression -> Operator primary-expression """
        token = self.curtoken
        if token.type == scanner.TK_OPERATOR and token.val in ['+','-']:
            self.token_accept_any()
            e1 = self.parse_priexpr()
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return ast.UnaryExpression(token.val, e1)

    def parse_binaryexpr(self):
        """ Expression -> calculation-expr ( operator calculation-expr )* """
        e1 = self.parse_calculationexpr()
        token = self.curtoken
        if token.type == scanner.TK_OPERATOR and token.val in ['>','<','=']:
            oper = token.val
            self.token_accept_any()
            e2 = self.parse_calculationexpr()
            token = self.token_current()
            e1 = ast.BinaryExpression(e1, oper, e2)

        return e1

    def parse_calculationexpr(self):
        """ calculationExpression -> sec-expression ( operator sec-expression )* """

        e1 = self.parse_secexpr()
        token = self.curtoken
        while token.type == scanner.TK_OPERATOR and token.val in ['+','-']:
            oper = token.val
            self.token_accept_any()
            e2 = self.parse_secexpr()
            token = self.token_current()
            e1 = ast.BinaryExpression(e1, oper, e2)

        return e1

    def parse_secexpr(self):
        """secexpr -> primary-expression ( operator primary-expression )*"""

        e1 = self.parse_priexpr()
        token = self.curtoken
        while token.type == scanner.TK_OPERATOR and token.val in ['*','/','\\']:
            oper = token.val
            self.token_accept_any()
            e2 = self.parse_priexpr()
            token = self.token_current()
            e1 = ast.BinaryExpression(e1, oper, e2)

        return e1

    def parse_priexpr(self):
        """ priexpr -> Integer-Literal
        |   V-name
        |   Operator primary-Expression
        |   '(' Expression ')'
        |   Identifier ( '(' * empty | ( V-name ( ',' V-name )* ) ')') """

        token = self.curtoken
        if token.type == scanner.TK_INTLITERAL:
            e1 = self.parse_integerexpr()
        elif token.type == scanner.TK_IDENTIFIER:
            if self.lookahead().type == scanner.TK_LPAREN:
                self.token_accept_any()
                self.token_accept(scanner.TK_LPAREN)
                if self.curtoken.type is not scanner.TK_RPAREN:
                    e1 = self.parse_sequentialargumentexpression()
                    self.token_accept(scanner.TK_RPAREN)
                    return ast.ArgumentFunctionExpression(token.val, e1)
                else:
                    self.token_accept(scanner.TK_RPAREN)
                    return ast.FunctionExpression(token.val)
            else:
                e1 = self.parse_vnameexpr()
        elif token.type == scanner.TK_OPERATOR:
            e1 = self.parse_unaryexpr()
        elif token.type == scanner.TK_LPAREN:
            self.token_accept(scanner.TK_LPAREN)
            e1 = self.parse_binaryexpr()
            self.token_accept(scanner.TK_RPAREN)
        elif token.type == scanner.TK_STRING:
            e1 = self.parse_string()

        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return e1


    def parse_singleparameter(self):
        """ SingleParameter ->  V-name ':' Type-denoter """
        e1 = self.parse_vname()
        self.token_accept(scanner.TK_COLON)
        e2 = self.parse_typedenoter()
        return ast.SingleParameter(e1,e2)

    def parse_sequetialparameter(self):
        """ SequetialParameter ->  SingleParameter ( ',' SingleParameter )* """
        e1 = self.parse_singleparameter()
        token = self.curtoken
        while token.type == scanner.TK_COMMA:
            self.token_accept_any()
            e2 = self.parse_singleparameter()
            e1 = ast.SequetialParameter(e1,e2)
            token = self.curtoken
        return e1

    def parse_string(self):
        token = self.curtoken
        self.token_accept_any()
        return ast.String(token.val)


    def parse_vname(self):
        """ v-name -> identifier """
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()

            return ast.Vname(token.val)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

    def parse_constdeclaration(self):
        """ single-declaration -> const identifier ~ expr """
        self.token_accept(scanner.TK_CONST)
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            self.token_accept(scanner.TK_IS)
            e1 = self.parse_binaryexpr()
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return ast.ConstDeclaration(token.val, e1)

    def parse_vardeclaration(self):
        """ single-declaration -> var identifier : type-denoter"""
        self.token_accept(scanner.TK_VAR)
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            self.token_accept(scanner.TK_COLON)
            e1 = self.parse_typedenoter()

        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return ast.VarDeclaration(token.val, e1)

    def parse_parameterfunctiondeclaration(self):
        """ funcdeclaration -> func Identifier  '(' [Parameter] ')' ':' Type-denoter single-Command """
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            self.token_accept(scanner.TK_LPAREN)
            e1 = self.parse_sequetialparameter()
            self.token_accept(scanner.TK_RPAREN)
            self.token_accept(scanner.TK_COLON)
            e2 = self.parse_typedenoter()
            e3 = self.parse_singlecommand()
        else:
            print "func"
            raise ParserError(self.curtoken.pos, self.curtoken.type)
        return ast.ParameterFunctionDeclaration(token.val,e1,e2,e3)

    def parse_functiondeclaration(self):
        """ funcdeclaration -> func Identifier  '(' ')' ':' Type-denoter single-Command """
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            self.token_accept(scanner.TK_LPAREN)
            self.token_accept(scanner.TK_RPAREN)
            self.token_accept(scanner.TK_COLON)
            e1 = self.parse_typedenoter()
            # self.returnflag = 1
            e2 = self.parse_singlecommand()
            # self.returnflag = 0
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)
        return ast.FunctionDeclaration(token.val,e1,e2)


    def parse_sequentialdeclaration(self):
        """ declaration -> (single-declaration)+ """
        e1 = self.parse_singledeclaration()
        token = self.curtoken
        while token.type in [scanner.TK_CONST,scanner.TK_VAR,scanner.TK_FUNCDEF]:
            e2 = self.parse_singledeclaration()
            e1 = ast.SequentialDeclaration(e1, e2)
            token = self.curtoken

        return e1

    def parse_singledeclaration(self):
        """ single-d -> const id ~ expr | var id : type-denoter """
        token = self.curtoken
        if token.type == scanner.TK_CONST:
            e1 = self.parse_constdeclaration()
            self.token_accept(scanner.TK_SEMICOLON)
        elif token.type == scanner.TK_VAR:
            e1 = self.parse_vardeclaration()
            self.token_accept(scanner.TK_SEMICOLON)
        elif token.type == scanner.TK_FUNCDEF:
            self.token_accept(scanner.TK_FUNCDEF)
            if self.tokens[self.curindex+2].type == scanner.TK_RPAREN:
                e1 = self.parse_functiondeclaration()
            elif self.tokens[self.curindex+2].type == scanner.TK_IDENTIFIER:
                e1 = self.parse_parameterfunctiondeclaration()
            else:
                print "wrong function declaration! "
                exit()
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

        return e1

    def parse_typedenoter(self):
        """ type-denoter -> identifier """
        token = self.curtoken
        if token.type == scanner.TK_IDENTIFIER:
            self.token_accept_any()
            return ast.TypeDenoter(token.val)
        else:
            raise ParserError(self.curtoken.pos, self.curtoken.type)

    def token_current(self):
        return self.curtoken

    def token_accept_any(self):
        if self.curtoken.type != scanner.TK_EOT:
            self.curindex += 1
            self.curtoken = self.tokens[self.curindex]

    def token_accept(self, type):
        if self.curtoken.type != type:
            print "asked token: %s" %type
            raise ParserError(self.curtoken.pos, self.curtoken.type)
        self.token_accept_any()

    def lookahead(self):
        if self.curtoken.type != scanner.TK_EOT:
            return self.tokens[self.curindex+1]


if __name__ == '__main__':
    #pass
    s1 = """! Factorial
                 let var x: Integer;
                 var fact: Integer;
                 in
                 begin
                 getint(x);
                 fact := 2*(3+>4)*5;
               !  while x > 0 do
                ! begin
                 !fact := fact * x;
                 !x := x - 1
                ! end;
                 putint(fact);
                 end"""

    s2= """let var x:Integer;
    !var uy:Integer;
func foo (): Integer if x=2 then begin x:=2;return x+y>y*y; end else x:=3;
            in
            begin
               ! while x +1= 0 do
                ! begin
                 fact := "7';x :=+1- 0 ;
                 foo(s,s,s);
!end
                 end
                 """

    prog= """let var x:Integer;
    !var uy:Integer;
func foo (): Integer return 2; !end else x:=3;
            in
            begin
               ! while x +1= 0 do
                ! begin
                 !fact := x =+1- 0 ;
                 foo();
!end
                 end
                 """
    s = """
            let
                func foo(x:Integer,y:Integer):Integer let var y:Integer; in if 1>0 then begin x:= 6;putint(x);end  else putint(2);
            in
                foo(20);
           """



    scanner_obj = scanner.Scanner(s)
    tokens = scanner_obj.scan()
    parser_obj = Parser(tokens)
    print tokens

    tree = parser_obj.parse()
    print tree








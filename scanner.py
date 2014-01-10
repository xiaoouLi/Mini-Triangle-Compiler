#!/usr/bin/env python
#
# Scanner for a calculator interpreter

import cStringIO as StringIO
import string

# Token Constants

TK_EOT = 0
TK_INT = 1
TK_LPAREN = 2
TK_RPAREN = 3
TK_OPER   = 4
TK_SEMICOLON = 5
TK_EQUALS = 6
TK_IDENT = 7

TOKENS = {TK_EOT: 'EOT',
          TK_INT: 'INT',
          TK_LPAREN: 'LPAREN',
          TK_RPAREN: 'RPAREN',
          TK_OPER: 'OPER',
          TK_SEMICOLON: 'SEMICOLON',
          TK_EQUALS: 'EQUALS',
          TK_IDENT: 'IDENT'}

OPERATORS = ['+', '-', '*', '/']

class Token(object):
    """ A simple Token structure.
        
        Contains the token type, value and position. 
    """
    def __init__(self, type, val, pos):
        self.type = type
        self.val = val
        self.pos = pos

    def __str__(self):
        return '(%s(%s) at %s)' % (TOKENS[self.type], self.val, self.pos)

    def __repr__(self):
        return self.__str__()


class ScannerError(Exception):
    """ Scanner error exception.

        pos: position in the input text where the error occurred.
    """
    def __init__(self, pos, char):
        self.pos = pos
        self.char = char

    def __str__(self):
        return 'ScannerError at pos = %d, char = %s' % (self.pos, self.char)

class Scanner(object):
    """Implement a scanner for the following token grammar
    
       Token     :== EOT | EOL | Int | '(' | ')' | '=' | Ident | Op
       Int       :== Digit (Digit)*
       Ident     :== Letter (Letter | Digit)*
       Op        :== '+' | '-' | '*' | '/' 
       Digit     :== [0..9]

       Separator :== ' ' | '\t' | '\n'        
    """

    def __init__(self, input):
        # Use StringIO to treat input string like a file.
        self.inputstr = StringIO.StringIO(input)
        self.eot = False   # Are we at the end of the input text?
        self.pos = 0       # Position in the input text
        self.char = ''     # The current character from the input text
        self.char_take()   # Fill self.char with the first character

    def scan(self):
        """Main entry point to scanner object.

        Return a list of Tokens.
        """

        self.tokens = []
        while 1:
            token = self.scan_token()
            self.tokens.append(token)
            if token.type == TK_EOT:
                break
        return self.tokens
    
    def scan_token(self):
        """Scan a single token from input text."""

        c = self.char_current()
        token = None
        
        while not self.char_eot():
            if c.isspace():
                self.char_take()
                c = self.char_current() 
                continue
            elif c == '!':
                self.char_take()
                while self.char_current() != '\n' and not self.char_eot():
                    self.char_take()
                self.char_take()
                c = self.char_current()
                continue
            elif c.isdigit():
                token = self.scan_int()
                break
            elif c.isalpha():
                token = self.scan_ident()
                break
            elif c in OPERATORS:
                token = self.scan_operator()
                break
            elif c == '(':
                token = Token(TK_LPAREN, 0, self.char_pos())
                self.char_take()
                break
            elif c == ')':
                token = Token(TK_RPAREN, 0, self.char_pos())
                self.char_take()
                break
            elif c == ';':
                token = Token(TK_SEMICOLON, 0, self.char_pos())
                self.char_take()
                break
            elif c == '=':
                token = Token(TK_EQUALS, 0, self.char_pos())
                self.char_take()
                break
            else:
                raise ScannerError(self.char_pos(), self.char_current())
      
        if token is not None:
            return token
           
        if self.char_eot():
            return(Token(TK_EOT, 0, self.char_pos()))

         
    def scan_int(self):
        """Int :== Digit (Digit*)"""
        
        pos = self.char_pos()
        numlist = [self.char_take()]

        while self.char_current().isdigit():
            numlist.append(self.char_take())
        
        return Token(TK_INT, int(string.join(numlist ,'')), pos)

    def scan_ident(self):
        """Ident :== Letter (Letter | Digit)*"""
        
        pos = self.char_pos()
        charlist = [self.char_take()]

        while self.char_current().isalnum():
            charlist.append(self.char_take())
        
        return Token(TK_IDENT, string.join(charlist ,''), pos)

    def scan_operator(self):
        """Op :== '+' | '-' | '*' | '/'"""

        pos = self.char_pos()
        op_value = self.char_take()
        return Token(TK_OPER, op_value, pos)

    def char_current(self):
        """Return in the current input character."""

        return self.char

    def char_take(self):
        """Consume the current character and read the next character 
        from the input text.

        Update self.char, self.eot, and self.pos
        """

        char_prev = self.char
        
        self.char = self.inputstr.read(1)
        if self.char == '':
            self.eot = True

        self.pos += 1
        
        return char_prev
        
    def char_pos(self):
        """Return the position of the *current* character in the input text."""

        return self.pos - 1
        
    def char_eot(self):
        """Determine if we are at the end of the input text."""

        return self.eot
        

if __name__ == '__main__':
    exprs = ['1',
             '723',
             '1 + 1',
             '3 - 2',
             '9 * 10',
             '(1)',
             '1 + 2 * (3 + 4)',
             '(1   +   2)   *   (   (3 * 10) / 5)',
             '1 + &',
             """! Hi Mom!
                (1
                +2 ! Hi Dad...
                ) ! Last Comment""",
             'a = 1 + c + d']

    for exp in exprs:
        print '=============='
        print exp
        scanner = Scanner(exp)
        try:
            tokens = scanner.scan()
            print tokens
        except ScannerError as e:
            print e



from operator import le
from threading import currentThread
import re
import sys

path_text = str()
if __name__ == "__main__":
    if len(sys.argv) > 1:
       path_text = sys.argv[1]
    else:
       path_text = "text.txt"
else:
    path_text = "text.txt"
lex_output = list()
dictionary = [';', '=','(',')','{','}','if','else','while','+','-','*','/','>','<','==','&&','||','!','~']
reg_ident = r'([a-zA-Z_]{1}[0-9a-zA-Z_]*$)'
reg_const = r'([1-9]{1}[0-9]*$)|([0]{1}$)' # 
reg_space = r'([ \n\t]+$)'
reg_all = reg_ident + r'|' + reg_const + r'|' + reg_space
reg_operators = r'([+\-*/><!=]{1}$)|([&]{2}$)|([=]{2}$)|([\|]{2}$)'
reg_operators2 = r'([+\-*/><!]{1}$)|([&]{2}$)|([=]{2}$)|([\|]{2}$)' # without =
def priority_operator(operat):
        if re.match(r'[()]{1}$',operat): 
            return 8
        elif re.match(r'[*/]{1}$',operat):  
            return 7
        elif re.match(r'[+\-]{1}$',operat):
            return 6
        elif operat == '!':
            return 5
        elif re.match(r'[><]{1}$',operat): 
            return 4
        elif operat == "==":
            return 3
        elif operat == "&&" or operat == "||":
            return 2
        elif operat == "=":
            return 1
        else:
            return 0

def lex_analyser(path_text):
    global lex_output
    f = open(path_text,'r')
    current_lexem = ""
    end_of_file = False
    #lexer
    # eof added
    while 1:
        new_symbol = f.read(1)
        if not new_symbol: # конец файла
            end_of_file = True
        if new_symbol == "\n": # костыль во избежания ошибок с re.match \n меняю на пробел
            new_symbol = " "
        if (current_lexem + new_symbol in dictionary or re.match(reg_all, current_lexem + new_symbol)) and not end_of_file: # может ли лексема быть продолжена?
            current_lexem += new_symbol
        else: # лексема закончилась
            if current_lexem in dictionary:           # найдено ключевое слово
                lex_output.append({ "code" : current_lexem})
            elif re.match(reg_ident, current_lexem):  # найден идентификатор
                lex_output.append({ "code" : "ident", "name" : current_lexem})
            elif re.match(reg_const, current_lexem):  # найдена константа 
                lex_output.append({ "code" : "const", "value" : current_lexem})
            elif re.match(reg_space, current_lexem):  # найден пробел
                pass        
            else:                                     # иначе ошибка и выход
                print('lexic error!')
                return False
                break        
            if end_of_file:                       # успешно считали весь файл
                lex_output.append({"code":"eof"})
                for i in lex_output:
                    if i["code"] == "ident":
                        print(i["name"],end=' ')
                    elif i["code"] == "const":
                        print(i["value"],end=' ')
                    else:
                        print(i["code"],end=' ')
                print("\n LEXIC SUCCESS!!")
                return True
                break
            current_lexem = new_symbol
            continue        
#'''

lex_analyser(path_text)

#syntax
# ifwhile ( ) -> ifwhile # #
# let
# unar to binary substitution:  (- 1)  to (0 - 1)
# unar operation { } substitution
# jmp, jz, label
# let ident has now new field - pointer set on 1 
synt_input = lex_output
synt_output = list()

stack_postfix = list()
queue_postfix = list()

# REVERSE POLISH NOTATION processing
# https://habr.com/ru/post/489744/    took here
# assuming syntax is correct
def postfix(current_lexem):
    if current_lexem["code"]=="const" or  current_lexem["code"]=="ident":
        queue_postfix.append(current_lexem)
    elif re.match(reg_operators,current_lexem["code"]):
        while len(stack_postfix)>0:
            if stack_postfix[-1]["code"] == "(":
                break
            elif priority_operator(current_lexem["code"]) > priority_operator(stack_postfix[-1]["code"]):
                break
            else:
                queue_postfix.append(stack_postfix.pop())
                continue
        stack_postfix.append(current_lexem)
    elif current_lexem["code"]=="(":
        stack_postfix.append(current_lexem)
    elif current_lexem["code"]==")":
        while not stack_postfix[-1]["code"] == "(":
            queue_postfix.append(stack_postfix.pop())
        stack_postfix.pop()
def complete_postfix():
    while not len(stack_postfix) == 0:
        queue_postfix.append(stack_postfix.pop())


# mode:
#   root - main body (eof allowed)
#   0    - internal body (doesn't require operator '}' allowed )
#   1    - internal body (require only 1 operator for once)
#   2    - internal body (requre 1+ operator and comes to mode 0)
#
#   -----------|-----------------------------|---------
#   root 2 1 0 | id    = B ;                 |root:root
#        not3  |                             |0:0
#              | if    ( B ) { 2 }        3  |1:ret
#              |             not{ unpop 1 3  |2:0
#              |                             |
#              | while ( B ) { 2 }           |
#              |             not{ unpop 1    |
#   -----------|-----------------------------|---------
#            3 | else  { 2 } ret             |
#              |       not{ unpop 1 ret      |
#              | notelse unpop ret           |
#   -----------|-----------------------------|---------
#         root | eof                         |ret
#   -----------|-----------------------------|---------
#            0 | }                           |unpop ret
#   -----------|-----------------------------|---------                       
#              
#
# label section:
# 
#     if             
#     ...
#    {, {"jz":?} -> buff1
#     ...
#   }, {"jmp":?} -> buff2   carry_else=buff2, {"label":++label_count}-> buff1["jz"] 
#      ...
#   buff2=carry_else          not else                |        else
#                       synt_output.remove(buff2)     |     {"label":++label_count} -> buff2["jmp"], }
#
#
#   while
#   ...
#   {"label",++label_count} -> buff2
#   ...
#   {, {"jz":?} -> buff1
#   ...
#   {"jmp", buff2}, {"label",++label_count} -> buff1["jz"], }
#   
#
carry_else = dict() # remember buff2 in else recursion
label_count = 1 # global label counter
def A_nonterminal(mode):
    global synt_input
    global synt_output
    global carry_else
    global label_count
    current_lexem = synt_input.pop(0) 
    if current_lexem["code"] == "ident" and not mode == 3:
       current_lexem["pointer"] = 1               # pointer field in 1
       synt_output.append({"code":"let"}) 
       synt_output.append(current_lexem)
       current_lexem = synt_input.pop(0) 
       if current_lexem["code"] == "=":
           synt_output.append(current_lexem)
           if B_nonterminal(0) == True:
               current_lexem = synt_input.pop(0) 
               if current_lexem["code"] == ";":
                    synt_output.append(current_lexem)
                    if mode == "root":
                        if A_nonterminal("root") == True:
                            return True
                    elif mode == 2 or mode == 0:
                        if A_nonterminal(0) == True:
                            return True 
                    elif mode == 1:
                        return True

    elif current_lexem["code"] == "while" and not mode == 3:
        synt_output.append(current_lexem)
        synt_output.append({"code":"label","value":label_count})        #l
        buff2 = synt_output[-1]                                         #l
        label_count += 1                                                #l
        current_lexem = synt_input.pop(0)
        if current_lexem["code"] == "(":
            synt_output.append({"code":"#"})  
            if B_nonterminal(0) == True:
                current_lexem = synt_input.pop(0)
                if current_lexem["code"] == ")":
                    synt_output.append({"code":"#"})
                    current_lexem = synt_input.pop(0)
                    if current_lexem["code"] == "{":
                        synt_output.append(current_lexem)
                        synt_output.append({"code":"jz","value":0})        #l
                        buff1 = synt_output[-1]                            #l
                        if  A_nonterminal(2)==True:
                            current_lexem = synt_input.pop(0)
                            if current_lexem["code"] == "}":
                                synt_output.append({"code":"jmp","value":buff2})                #l
                                synt_output.append({"code":"label","value":label_count})        #l
                                buff1["value"] = synt_output[-1]                                #l
                                label_count += 1                                                #l
                                synt_output.append(current_lexem)
                                if mode == "root":
                                    if A_nonterminal("root") == True:
                                        return True
                                elif mode == 2 or mode == 0:
                                    if A_nonterminal(0) == True:
                                        return True 
                                elif mode == 1:
                                    return True
                    else:
                        synt_input = [current_lexem] + synt_input 
                        synt_output.append({"code":"{"})   # unar operation { } substitution
                        synt_output.append({"code":"jz","value":0})                               #l
                        buff1 = synt_output[-1]                                                   #l
                        if A_nonterminal(1)==True:
                            synt_output.append({"code":"jmp","value":buff2})                #l
                            synt_output.append({"code":"label","value":label_count})        #l
                            buff1["value"] = synt_output[-1]                                #l
                            label_count += 1                                                #l
                            synt_output.append({"code":"}"})
                            if mode == "root":
                                if A_nonterminal("root") == True:
                                    return True
                            elif mode == 2 or mode == 0:
                                if A_nonterminal(0) == True:
                                    return True 
                            elif mode == 1:
                                return True
    elif current_lexem["code"] == "if" and not mode == 3:
        synt_output.append(current_lexem)  
        current_lexem = synt_input.pop(0)
        if current_lexem["code"] == "(":
            synt_output.append({"code":"#"})  
            if B_nonterminal(0) == True:
                current_lexem = synt_input.pop(0)
                if current_lexem["code"] == ")":
                    synt_output.append({"code":"#"})
                    current_lexem = synt_input.pop(0)
                    if current_lexem["code"] == "{":                                                
                        synt_output.append(current_lexem)
                        synt_output.append({"code":"jz","value":0})                     #l
                        buff1 = synt_output[-1]                                         #l
                        if  A_nonterminal(2)==True:
                            current_lexem = synt_input.pop(0)
                            if current_lexem["code"] == "}":
                                synt_output.append({"code":"jmp","value":0})                    #l
                                buff2 = synt_output[-1]                                         #l
                                carry_else = buff2                                              #l 
                                synt_output.append({"code":"label","value":label_count})        #l
                                label_count +=1                                                 #l
                                buff1["value"]=synt_output[-1]                                  #l

                                synt_output.append(current_lexem)
                                if A_nonterminal(3) == True: # to else
                                    if mode == "root":
                                        if A_nonterminal("root") == True:
                                            return True
                                    elif mode == 2 or mode == 0:
                                        if A_nonterminal(0) == True:
                                            return True 
                                    elif mode == 1:
                                        return True
                    else:
                        synt_input = [current_lexem] + synt_input
                        synt_output.append({"code":"{"})   # unar operation { } substitution
                        synt_output.append({"code":"jz","value":0})                     #l
                        buff1 = synt_output[-1]                                         #l 
                        if A_nonterminal(1)==True:
                            synt_output.append({"code":"jmp","value":0})                    #l
                            buff2 = synt_output[-1]                                         #l
                            carry_else = buff2                                              #l 
                            synt_output.append({"code":"label","value":label_count})        #l
                            label_count +=1                                                 #l
                            buff1["value"]=synt_output[-1]                                  #l
                            synt_output.append({"code":"}"})
                            if A_nonterminal(3) == True: # to else
                                if mode == "root":
                                    if A_nonterminal("root") == True:
                                        return True
                                elif mode == 2 or mode == 0:
                                    if A_nonterminal(0) == True:
                                        return True 
                                elif mode == 1:
                                    return True
    elif mode == 3: # else section
        buff2 = carry_else 
        if current_lexem["code"] == "else":
            synt_output.append(current_lexem)
            current_lexem = synt_input.pop(0)
            if current_lexem["code"] == "{":
                synt_output.append(current_lexem)
                if A_nonterminal(2) == True:
                    current_lexem = synt_input.pop(0)
                    if current_lexem["code"] == "}":
                        synt_output.append({"code":"label","value":label_count})        #l
                        label_count +=1                                                 #l
                        buff2["value"] = synt_output[-1]                                #l

                        synt_output.append(current_lexem)
                        return True
            else:                           
               synt_input = [current_lexem] + synt_input
               synt_output.append({"code":"{"})   # unar operation { } substitution 
               if A_nonterminal(1) == True:
                   synt_output.append({"code":"label","value":label_count})        #l
                   label_count +=1                                                 #l
                   buff2["value"] = synt_output[-1]                                #l
                   synt_output.append({"code":"}"}) 
                   return True 
        else:
            synt_output.remove(buff2)                               #l            
            synt_input = [current_lexem] + synt_input
            return True
    elif current_lexem["code"] == "}" and mode == 0:                
        synt_input = [current_lexem] + synt_input
        return True
    elif current_lexem["code"] == "eof" and mode == "root":
        synt_output.append({"code":"eof"})
        return True
    return False
# mode:
#   0 - default
#   1 - after unar operator
#   2 - ready to return
#   3 - +(  is now possible
# X - operand   + - binar operator   - - unar operator
# unpop - retrieve element to pop him again in parent
# ret -  return True and come to parent
#
#  3 1 0| ( 0 )           | 2
#       |                 |
#    1 0| X               | 2
#       |                 |
#      0| -               | 1
#       |                 |
#      2| + X             | 2
#       | + notX unpop 3  |  
#      2| not+            | unpop ret
#
def B_nonterminal(mode):
    global synt_input
    global synt_output
    current_lexem = synt_input.pop(0)
    if current_lexem["code"] == "(" and (mode in [0,1,3]):
        synt_output.append(current_lexem)
        if B_nonterminal(0) == True:
            current_lexem = synt_input.pop(0)
            if current_lexem["code"] == ")":
                synt_output.append(current_lexem)
                if B_nonterminal(2) == True:
                    return True
    elif (current_lexem["code"] in ["const","ident"]) and (mode in [0,1]):
        synt_output.append(current_lexem)
        if B_nonterminal(2) == True:
            return True
    elif (current_lexem["code"] in ["!","-"]) and mode == 0:
        if current_lexem["code"] == "-":
            synt_output.append({"code":"const", "value":0}) #  unar minus to binar substitution
        synt_output.append(current_lexem)
        if B_nonterminal(1) == True:
            return True
    elif re.match(reg_operators2 ,current_lexem["code"]) and mode == 2:
        synt_output.append(current_lexem)
        current_lexem = synt_input.pop(0)
        if current_lexem["code"] in ["const","ident"]:
            synt_output.append(current_lexem)
            if B_nonterminal(2) == True:
                return True
        else:
            synt_input = [current_lexem] + synt_input
            if B_nonterminal(3) == True:
                return True
    elif mode == 2:
        synt_input = [current_lexem] + synt_input
        return True
    return False


synt2_input = list()
synt2_output = list()

def synt_analyser(): # postfix
    global synt_output
    global synt2_output
    global synt2_input
    global stack_postfix
    global queue_postfix
    if A_nonterminal("root") == True:
        synt2_input = synt_output

        current_lexem=synt2_input.pop(0)
        while not current_lexem["code"] == "eof":
            if current_lexem["code"] == "let":
                stack_postfix = []
                queue_postfix = []
                synt2_output.append(current_lexem)
                current_lexem=synt2_input.pop(0)
                while not current_lexem["code"]==";":
                    postfix(current_lexem)
                    current_lexem = synt2_input.pop(0)
                complete_postfix()
                synt2_output = synt2_output + queue_postfix
            elif current_lexem["code"] == "#":
                stack_postfix = []
                queue_postfix = []
                synt2_output.append(current_lexem)
                current_lexem=synt2_input.pop(0)
                while not current_lexem["code"]=="#":
                    postfix(current_lexem)
                    current_lexem = synt2_input.pop(0)
                complete_postfix()
                synt2_output = synt2_output + queue_postfix
            synt2_output.append(current_lexem)
            current_lexem = synt2_input.pop(0)
        synt2_output.append(current_lexem)

        print("\n\n\n")        
        for i in synt2_output:
                if i["code"] == "ident":
                    print(i["name"], end=' ')
                elif i["code"] == "const":
                    print(i["value"], end=' ')
                elif i["code"] == "label":
                    print(":"+str(i["value"]), end=' ')
                elif i["code"] == "jmp":
                    print(i["code"]+"_"+str(i["value"]["value"]), end=' ')
                elif i["code"] == "jz":
                    print(i["code"]+"_"+str(i["value"]["value"]), end=' ')
                else:
                    print(i["code"],end = ' ')
        print("\n SYNTAX SUCCESS! \n\n")
        return True
    else:
        print(" syntax error! \n\n")
        return False

################################### SEMANTICS ########################
#   1) obslast vidimosti (variable scope)
#   2) if while let #  ; { }  dissapear.  JZ, jmp and label added
#   
#   
#   variable scope layers depend on { }.
#   a) we work with only ident, {, }, let, #, ident   
#   d) {  - layer++
#   e) } - layer--  delete some from sem_dictionary
#   f) # idents checked if they are in sem_dictionary
#   b) let  remember first ident then repeat f step then if that ident is not in sem_dictionary then add him with value of layer


sem_input = list()
def sem_analyser1():
    global sem_input
    layer = 1
    sem_dictionary = dict()
    if synt_analyser()==True:
        sem_input = synt2_output.copy()
        current_lexem = sem_input.pop(0)        
        while not current_lexem["code"] == "eof":
            if current_lexem["code"] == "{":
                layer += 1
            elif current_lexem["code"] == "}":
                for i in list(sem_dictionary):
                    if sem_dictionary[i] == layer:
                        del(sem_dictionary[i])
                layer -= 1
            
            elif current_lexem["code"] == "#":
                current_lexem = sem_input.pop(0) 
                while not current_lexem["code"] == "#":
                    if current_lexem["code"] == "ident":
                        if not current_lexem["name"] in sem_dictionary:
                            print("semantic error: "+current_lexem["name"])
                            return False
                    current_lexem = sem_input.pop(0)
            elif current_lexem["code"] == "let":
                asgn = sem_input.pop(0)
                current_lexem = sem_input.pop(0)
                while not current_lexem["code"] == ";":
                    if current_lexem["code"] == "ident":
                        if not current_lexem["name"] in sem_dictionary:
                            print("semantic error: "+current_lexem["name"])
                            return False
                    current_lexem = sem_input.pop(0)
                if not asgn["name"] in sem_dictionary:
                    sem_dictionary[asgn["name"]] = layer
            current_lexem = sem_input.pop(0)

        #print("SEMANTIC SUCCESS!!")
        return True        
    else:
        #print("semantic error!!")
        return False

# getting rid of ; if while let else # { } 
# changing const, ident and *ident to pushc, pushv and push*
# = -> asgn
# pushv pushc push* jz jmp have field "opperand"  
# label is now without operands and just idle
# jz and jmp now refer to real address(I mean, index)
sem_output = list()
def sem_analyser2():
    global sem_output
    if sem_analyser1() == True:
        sem_output = synt2_output.copy()
        for i in list(sem_output):
            if i["code"] in [";","if","while","let","else","#","{","}"]:
                sem_output.remove(i)
            elif i["code"] == "const":
                i["code"] = "pushc"
                i["operand"] = i["value"]
            elif i["code"]=="ident":
                if "pointer" in i:
                    i["code"] = "push*"
                else:
                    i["code"] = "pushv"
                i["operand"] = i["name"]
            elif i["code"] == "=":
                i["code"] = "asgn"
        for i in list(sem_output):
            if i["code"] in ["jmp","jz"] :
                i["operand"] = sem_output.index(i["value"])  


        print("\n\n\n")
        j = 0
        for i in sem_output:
                print(j,end='  ')
                if i["code"] in ["pushv","pushc","push*","jmp","jz"]:
                    print(i["code"]+"("+str(i["operand"])+")")
                else:
                    print(i["code"])
                j+=1
        print("\n SEMANTIC SUCCESS!!")
        return True
    else:
        print("\n semantic error!!")
        return False

sem_analyser2()


###################################### VIRTUAL MACHINE #######################
# pushc pushv push* asgn label jmp jz eof     + - * / > < == ! || &&
def Virtual_Machine():
    stack = list()
    variables = dict()
    code_segment = sem_output.copy()
    i = 0
    while i < len(code_segment):
        if code_segment[i]["code"]in ["pushc","push*"]:
            stack.append(code_segment[i]["operand"])
        elif code_segment[i]["code"]=="pushv":
            stack.append(variables[code_segment[i]["operand"]])
        elif code_segment[i]["code"]=="asgn":
            buf = stack.pop()
            variables[str(stack.pop())]=buf
        elif code_segment[i]["code"]=="label":
            pass
        elif code_segment[i]["code"]=="jmp":
            i = code_segment[i]["operand"]
            continue
        elif code_segment[i]["code"]=="jz":
            if int(stack.pop()) == 0:
                i = code_segment[i]["operand"]
                continue


        elif code_segment[i]["code"]=="+":
            buff = float(stack.pop()) + float(stack.pop())
            stack.append(str(buff))
        elif code_segment[i]["code"]=="*":
            buff = float(stack.pop()) * float(stack.pop())
            stack.append(str(buff))
        elif code_segment[i]["code"]=="-":
            buff = float(stack.pop())
            buff = float(stack.pop()) - buff
            stack.append(str(buff))
        elif code_segment[i]["code"]=="/":
            buff = float(stack.pop())
            buff = float(stack.pop()) / buff
            stack.append(str(buff))
        elif code_segment[i]["code"]=="==":
            if  float(stack.pop()) == float(stack.pop()):
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]=="!":
            if  float(stack.pop()) == "0":
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]==">":
            buff = float(stack.pop())
            if float(stack.pop()) > buff:
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]=="<":
            buff = float(stack.pop())
            if float(stack.pop()) < buff:
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]=="&&":
            if  float(stack.pop()) and float(stack.pop()):
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]=="||":
            if  float(stack.pop()) or float(stack.pop()):
                stack.append(1)
            else:
                stack.append(0)
        elif code_segment[i]["code"]=="eof":
            break # success
        i+=1

    for i in variables:
        print(i+": "+variables[i])

    

Virtual_Machine()       


input()



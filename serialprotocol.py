import serial as ps
import struct
from enum import Enum

"""
Ok quindi vediamo cosa e' questa classe:

non e' altro che un wrapper tra dati python e dati in formato binario
alla c

assunzioni: i messaggi saranno sempre in questo formato sia per leggere
che scrivere

uint8_t id, uint8_t val, uint32_t len, uint8_t payload[len]

dove id e val sono usati per fare multiplexing dei messaggi,
len e' la lunghezza del payload e poi il payload.

Siamo su python che e' bellino e tutto, pero' se si deve lavorare a basso
livello rompe un po'. La soluzione e' questa:

impara questi simboli

i -> int                    (4 byte)            integer
I -> unsigned int           (4 byte)            integer
q -> long long              (8 byte)            integer
Q -> unsigned long long     (8 byte)            integer
B -> unsigned char aka byte (1 byte)            integer
s -> char []                (uint32_t + char)   bytes       *
d -> na struttura           (struct)            DATA
? -> boolean                (1 byte)            bool
f -> float                  (4 byte)            float
aX -> array di X dove X puo' essere uno qualunque dei valori
      precedenti
      un array e' rappresentato da un unsigned int che indica quanti elementi
      sono presenti nell'array e dagli elementi 

*   l'intero che indica la lunghezza della stringa comprende anche il 
    carattere terminatore \0

Ok imparati? son pochi daje

hai bisogno solamente della classe DATA quindi creiamo un oggetto

id = 1
value = 2
d = DATA(id,value)

nice ora abbiamo d che ci si fa?

Dipende, vuoi usarlo per ricevere o inviare dati?

diciamo inviare ok? Fantastico

semplicemente sommaci dentro i dati che vuoi inviare es.

d += 1
d += 'ciao'
d += ('a', False, True, False)

cosa contiene d dopo queste operazioni?

un messaggio con un intero di valore 1 una stringa di valore 'ciao\0'
e un array di booleani

potevamo ottenere la stessa identica cosa con una sola operazione

d += [1,'ciao', ('a', False, True, False)]

questo avrebbe dato errore invece

d += (1,'ciao', ('a', False, True, False))

le tuple hanno un valore speciale, servono per forzare (nei limiti)
il tipo che vuoi inviare e cioe' il primo elemento della tupla indica
il tipo dell'elemento da aggiungere ad esempio

d += 200

inserisce l'intero 200 se voglio inserire un byte di valore 200

d += ('B', 200)

inoltre se voglio inserire un array devo per forza utilizzare una tupla
quindi

d += [1,2,3,4]

il messaggio sara' 1,2,3,4
mentre

d += ('a',1,2,3,4)

o anche

d += ('a',[1,2,3,4])

o ancora

d += ('aB',[1,2,3,4]) //in questo caso forzo l'array ad essere un array di byte

sara' 4(dimensione),1,2,3,4

ultima cosa puoi aggiungere anche altri DATA ad un data
ad esempio

b = sp.DATA(1,2)
b += 'ciao'
d = sp.DATA(1,2)
d += 1,2,3,4
d += b


perfetto. Per vedere il risultato e ottenere i bytes nulla di piu' semplice

bytes(d) o ancora meglio (per chiarezza)

list(bytes(d))

se si vuole invece direttamente i valori in python sotto forma di lista

d.get_data()

ad esempio

d += 1
d += 'ciao'
d += ('a', 'su','sa','see')

d.get_data()
[1, b'ciao', ['su','sa','see']]

Ok, per ricevere invece

usiamo *= inceve di += e ci aggiungiamo cio' che vogliamo
sotto forma del suo tipo di dato

e cioe'

vogliamo leggere una stringa

d *= 's'

un array di stringhe

d *= 'as'

un intero

d *= 'i'

al solito tutto si puo' compattare in

d *= 'sasi'

se vogliamo leggere una struttura allora ci basta fare in questo modo

b = sp.DATA(1,2)
b *= 'sB'
d = sp.DATA(1,2)
d *= 'III'
d *= ('d', b)

in questo caso non e' possibile unire le operazioni in una unica

cosi stiamo dicendo che quello che leggeremo sara' un messaggio composto
da 3 interi piu' una struttura composta da una stringa e un carattere

altro caso speciale e' se vogliamo leggere un array di strutture

d *= ('ad', b)

in questo caso stiamo specificando che leggeremo un array di strutture dove
ogni struttura ha la stessa struttura (naturalmente)

per leggere un messaggio (in realta' un qualque oggetto bytes())

ci basta fare 

d(bytes)

esempio completo:

d = sp.DATA(1,2)

d += ['ciao', 3, ('a', 'c', 'd', 'e')]

b = sp.DATA(1,2)

b *= 'sIaB'

byte = bytes(d)

b(byte)

b.get_data()
[b'ciao', 3, [12, 13, 14]] (i caratteri vengono trasformati in interi aka unsigned bytes)


"""


class DifferentIdException(Exception):
    pass


class DifferentValueException(Exception):
    pass


class UnknownFormatException(Exception):
    pass


class DifferentLengthException(Exception):
    pass


class DATA:

    def __init__(self, id, value, default_int='unsigned',
                 default_long='unsigned', expand_arrays=False, copy=None):
        if copy is None:
            self.__id = id
            self.__value = value
            self.__fmt = '=BBI'
            self.__len = 0
            self.__data = []
            self.__data_read = []
            if default_int != 'unsigned' and default_int != 'signed':
                raise ValueError("please, numbers can be just signed \
                                  or unsigned")
            if default_long != 'unsigned' and default_long != 'signed':
                raise ValueError("please, longs can be just signed \
                                  or unsigned")
            self.__def_int = default_int
            self.__def_long = default_long
            self._exp_arr = expand_arrays
            self._sub_data = False
            self._up_data = None
            self.__index = 0
            self.__int_index = 0
            self.__sent_len = False
            self.__int_sent_len = False
        else:
            self.__id = copy.__id
            self.__value = copy.__value
            self.__fmt = copy.__fmt
            self.__len = copy.__len
            self.__data = []
            self.__data_read = [DATA(0, 0, copy=x) for x in copy.__data_read]
            self.__def_int = copy.__def_int
            self.__def_long = copy.__def_long
            self._exp_arr = copy._exp_arr
            self._sub_data = True
            self._up_data = copy._up_data
            self.__index = 0
            self.__int_index = 0
            self.__sent_len = False
            self.__int_sent_len = False

    def get_id(self):
        return self.__id

    def get_value(self):
        return self.__value

    def get_def_int(self):
        return self.__def_int

    def get_def_long(self):
        return self.__def_long

    def get_exp_arr(self):
        return self._exp_arr

    def __iadd__(self, other):
        if type(other) != list:
            self.__internal_add([other])
        else:
            self.__internal_add(other)
        return self

    def __internal_add(self, objects):
        for val in objects:
            t, l, d = self._calc_from_val(val)
            self.__len += l
            if 'as' == t:
                if self._exp_arr:
                    self.__fmt += 'I'
                    self.__data.append(len(d))
                    for s_arr in d:
                        self.__fmt += 's'
                        self.__data.append(s_arr)
                else:
                    self.__fmt += 'as'
                    res = []
                    for s_arr in d:
                        res.append(s_arr)
                    self.__data.append(res)
            elif 'ad' == t:
                self.__fmt += t
                self.__data.append(d)
            elif 'a' in t:
                if self._exp_arr:
                    self.__fmt += 'I{0}'.format(len(d))+t[1]
                    self.__data += d
                else:
                    self.__fmt += t
                    self.__data.append(d)
            else:
                self.__fmt += t
                self.__data.append(d)
            if self._sub_data:
                self._up_data.__len += l

    def _calc_from_val(self, val):
        if type(val) == int:
            return self._handle_integer(val)
        elif type(val) == float:
            return self._handle_floating(val)
        elif type(val) == bool:
            return self._handle_boolean(val)
        elif type(val) == bytes or type(val) == bytearray:
            return self._handle_bytes(val)
        elif type(val) == str:
            return self._handle_strings(val)
        elif type(val) == tuple:
            return self._handle_tuples(val)
        elif type(val) == DATA:
            return self._handle_data(val)

    def _handle_data(self, val):
        val._sub_data = True
        val._up_data = self
        return 'd', int(val) - 6, val

    def _handle_tuples(self, val):
        if len(val[0]) == 1:
            if val[0] in 'B?iIfQq':
                if len(val) != 2:
                    raise ValueError('The tuple should have exactly 2 \
                                      elements')
                if type(val[1]) == list or type(val[1]) == tuple:
                    raise ValueError('Tuple or List not allowed if the first \
                                      type is not an array')
                v = self._convert_to_type(val[0], val[1])
                l = DATA._type_to_len(val[0])
                return val[0], l, v
            elif val[0] == 'a':
                if type(val[1]) != list and type(val[1]) != tuple:
                    v = val[1:]
                else:
                    v = val[1]
                t, l, _ = self._calc_from_val(v[0])
                res = []
                if t in 'sd':
                    l = 0
                    for elem in v:
                        s = self._convert_to_type(t, elem)
                        l += len(s)
                        if t == 's':
                            l += 1
                        res.append(s)
                    return 'a'+t, 4+l, res
                else:
                    for elem in v:
                        res.append(self._convert_to_type(t, elem))
                    return 'a'+t, 4+l*len(res), res
            elif val[0] == 's':
                if type(val[1]) != list and type(val[1]) != tuple:
                    v = val[1:]
                else:
                    v = val[1]
                v = self._convert_to_type('s', v)
                return 's', len(v)+1+4, v
            else:
                raise ValueError('The type of this is not recognizable')
        else:
            if 'a' in val[0]:
                if type(val[1]) != list and type(val[1]) != tuple:
                    v = val[1:]
                else:
                    v = val[1]
                res = []
                if val[0][1] in 'sd':
                    l = 0
                    for elem in v:
                        s = self._convert_to_type(val[0][1], elem)
                        l += len(s)
                        if val[0][1] == 's':
                            l += 1
                        res.append(s)
                    return val[0], 4+l, res
                else:
                    for elem in v:
                        res.append(self._convert_to_type(val[0][1], elem))
                return val[0], 4+self._type_to_len(val[0])*len(res), res

    def _convert_to_type(self, t, val):
        if t == 'B':
            v = self._convert_to_int(val)
            if v > 255:
                raise ValueError('Only values between 0 and 255 are allowed \
                                  for bytes')
        elif t == '?':
            try:
                v = bool(val)
            except Exception:
                raise ValueError("Ok so I don't know what value you have passed to me \
                                  but is definitely not a boolean")
        elif t == 'i' or t == 'I':
            v = self._convert_to_int(val)
            if t == 'I':
                if v.bit_length() > 32:
                    raise ValueError("The integer seems a lot like an unsigned \
                                      long long")
                if v < 0:
                    raise ValueError("The integer is not unsigned")
            else:
                if v.bit_length() > 31:
                    raise ValueError('The integer seems a lot like a long \
                                      long')
        elif t == 'f':
            try:
                v = float(val)
            except Exception:
                raise ValueError('Ok, the "float" is actually NOT a float')
        elif t == 'Q' or t == 'q':
            v = self._convert_to_int(val)
            if t == 'Q':
                if v.bit_length() > 64:
                    raise ValueError("The long integer seems a lot like \
                                      a too much big number")
                if v < 0:
                    raise ValueError("The long integer is not unsigned")
            else:
                if v.bit_length() > 63:
                    raise ValueError('The long integer seems a lot like \
                                      a too much big number')
        elif t == 's':
            v = self._convert_to_string(val)
        elif t == 'd':
            val._sub_data = True
            val._up_data = self
            v = val
        else:
            raise ValueError("I don't know this type... ")
        return v

    def _convert_to_string(self, val):
        if type(val) == tuple or type(val) == list:
            v = bytes(''.join(str(s) for s in val), 'utf-8')
        else:
            v = bytes(val, 'utf-8')
        return v

    def _convert_to_int(self, val):
        try:
            v = int(val)
        except Exception:
            try:
                v = int(val, 2)
            except Exception:
                try:
                    v = int(val, 16)
                except Exception:
                    try:
                        v = ord(val)
                    except Exception:
                        raise ValueError("I've really tried to convert this to an integer \
                                          but as everything else in my \
                                          life I've failed. int(x), \
                                          int(x,2), int(x,16) even ord(x) \
                                          didn't work if I've missed \
                                          something let me know")
        return v

    def _handle_strings(self, val):
        if len(val) == 1:
            return 'B', 1, ord(val)
        l = len(val) + 1
        return 's', l+4, bytes(val, 'utf-8')

    def _handle_bytes(self, val):
        if 0 in [c in val for c in b'01']:
            raise ValueError('Only 0 and 1 are allowed in a byte')
        v = int(val, 2)
        if v > 255:
            raise ValueError('Only values between 0 and 255 are allowed')

        return 'B', 1, v

    def _handle_boolean(self, val):
        return '?', 1, val

    def _handle_floating(self, val):
        return 'f', 4, val

    def _handle_integer(self, val):
        if val.bit_length() > 64:
            raise ValueError("You are trying to pack an integer which is \
                             greater than 2^64, calm your titties big boi")
        if val.bit_length() > 32:
            if self.__def_long == 'signed':
                if val.bit_length() < 64:
                    return 'q', 8, val
                else:
                    if val < 0:
                        raise ValueError("Sorry this long long is signed but \
                                          I don't have enough bits for it")
                    return 'Q', 8, val
            else:
                if val >= 0:
                    return 'Q', 8, val
                else:
                    if val.bit_length() == 64:
                        raise ValueError("Sorry this long long is signed but \
                                          I don't have enough bits for it")
                    return 'q', 8, val
        else:
            if self.__def_int == 'signed':
                if val.bit_length() < 32:
                    return 'i', 4, val
                else:
                    if val < 0:
                        return 'q', 8, val
                    return 'I', 4, val
            else:
                if val >= 0:
                    return 'I', 4, val
                else:
                    if val.bit_length() == 32:
                        return 'q', 8, val
                    return 'i', 4, val

    def get_def(self):
        fmt = self.format()
        return fmt if not self._sub_data else fmt[4:]

    def format(self):
        fmt = '=BBI'
        index = 4
        data_index = 0
        while index < len(self.__fmt):
            if self.__fmt[index] == 'a':
                if self.__fmt[index + 1] not in 'sd':
                    fmt += 'I{0}'.format(len(self.__data[data_index]))
                elif self.__fmt[index + 1] == 'd':
                    fmt += 'I'
                    for data in self.__data[data_index]:
                        fmt += data.get_def()
                    index += 1
                    data_index += 1
                else:
                    fmt += 'I'
                    for data in self.__data[data_index]:
                        fmt += 'I{0}s'.format(len(data) + 1)
                    index += 1
                    data_index += 1
                index += 1
            elif self.__fmt[index] == 'd':
                fmt += self.__data[data_index].get_def()
                index += 1
                data_index += 1
            elif self.__fmt[index] == 's':
                fmt += 'I{0}s'.format(len(self.__data[data_index]) + 1)
                index += 1
                data_index += 1
            elif self.__fmt[index] in '0123456789':
                fmt += self.__fmt[index]
                index += 1
            else:
                fmt += self.__fmt[index]
                index += 1
                data_index += 1
        return fmt

    @staticmethod
    def _type_to_len(val):
        if val in "iIf":
            return 4
        elif val in 'B?':
            return 1
        elif val in 'qQ':
            return 8
        elif 's' in val:
            return int(val[:-1])
        else:
            return 0

    @staticmethod
    def val_to_type(val):
        if type(val) == int:
            return 'I'
        elif type(val) == str:
            return 'B'
        elif type(val) == float:
            return 'f'
        elif type(val) == bool:
            return '?'
        elif type(val) == bytes:
            return 'B'

    def __int__(self):
        return self.__len + 4 + 1 + 1

    def __len__(self):
        return self.__int__()

    def __bytes__(self):
        fmt = self.format()
        return (struct.pack(fmt, self.__id, self.__value,
                struct.calcsize('='+fmt[4:]), *self))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            if type(self.__data[self.__index]) == list or \
               type(self.__data[self.__index]) == tuple:
                if self.__sent_len:
                    if self.__int_index < len(self.__data[self.__index]):
                        ret = self.__data[self.__index][self.__int_index]
                        if type(ret) == DATA:
                            try:
                                return ret.__next__()
                            except StopIteration:
                                self.__int_index += 1
                                return self.__next__()
                        elif type(ret) == bytes:
                            if self.__int_sent_len:
                                self.__int_index += 1
                                self.__int_sent_len = False
                            else:
                                self.__int_sent_len = True
                                ret = len(ret) + 1
                        else:
                            self.__int_index += 1
                        return ret
                    else:
                        self.__sent_len = False
                        self.__int_index = 0
                        self.__index += 1
                        return self.__next__()
                else:
                    self.__sent_len = True
                    return len(self.__data[self.__index])
            elif type(self.__data[self.__index]) == bytes:
                if self.__sent_len:
                    ret = self.__data[self.__index]
                    self.__index += 1
                    self.__sent_len = False
                    return ret
                else:
                    self.__sent_len = True
                    return len(self.__data[self.__index]) + 1
            elif type(self.__data[self.__index]) == DATA:
                try:
                    return self.__data[self.__index].__next__()
                except StopIteration:
                    self.__index += 1
                    return self.__next__()
            else:
                ret = self.__data[self.__index]
                self.__index += 1
                return ret
        except IndexError:
            self.__index = 0
            raise StopIteration()

    def _gen_def(self, l):
        return FormatGenerator(self, l)

    def __call__(self, data):
        self.__data = []
        t = []
        gen = self._gen_def(t)
        try:
            while True:
                size, fmt = gen.__next__()
                if fmt == 'd':
                    if type(size) == list:
                        t.append(size)
                        for d in size:
                            self.__index += d(data[self.__index:])
                    else:
                        t.append(size)
                        self.__index += size(data[self.__index:])
                else:
                    t += list(struct
                              .unpack(fmt,
                                      data[self.__index:self.__index+size])
                              )
                    self.__index += size
        except StopIteration:
            pass
        self.__data = t[3:] if not self._sub_data else t
        index = self.__index
        self.__index = 0
        return index

    def get_fmt(self):
        return self.__fmt

    def get_data(self):
        return self.__data

    def get_data_read(self):
        return self.__data_read

    def __imul__(self, other):
        if type(other) != list:
            other = [other]
        for c in other:
            if type(c) == str:
                for char in c:
                    if char not in 'B?IifqQas':
                        raise ValueError("Didn't recognize the pattern passed")
                    self.__fmt += char
            elif type(c) == tuple:
                if c[0] == 'd' and type(c[1]) == DATA:
                    c[1]._sub_data = True
                    c[1]._up_data = self
                    self.__data_read.append(c[1])
                    self.__fmt += 'd'
                elif c[0] == 'ad' and type(c[1]) == DATA:
                    c[1]._sub_data = True
                    c[1]._up_data = self
                    self.__data_read.append(c[1])
                    self.__fmt += 'ad'
        return self


class FormatGenerator():

    def __init__(self, data, l):
        self.__data = data
        self._data_index = 0
        self.__index = 1 if not data._sub_data else 4
        self._state = 0
        self._functions = [self._normal_exec, self._array_exec,
                           self._data_exec, self._post_array_exec,
                           self._string_exec, self._arr_str_exec_first,
                           self._arr_str_exec_sec, self._post_string_exec,
                           self._arr_str_exec_third]
        self._list = l
        self._len = 0
        self._str_len = 0

    def __next__(self):
        if self.__index < len(self.__data.get_fmt()):
            return self._functions[self._state]()
        raise StopIteration()

    def _string_exec(self):
        l = self._list[-1]
        self._list.pop()
        fmt = '={0}s'.format(l)
        self._state = 7
        return struct.calcsize(fmt), fmt

    def _post_string_exec(self):
        s = self._list[-1]
        self._list.pop()
        self._list.append(s[:-1])
        self.__index += 1
        self._state = 0
        return self.__next__()

    def _arr_str_exec_first(self):
        if self._str_len > 0:
            fmt = '=I'
            self._state = 6
            return struct.calcsize(fmt), fmt
        else:
            self._state = 3
            return self.__next__()

    def _arr_str_exec_sec(self):
        l = self._list[-1]
        self._list.pop()
        fmt = '={0}s'.format(l)
        self._state = 8
        return struct.calcsize(fmt), fmt

    def _arr_str_exec_third(self):
        s = self._list[-1]
        self._list.pop()
        self._list.append(s[:-1])
        self._state = 5
        self._str_len -= 1
        return self.__next__()

    def _normal_exec(self):
        fmt = '='
        index = self.__index
        data = self.__data
        while index < len(data.get_fmt()):
            if data.get_fmt()[index] == 'a':
                fmt += 'I'
                self._state = 1
                index += 1
                break
            elif data.get_fmt()[index] == 'd':
                self._state = 2
                break
            elif data.get_fmt()[index] == 's':
                self._state = 4
                fmt += 'I'
                break
            else:
                fmt += data.get_fmt()[index]
                index += 1
        self.__index = index
        return struct.calcsize(fmt), fmt

    def _data_exec(self):
        fmt = 'd'
        cp = self.__data.get_data_read()[self._data_index]
        self.__index += 1
        self._data_index += 1
        res = DATA(0, 0, copy=cp)
        self._state = 0
        return res, fmt

    def _array_exec(self):
        l = self._list[-1]
        if not self.__data._exp_arr:
            self._list.pop()
        c = self.__data.get_fmt()[self.__index]
        if c not in 'sd':
            fmt = '={0}'.format(l)
            self._len = l
            fmt += self.__data.get_fmt()[self.__index]
            self._state = 3
            return struct.calcsize(fmt), fmt
        elif c == 'd':
            fmt = 'd'
            res = []
            cp = self.__data.get_data_read()[self._data_index]
            self._data_index += 1
            for _ in range(l):
                res.append(DATA(0, 0, copy=cp))
            self._state = 0
            self.__index += 1
            return res, fmt
        else:
            self._state = 5
            self._len = l
            self._str_len = l
            return self.__next__()

    def _post_array_exec(self):
        if not self.__data._exp_arr:
            l = []
            for _ in range(self._len):
                l.insert(0, self._list.pop())
            self._list.append(l)
        self._state = 0
        self.__index += 1
        self._len = 0
        return self.__next__()

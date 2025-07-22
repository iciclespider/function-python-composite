##################################################################################
#
# Pythonic class wrappers around protobuf classes that enables traversing
# and modifying the protobuf message structure much like one can in JavaScript.
# For example, to get a region value from the composite's spec:
#
#   region = request.observed.composite.resource.spec.region
#
# If any item in the path to the field does not exist, None is returned.
# To set a field in the composite status:
#
#   response.desired.composite.resource.status.homepage.url = 'https://for.example.com'
#
# Here all items in the path to the field that do not exist will be created.
#
##################################################################################

import google.protobuf.struct_pb2


def protobuf_map(**kwargs):
    values = google.protobuf.struct_pb2.Struct()
    if len(kwargs):
        values.update(kwargs)
    return Values(None, None, values, Values.Type.MAP)


def protobuf_list(*args):
    values = google.protobuf.struct_pb2.ListValues()
    if len(args):
        values.extend(args)
    return Values(None, None, values, Values.Type.LIST)


class Message:
    def __init__(self, parent, key, descriptor, message, read_only=False):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_descriptor'] = descriptor
        self.__dict__['_message'] = message
        self.__dict__['_read_only'] = read_only
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        field = self._descriptor.fields_by_name.get(key)
        if not field:
            raise AttributeError(obj=self, name=key)
        if self._message:
            value = getattr(self._message, key)
        else:
            value = None
        if value is None and field.has_default_value:
            value = field.default_value
        if field.type == field.TYPE_MESSAGE:
            if field.message_type.name == 'Struct':
                value = Values(self, key, value, Values.Type.MAP, self._read_only)
            elif field.message_type.name == 'ListValue':
                value = Values(self, key, value, Values.Type.LIST, self._read_only)
            elif field.label == field.LABEL_REPEATED:
                if field.message_type.GetOptions().map_entry:
                    value = MapMessage(self, key, field.message_type, value, self._read_only)
                else:
                    value = RepeatedMessage(self, key, field.message_type, value, self._read_only)
            else:
                value = Message(self, key, field.message_type, value, self._read_only)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._message != None

    def __len__(self):
        return len(self._descriptor.fields)

    def __contains__(self, key):
        return key in self._descriptor.fields_by_name

    def __iter__(self):
        for key in self._descriptor.fields_by_name:
            yield key, self[key]

    def __hash__(self):
        if self._message:
            return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
        return 0

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._message is None:
            return other._message is None
        elif other._message is None:
            return False
        if len(self) != len(other):
            return False
        for key, value in self:
            if key not in other:
                return False
            if value != other[key]:
                return False
        return True

    def __str__(self):
        return str(self._message)

    def _create_child(self, key, type=None):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        return getattr(self._message, key)

    def __call__(self, **kwargs):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        self._message.Clear()
        self.__dict__['_cache'] = {}
        for key, value in kwargs.items():
            self[key] = value
        return self

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if key not in self._descriptor.fields_by_name:
            raise AttributeError(obj=self, name=key)
        if self._message is None:
            self.__dict__['_message'] = self._parent._create_child(self._key)
        if isinstance(value, Message):
            value = value._message
        elif isinstance(value, (MapMessage, RepeatedMessage)):
            value = value._messages
        elif isinstance(value, Values):
            value = value._values
        setattr(self._message, key, value)
        if key in self._cache:
            del self._cache[key]

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if key not in self._descriptor.fields_by_name:
            raise AttributeError(obj=self, name=key)
        if self._message is not None:
            del self._message[key]
            if key in self._cache:
                del self._cache[key]


class MapMessage:
    def __init__(self, parent, key, descriptor, messages, read_only=False):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_field'] = descriptor.fields_by_name['value']
        self.__dict__['_messages'] = messages
        self.__dict__['_read_only'] = read_only
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if self._messages is None or key not in self._messages:
            value = None
        else:
            value = self._messages[key]
        if value is None and self._field.has_default_value:
            value = self._field.default_value
        if self._field.type == self._field.TYPE_MESSAGE:
            if self._field.message_type.name == 'Struct':
                value = Values(self, key, value, Values.Type.MAP, self._read_only)
            elif self._field.message_type.name == 'ListValue':
                value = Values(self, key, value, Values.Type.LIST, self._read_only)
            elif self._field.label == self._field.LABEL_REPEATED:
                if self._field.message_type.GetOptions().map_entry:
                    value = MapMessage(self, key, self._field.message_type, value, self._read_only)
                else:
                    value = RepeatedMessage(self, key, self._field.message_type, value, self._read_only)
            else:
                value = Message(self, key, self._field.message_type, value, self._read_only)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._messages != None and len(self._messages) > 0

    def __len__(self):
        return 0 if self._messages is None else len(self._messages)

    def __contains__(self, key):
        return self._messages is not None and key in self._messages

    def __iter__(self):
        if self._messages is not None:
            for key in self._messages:
                yield key, self[key]

    def __hash__(self):
        if self._nessages is not None:
            return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
        return 0

    def __eq__(self, other):
        if not isinstance(other, MapMessage):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._messages is None:
            return other._messages is None
        elif other._messages is None:
            return False
        if len(self) != len(other):
            return False
        for key, value in self:
            if key not in other:
                return False
            if value != other[key]:
                return False
        return True

    def __str__(self):
        return str(self._messages)

    def _create_child(self, key, type=None):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        return self._messages[key]

    def __call__(self, **kwargs):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        self._messages.Clear()
        self.__dict__['_cache'] = {}
        for key, value in kwargs.items():
            self[key] = value
        return self

    def __setattr__(self, key, message):
        self[key] = message

    def __setitem__(self, key, message):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        if isinstance(message, Message):
            message = message._message
        self._messages[key] = message
        if key in self._cache:
            del self._cache[key]

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if key not in self._descriptor.fields_by_name:
            raise AttributeError(obj=self, name=key)
        if self._messages is not None:
            if key in self._messages:
                del self._messages[key]
            if key in self._caache:
                del self._cache[key]


class RepeatedMessage:
    def __init__(self, parent, key, descriptor, messages, read_only=False):
        self._parent = parent
        self._key = key
        self._descriptor = descriptor
        self._messages = messages
        self._read_only = read_only
        self._cache = {}

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if self._messages is None or key >= len(self._messages):
            message = None
        else:
            message = self._messages[key]
        value = Message(self._parent, key, self._descriptor, message, self._read_only)
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._messages != None and len(self._messages) > 0

    def __len__(self):
        return 0 if self._messages is None else len(self._messages)

    def __contains__(self, key):
        return self._messages is not None and key in self._messages

    def __iter__(self):
        if self._messages is not None:
            for ix in range(len(self._messages)):
                yield self[ix]

    def __hash__(self):
        if self._messages is not None:
            return hash(tuple(hash(item) for item in self))
        return 0

    def __eq__(self, other):
        if not isinstance(other, RepeatedMessage):
            return False
        if self._descriptor.full_name != other._descriptor.full_name:
            return False
        if self._messages is None:
            return other._messages is None
        elif other._messages is None:
            return False
        if len(self) != len(other):
            return False
        for ix, value in enumerate(self):
            if value != other[ix]:
                return False
        return True

    def __str__(self):
        return str(self._messages)

    def _create_child(self, key, type=None):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        while key >= len(self._messages):
            self._messages.add()
        return self._messages[key]

    def __call__(self, *args):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self.__dict__['_messages'] = self._parent._create_child(self._key)
        self._messages.Clear()
        self.__dict__['_cache'] = {}
        for arg in args:
            self.append(arg)
        return self

    def __setitem__(self, key, message):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        while key >= len(self._messages):
            self._messages.add()
        if isinstance(message, Message):
            message = message._message
        self._messages[key] = message
        if key in self._cache:
            del self._cache[key]

    def __delitem__(self, key):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._values is not None:
            del self._values[key]
            if key in self._cache:
                del self._cache[key]

    def append(self, message=None):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if self._messages is None:
            self._messages = self._parent._create_child(self._key)
        if message is None:
            message = self._messages.add()
        else:
            message = self._messages.append(message)
        return self[len(self._messages) - 1]


class ProtobufValue:
    @property
    def _protobuf_value(self):
        return None


class Values:
    class Type:
        UNKNOWN = 0
        MAP = 1
        LIST = 2

    def __init__(self, parent, key, values, type, read_only=None):
        self.__dict__['_parent'] = parent
        self.__dict__['_key'] = key
        self.__dict__['_values'] = values
        self.__dict__['_type'] = type
        self.__dict__['_read_only'] = read_only
        self.__dict__['_cache'] = {}

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        if key in self._cache:
            return self._cache[key]
        if isinstance(key, str):
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None or key not in self._values:
                struct_value = None
            else:
                struct_value = self._values.fields[key]
        elif isinstance(key, int):
            if self._type != self.Type.LIST:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None or key >= len(self._values):
                struct_value = None
            else:
                struct_value = self._values.values[key]
        else:
            raise ValueError('Unexpected key type')
        if struct_value is None:
            value = Values(self, key, None, self.Type.UNKNOWN, self._read_only)
        else:
            kind = struct_value.WhichOneof('kind')
            if kind is None:
                value = Values(self, key, None, self.Type.UNKNOWN, self._read_only)
            elif kind == 'struct_value':
                value = Values(self, key, struct_value.struct_value, self.Type.MAP, self._read_only)
            elif kind == 'list_value':
                value = Values(self, key, struct_value.list_value, self.Type.LIST, self._read_only)
            elif kind == 'string_value':
                value = struct_value.string_value
            elif kind == 'number_value':
                value = struct_value.number_value
            elif kind == 'bool_value':
                value = struct_value.bool_value
            elif kind == 'null_value':
                value = None
            else:
                raise ValueError(f"Unexpected value kind: {kind}")
        self._cache[key] = value
        return value

    def __bool__(self):
        return self._values != None and len(self._values) > 0

    def __len__(self):
        return 0 if self._values is None else len(self._values)

    def __contains__(self, key):
        if self._values is None:
            return False
        if isinstance(key, str):
            if self._type != self.Type.MAP:
                raise ValueError('Invalid key, must be a str for maps')
            return key in self._values
        elif isinstance(key, int):
            if self._type != self.Type.LIST:
                raise ValueError('Invalid key, must be an int for lists')
            return key < len(self._values)
        else:
            raise ValueError('Unexpected key type')

    def __iter__(self):
        if self._values is not None:
            if self._type == self.Type.MAP:
                for key in self._values:
                    yield key, self[key]
            elif self._type == self.Type.LIST:
                for ix in range(len(self._values)):
                    yield self[ix]

    def __hash__(self):
        if self._values is not None:
            if self._type == self.Type.MAP:
                return hash(tuple(hash(item) for item in sorted(iter(self), key=lambda item: item[0])))
            if self._type == self.Type.LIST:
                return hash(tuple(hash(item) for item in self))
        return self._type

    def __eq__(self, other):
        if not isinstance(other, Values):
            return False
        if self._type != other._type:
            return False
        if self._values is None:
            return other._values is None
        elif other._values is None:
            return False
        if len(self) != len(other):
            return False
        if self._type == self.Type.MAP:
            for key, value in self:
                if key not in other:
                    return False
                if value != other[key]:
                    return False
        if self._type == self.Type.LIST:
            for ix, value in enumerate(self):
                if value != other[ix]:
                    return False
        return True

    def __str__(self):
        return str(self._values)

    def _create_child(self, key, type):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if isinstance(key, str):
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            struct_value = self._values.fields[key]
        elif isinstance(key, int):
            if self._type != self.Type.LIST:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            while key >= len(self._values.values):
                self._values.values.add()
            struct_value = self._values.values[key]
        else:
            raise ValueError('Unexpected key type')
        if type == self.Type.MAP:
            if not struct_value.HasField('struct_value'):
                struct_value.struct_value.Clear()
            return struct_value.struct_value
        if type == self.Type.LIST:
            if not struct_value.HasField('list_value'):
                struct_value.list_value.Clear()
            return struct_value.list_value
        raise ValueError(f"Unexpected type: {type}")

    def __call__(self, *args, **kwargs):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if len(kwargs):
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Cannot specify kwargs on lists')
                self.__dict__['_type'] = self.Type.MAP
            if len(args):
                raise ValueError('Connect specify args on maps')
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
            self.__dict__['_cache'] = {}
            for key, value in kwargs.items():
                self[key] = value
        elif len(args):
            if self._type != self.Type.LIST:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Cannot specify args on maps')
                self.__dict__['_type'] = self.Type.LIST
            if len(kwargs):
                raise ValueError('Connect specify kwargs on lists')
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
            self.__dict__['_cache'] = {}
            for key in range(len(args)):
                self[key] = args[key]
        else:
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    self.__dict__['_type'] = self.Type.MAP # Assume a map is wanted
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            self._values.Clear()
            self.__dict__['_cache'] = {}
        return self

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if isinstance(key, str):
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            struct_value = self._values.fields[key]
        elif isinstance(key, int):
            if self._type != self.Type.LIST:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is None:
                self.__dict__['_values'] = self._parent._create_child(self._key, self._type)
            while key >= len(self._values.values):
                self._values.values.add()
            struct_value = self._values.values[key]
        else:
            raise ValueError('Unexpected key type')
        if isinstance(value, ProtobufValue):
            value = value._protobuf_value
        if value is None:
            struct_value.null_value = 0
        elif isinstance(value, bool): # Must be before int check
            struct_value.bool_value = value
        elif isinstance(value, str):
            struct_value.string_value = value
        elif isinstance(value, (int, float)):
            struct_value.number_value = value
        elif isinstance(value, dict):
            struct_value.struct_value.Clear()
            struct_value.struct_value.update(value)
        elif isinstance(value, (list, tuple)):
            struct_value.list_value.Clear()
            struct_value.list_value.extend(value)
        elif isinstance(value, Values):
            if value._type == value.Type.MAP:
                struct_value.struct_value.Clear()
                if value._values is not None:
                    struct_value.struct_value.update(value._values)
            elif value._type == value.Type.LIST:
                struct_value.list_value.Clear()
                if value._values is not None:
                    struct_value.list_value.extend(value._values)
            else:
                struct_value.null_value = 0
        else:
            raise ValueError('Unexpected type')
        if key in self._cache:
            del self._cache[key]

    def __delattr__(self, key):
        del self[key]

    def __delitem__(self, key):
        if self._read_only:
            raise ValueError(f"{self._read_only} is read only")
        if isinstance(key, str):
            if self._type != self.Type.MAP:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be a str for maps')
                self.__dict__['_type'] = self.Type.MAP
            if self._values is not None:
                if key in self._values:
                    del self._values[key]
                if key in self._cache:
                    del self._cache[key]
        elif isinstance(key, int):
            if self._type != self.Type.LIST:
                if self._type != self.Type.UNKNOWN:
                    raise ValueError('Invalid key, must be an int for lists')
                self.__dict__['_type'] = self.Type.LIST
            if self._values is not None:
                if key < len(self._values):
                    self._values.values[key].Clear()
                if key in self._cache:
                    del self._cache[key]
        else:
            raise ValueError('Unexpected key type')
